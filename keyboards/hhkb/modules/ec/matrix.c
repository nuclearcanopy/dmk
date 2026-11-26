#include "matrix.h"
#include "classic_matrix.h"
#include "keyboard.h"
#include "queue.h"
#include "task.h"
#include "task_internal.h"
#include "config.h"
#include "tusb.h"
#include "sof_lock.h"
#ifdef HHKB_HYBRID
#include "hybrid.h"
#endif
#include "stm32l072xx.h"

extern QueueHandle_t matrix_queue;

// Acquisition runs one level above the shared task priority when a level is
// available; the task drops back between scans (see the loop in matrix_task).
#if TASK_PRIO_MATRIX + 1 < configMAX_PRIORITIES
#define MATRIX_SCAN_PRIO (TASK_PRIO_MATRIX + 1)
#else
#define MATRIX_SCAN_PRIO TASK_PRIO_MATRIX
#endif

static matrix_row_t s_matrix_state[MATRIX_ROWS] = {0};
static TaskHandle_t s_matrix_task;
static volatile uint16_t s_scan_period_ticks;
static volatile uint8_t s_scan_divider;
static uint8_t s_scan_phase;
static uint8_t s_scan_rate_applied;
static bool s_scan_calibrating;

static void update_scan_period(void) {
    static const uint16_t period_us[] = {10000, 8000, 4000, 2000, 1000, 5000, 11000};
    uint8_t rate = hhkb_get_effective_scan_rate();
    if (rate >= sizeof(period_us) / sizeof(period_us[0])) rate = 4;
    s_scan_rate_applied = rate;
    s_scan_period_ticks = period_us[rate] * HHKB_SCAN_TIMER_TICKS_PER_US;
    s_scan_calibrating = hhkb_is_calibrating();
    // Leave a complete USB service window during calibration at 1 kHz.
    s_scan_divider = rate == 0 || (rate == 4 && s_scan_calibrating) ? 2 : 1;
    s_scan_phase = 0;
}

void TIM2_IRQHandler(void) {
    if (!(TIM2->SR & TIM_SR_CC1IF)) return;
    TIM2->SR = (uint32_t)~TIM_SR_CC1IF;

    uint16_t fired = (uint16_t)TIM2->CCR1;
    uint16_t step = s_scan_period_ticks;
#if HHKB_SOF_LOCK
    step = sof_lock_step(fired, step);
#elif defined(HHKB_SCAN_DIAGNOSTICS)
    sof_lock_note_fire(fired);
#endif
    uint16_t next = (uint16_t)(fired + step);
    TIM2->CCR1 = next;
    uint16_t remaining = (uint16_t)(next - (uint16_t)TIM2->CNT);
    if (remaining > step) {
        // A delayed interrupt can miss a compare. Restart from the current count.
        TIM2->CCR1 = (uint16_t)(TIM2->CNT + step);
    }

    if (++s_scan_phase < s_scan_divider) return;
    s_scan_phase = 0;

    BaseType_t higher_priority_woken = pdFALSE;
    vTaskNotifyGiveFromISR(s_matrix_task, &higher_priority_woken);
    portYIELD_FROM_ISR(higher_priority_woken);
}
#ifdef HHKB_SCAN_DIAGNOSTICS
static volatile uint32_t s_rt_rebuild_ms;
static volatile uint32_t s_rt_rebuild_count;

void hhkb_note_rt_rebuild(uint32_t ms) {
    s_rt_rebuild_ms = ms;
    s_rt_rebuild_count++;
}

void hhkb_get_rt_rebuild(uint32_t *ms, uint32_t *count) {
    if (ms) *ms = s_rt_rebuild_ms;
    if (count) *count = s_rt_rebuild_count;
}

static volatile uint32_t s_matrix_scan_count;
static volatile uint32_t s_matrix_scan_us;
static volatile uint32_t s_matrix_scan_max_us;
static volatile uint32_t s_matrix_period_us;
static volatile uint32_t s_matrix_work_max_us;
static volatile uint32_t s_matrix_queue_full;
static volatile uint32_t s_matrix_queue_peak;
static volatile uint32_t s_matrix_scan_deadline_misses;
#endif

bool matrix_is_pressed(unsigned char row, unsigned char col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return false;
    return (s_matrix_state[row] & (1U << col)) != 0;
}


