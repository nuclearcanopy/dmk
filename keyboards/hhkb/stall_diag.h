#pragma once
// Opt-in stall diagnostics (HHKB_STALL_DIAG=1). Compiles to nothing when off.
// Counters are written by their owner task and read/cleared by vial_diag_task
// once per second; races only blur a count, never behaviour.
#include "config.h"
#if HHKB_STALL_DIAG
#include <stdint.h>
#include <stdbool.h>
#include "FreeRTOS.h"
#include "task.h"
#include "stm32l072xx.h"

typedef struct {
    volatile uint32_t eeprom_max_us;  // vial_eeprom_task() peak
    volatile uint32_t tud_max_us;     // tud_task_ext() peak
    volatile uint32_t flash_calls, flash_fail, flash_max_us; // write_word()
    volatile uint32_t wake_peak_us, wake_over5ms;             // fire -> task wake
    volatile uint32_t adc_timeouts;   // samples where adc_finish_sample timed out
    volatile uint32_t scan_overruns;  // scans containing >= 1 such sample
    volatile uint8_t sensor_down;     // matrix sensor_power_down
} stall_diag_t;
extern stall_diag_t g_stall;

// TIM2 is free-running, 16-bit, 4 ticks/us (32 MHz / (PSC+1=8); APB1 undivided),
// so it wraps at 16.4 ms. Durations of 12 ms or more fall back to the 1 ms RTOS tick.
typedef struct { uint16_t cnt; TickType_t tick; } stall_mark_t;
static inline stall_mark_t stall_mark(void) {
    stall_mark_t m = {(uint16_t)TIM2->CNT, xTaskGetTickCount()};
    return m;
}
static inline uint32_t stall_us_since(stall_mark_t m) {
    uint32_t ms = (uint32_t)(xTaskGetTickCount() - m.tick) * portTICK_PERIOD_MS;
    if (ms >= 12U) return ms * 1000U;
    return (uint16_t)((uint16_t)TIM2->CNT - m.cnt) / 4U;
}
static inline void stall_max(volatile uint32_t *peak, uint32_t v) {
    if (v > *peak) *peak = v;
}
#define STALL_TIMED(peak, stmt) do { stall_mark_t m_ = stall_mark(); stmt; stall_max(&(peak), stall_us_since(m_)); } while (0)
#else
#define STALL_TIMED(peak, stmt) stmt
#endif
