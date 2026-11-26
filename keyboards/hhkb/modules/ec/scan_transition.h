#ifndef HHKB_SCAN_TRANSITION_H
#define HHKB_SCAN_TRANSITION_H

#include "rapid_trigger.h"

typedef struct {
    uint8_t initialized : 1;
    uint8_t mode : 1;
    uint8_t waiting : 1;
} hhkb_scan_transition_t;

/* A mode change cannot reinterpret an already held key. Even a logically
 * released RT key may still be physically held. */
static inline bool hhkb_scan_transition(hhkb_scan_transition_t *state,
        rt_key_t *key, rt_raw_cache_t *cache, const rt_scan_cfg_t *rt,
        bool mode, uint16_t raw) {
    if (!state->initialized) {
        state->initialized = true;
        state->mode = mode;
    } else if (state->mode != mode) {
        state->mode = mode;
        state->waiting = true;
    }
    if (!state->waiting || raw == UINT16_MAX) return state->waiting;
    if (rt_scan_normalize(key, raw, rt) <= rt->cfg.reset_pm) {
        rt_key_reset(key);
        cache->last_raw = raw;
        state->waiting = false;
    }
    return true;
}
#endif