#ifdef HHKB_HYBRID
static void publish_released_matrix(matrix_row_t published_state[MATRIX_ROWS]) {
    xQueueReset(matrix_queue);
    for (uint8_t row = 0; row < MATRIX_ROWS; ++row) {
        s_matrix_state[row] = 0;
        for (uint8_t col = 0; col < MATRIX_COLS; ++col)
            hhkb_get_rt_key(col, row)->lock = 0;
        matrix_event_t event = {
            .row = MATRIX_EVENT_ROW_SNAPSHOT |
                   (row == 0 ? MATRIX_EVENT_SCAN_START : 0) | row,
            .col = 0,
            .row_state_hi = 0,
        };
        xQueueSend(matrix_queue, &event, portMAX_DELAY);
        published_state[row] = 0;
    }
}
#endif

void matrix_task(void *pvParameters) {
    (void)pvParameters;

    // main creates and checks this queue before starting the scheduler.
    configASSERT(matrix_queue != NULL);

    // The platform sets APB1 to HCLK with no prescaling.
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    RCC->APB1RSTR |= RCC_APB1RSTR_TIM2RST;
    RCC->APB1RSTR &= ~RCC_APB1RSTR_TIM2RST;
    TIM2->PSC = SystemCoreClock / (1000000U * HHKB_SCAN_TIMER_TICKS_PER_US) - 1U;
    TIM2->ARR = UINT16_MAX;
    TIM2->EGR = TIM_EGR_UG;
    TIM2->CR1 = TIM_CR1_CEN;
#ifdef HHKB_SCAN_DIAGNOSTICS
    uint16_t previous_scan_start = (uint16_t)TIM2->CNT;
#endif
    s_matrix_task = xTaskGetCurrentTaskHandle();
    update_scan_period();
    TIM2->CCR1 = (uint16_t)(TIM2->CNT + s_scan_period_ticks);
    TIM2->SR = 0;
    NVIC_ClearPendingIRQ(TIM2_IRQn);
    NVIC_SetPriority(TIM2_IRQn, (1U << __NVIC_PRIO_BITS) - 1U);
    NVIC_EnableIRQ(TIM2_IRQn);
    TIM2->DIER = TIM_DIER_CC1IE;
#if HHKB_SOF_LOCK
    sof_lock_init();
#endif
    matrix_row_t published_state[MATRIX_ROWS] = {0};
#ifdef HHKB_HYBRID
    hhkb_hybrid_init();
#endif
    for (;;) {
#if HHKB_SOF_LOCK
        if (!tud_mounted() || tud_suspended()) sof_lock_reset();
#endif
        hhkb_calibration_apply_pending();
#ifdef HHKB_HYBRID
        hhkb_hybrid_power_poll();
        if (!hhkb_hybrid_powered()) {
            // Battery: no output path. Park the sensor and enter STOP; USB resets.
            TIM2->DIER = 0;
            TIM2->CR1 &= ~TIM_CR1_CEN;
            ulTaskNotifyTake(pdTRUE, 0);
            publish_released_matrix(published_state);
            hhkb_hybrid_off_service();
            hhkb_hybrid_enter_stop();
        }
#endif
        if (s_scan_rate_applied != hhkb_get_effective_scan_rate() ||
            s_scan_calibrating != hhkb_is_calibrating()) {
            NVIC_DisableIRQ(TIM2_IRQn);
            update_scan_period();
            TIM2->CCR1 = (uint16_t)(TIM2->CNT + s_scan_period_ticks);
            TIM2->SR = 0;
            NVIC_ClearPendingIRQ(TIM2_IRQn);
            NVIC_EnableIRQ(TIM2_IRQn);
        }
        // Wait at elevated priority so the scan fire preempts same-priority
        // USB/key work immediately: at equal priority the wake waits for the
        // running peer to block, which measured up to ~0.9 ms of added
        // fire-to-wake latency and a missed deadline whenever the remainder
        // of the frame could not absorb it. The priority drops again after
        // the scan publishes, so consumers run every loop - including during
        // calibration overruns, where the task never blocks.
#if MATRIX_SCAN_PRIO != TASK_PRIO_MATRIX
        vTaskPrioritySet(NULL, MATRIX_SCAN_PRIO);
#endif
        uint32_t notifications = ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
#if HHKB_SOF_LOCK
        // Latch the fire that started this scan before the next one can
        // rewrite it mid-scan; includes the fire-to-wake latency in the work.
        uint16_t sof_fire = sof_lock_last_fire();
#endif
#ifdef HHKB_SCAN_DIAGNOSTICS
        if (notifications > 1) s_matrix_scan_deadline_misses += notifications - 1;
#else
        (void)notifications;
#endif
#ifdef HHKB_SCAN_DIAGNOSTICS
        uint16_t scan_start = (uint16_t)TIM2->CNT;
        if (s_matrix_scan_count != 0) {
            s_matrix_period_us = (uint16_t)(scan_start - previous_scan_start) / HHKB_SCAN_TIMER_TICKS_PER_US;
        }
        previous_scan_start = scan_start;
#endif
        hhkb_calibration_apply_pending();
        hhkb_matrix_scan_raw(s_matrix_state);
#ifdef HHKB_SCAN_DIAGNOSTICS
        uint32_t scan_us = (uint16_t)(TIM2->CNT - scan_start) / HHKB_SCAN_TIMER_TICKS_PER_US;
        s_matrix_scan_us = scan_us;
        if (scan_us > s_matrix_scan_max_us) s_matrix_scan_max_us = scan_us;
        s_matrix_scan_count++;
#endif

        // VIA reads s_matrix_state directly. Keep that physical state live,
        // but publish releases to the key-processing queue during calibration.
        bool calibrating = hhkb_is_calibrating();
        bool first_event = true;
        for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
            matrix_row_t state = calibrating ? 0 : s_matrix_state[row];
            if (state == published_state[row]) continue;
            matrix_event_t event = {
                .row = MATRIX_EVENT_ROW_SNAPSHOT | (first_event ? MATRIX_EVENT_SCAN_START : 0) | row,
                .col = (uint8_t)state,
                .row_state_hi = (uint8_t)(state >> 8),
            };
            if (xQueueSend(matrix_queue, &event, 0) != pdPASS) {
#ifdef HHKB_SCAN_DIAGNOSTICS
                s_matrix_queue_full++;
#endif
                // Retry this row from its latest scan on the next pass.
                break;
            }
            published_state[row] = state;
            first_event = false;
        }

#ifdef HHKB_SCAN_DIAGNOSTICS
        if (!first_event) {
            UBaseType_t waiting = uxQueueMessagesWaiting(matrix_queue);
            if (waiting > s_matrix_queue_peak) s_matrix_queue_peak = waiting;
        }
        uint32_t work_us = (uint16_t)(TIM2->CNT - scan_start) / HHKB_SCAN_TIMER_TICKS_PER_US;
        if (work_us > s_matrix_work_max_us) s_matrix_work_max_us = work_us;
#endif
#ifdef HHKB_SCAN_DIAGNOSTICS
        if (!first_event) sof_lock_note_publish();
#endif
#if HHKB_SOF_LOCK
        sof_lock_note_work(sof_fire);
#endif
#if MATRIX_SCAN_PRIO != TASK_PRIO_MATRIX
        vTaskPrioritySet(NULL, TASK_PRIO_MATRIX);
#endif
        // Keep the next timer notification. Discarding it here forces a
        // nearly-1-ms scan to wait for the following tick, halving throughput.
        // HHKB shares priority with USB/key processing, so this yield gives
        // ready consumers time even when acquisition overruns its period.
        taskYIELD();
    }
}

#ifdef HHKB_SCAN_DIAGNOSTICS
void hhkb_get_scan_diagnostics(uint32_t *scan_us, uint32_t *scan_max_us, uint32_t *work_max_us, uint32_t *missed, uint32_t *q_full) {
    if (scan_us) *scan_us = s_matrix_scan_us;
    if (scan_max_us) *scan_max_us = s_matrix_scan_max_us;
    if (work_max_us) *work_max_us = s_matrix_work_max_us;
    if (missed) *missed = s_matrix_scan_deadline_misses;
    if (q_full) *q_full = s_matrix_queue_full;
}

void hhkb_reset_scan_diagnostics_peaks(void) {
    s_matrix_scan_max_us = 0;
    s_matrix_work_max_us = 0;
}
#endif
