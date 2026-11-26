#pragma once
// Wake-on-key while the USB host has suspended the device and keyboard power
// saving has cut sensor power. The matrix task powers the sensor briefly every
// HHKB_SUSPEND_WAKE_PERIOD_MS, scans once, and asks the host to resume when a
// key became pressed since the previous poll.
#include <stdbool.h>
#include <stdint.h>
#include "tusb.h"

// Poll period: shorter than a quick tap (~60-100 ms) so taps are seen.
#ifndef HHKB_SUSPEND_WAKE_PERIOD_MS
#define HHKB_SUSPEND_WAKE_PERIOD_MS 50
#endif
// Analog power settle, same constant the resume path uses.
#ifndef HHKB_SUSPEND_WAKE_SETTLE_MS
#define HHKB_SUSPEND_WAKE_SETTLE_MS 10
#endif

// Host's Remote Wakeup feature state, latched from tud_suspend_cb().
static volatile bool s_suspend_wake_host_enabled;

static inline void hhkb_suspend_wake_note(bool remote_wakeup_en) {
    s_suspend_wake_host_enabled = remote_wakeup_en;
}

// Poll only when a wake could be delivered.
static inline bool hhkb_suspend_wake_should_poll(bool power_saving) {
    return power_saving && tud_mounted() && tud_suspended() &&
           s_suspend_wake_host_enabled;
}

// True when `cur` has a key down that `prev` did not. `prev` is updated, so a
// key held (or stuck) at suspend entry never wakes the host repeatedly.
static inline bool hhkb_suspend_wake_edge(const uint16_t *cur, uint16_t *prev,
                                          uint8_t rows) {
    bool pressed = false;
    for (uint8_t r = 0; r < rows; ++r) {
        if (cur[r] & (uint16_t)~prev[r]) pressed = true;
        prev[r] = cur[r];
    }
    return pressed;
}

// Resume the host only if suspended and the host enabled remote wakeup.
static inline bool hhkb_suspend_wake_fire(bool pressed) {
    if (!pressed || !tud_suspended() || !s_suspend_wake_host_enabled) return false;
    return tud_remote_wakeup();
}
