#ifndef HHKB_IDLE_SCAN_H
#define HHKB_IDLE_SCAN_H

#include <stdbool.h>
#include <stdint.h>

/* Idle slow-scan state machine. Pure logic: no hardware, host-testable.
 * The matrix task feeds it one sample per scan and applies the result to the
 * scan timer. Detection itself stays in hhkb_matrix_scan_raw(): same
 * calibrated threshold and release logic at every rate.
 *
 * Trade-off: at slow period P a press shorter than P can be missed and the
 * first press can be delayed by up to P. */
typedef struct {
    uint32_t last_activity_ms;
    bool slow;
} idle_scan_t;

static inline void idle_scan_init(idle_scan_t *st, uint32_t now_ms) {
    st->last_activity_ms = now_ms;
    st->slow = false;
}

/* key_activity: a key changed state or any key is down. A held key therefore
 * keeps the full rate, and a press seen in slow mode ends it immediately.
 * Calibration needs the full rate and restarts the idle timer.
 * Returns true while the matrix should run at the slow period. */
static inline bool idle_scan_update(idle_scan_t *st, uint32_t now_ms, uint32_t timeout_ms,
                                    bool key_activity, bool calibrating) {
    if (key_activity || calibrating) {
        st->last_activity_ms = now_ms;
        st->slow = false;
    } else if (!st->slow && (uint32_t)(now_ms - st->last_activity_ms) >= timeout_ms) {
        st->slow = true;
    }
    return st->slow;
}

/* Slow timer step is a fixed 10 ms; the ISR divider supplies the period. */
#define IDLE_SCAN_STEP_MS 10U
#define IDLE_SCAN_DIVIDER(period_ms) ((period_ms) / IDLE_SCAN_STEP_MS)

#endif
