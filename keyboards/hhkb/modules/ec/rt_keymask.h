#ifndef HHKB_RT_KEYMASK_H
#define HHKB_RT_KEYMASK_H

#include "rapid_trigger.h"
#include <string.h>

#define HHKB_RT_KEY_COUNT 7
#define HHKB_RT_MASK_BITS 60
#define HHKB_RT_MASK_BYTES 8
typedef struct {
    uint8_t bytes[HHKB_RT_MASK_BYTES];
} hhkb_rt_mask_t;

static inline bool hhkb_rt_mask_get(const hhkb_rt_mask_t *mask, unsigned index) {
    return index < HHKB_RT_MASK_BITS && (mask->bytes[index / 8] & (1u << (index % 8))) != 0;
}

static inline bool hhkb_rt_mask_set(hhkb_rt_mask_t *mask, unsigned index, unsigned value) {
    if (index >= HHKB_RT_MASK_BITS || value > 1) return false;
    uint8_t bit = (uint8_t)(1u << (index % 8));
    if (value) mask->bytes[index / 8] |= bit;
    else mask->bytes[index / 8] &= (uint8_t)~bit;
    return true;
}

static inline bool hhkb_rt_mask_member(const hhkb_rt_mask_t *mask, unsigned col, unsigned row) {
    return col < MATRIX_COLS && row < MATRIX_ROWS &&
           hhkb_rt_mask_get(mask, col * MATRIX_ROWS + row);
}

static inline bool hhkb_rt_mask_valid(const hhkb_rt_mask_t *mask) {
    return (mask->bytes[7] & 0xf0u) == 0;
}

static inline bool hhkb_rt_mask_equal(const hhkb_rt_mask_t *a, const hhkb_rt_mask_t *b) {
    return memcmp(a->bytes, b->bytes, HHKB_RT_MASK_BYTES) == 0;
}

/* Full board: all 60 positions set, byte 7 high nibble kept clear so
 * hhkb_rt_mask_valid() stays true. */
static inline void hhkb_rt_mask_full(hhkb_rt_mask_t *mask) {
    memset(mask->bytes, 0xFF, HHKB_RT_MASK_BYTES - 1);
    mask->bytes[HHKB_RT_MASK_BYTES - 1] =
        (uint8_t)((1u << (HHKB_RT_MASK_BITS % 8)) - 1);
}

/* "Full" is the byte-exact canonical pattern: all 60 positions set and the
 * reserved nibble clear, so is_full implies hhkb_rt_mask_valid(). Reserved
 * nibble garbage disqualifies a mask; hhkb_rt_mask_restore() then treats it
 * as "anything else" and normalizes to the default. */
static inline bool hhkb_rt_mask_is_full(const hhkb_rt_mask_t *mask) {
    if (!hhkb_rt_mask_valid(mask)) return false;
    for (unsigned i = 0; i < HHKB_RT_MASK_BITS; ++i)
        if (!hhkb_rt_mask_get(mask, i)) return false;
    return true;
}

#define HHKB_RT_KEYS(X) \
    X(1,2,0) X(3,3,1) X(1,3,2) X(2,3,3) \
    X(6,0,4) X(0,0,5) X(0,3,6)

_Static_assert(MATRIX_COLS == 15 && MATRIX_ROWS == 4, "Unexpected HHKB matrix");
_Static_assert(HHKB_RT_KEY_COUNT <= MATRIX_COLS * MATRIX_ROWS, "Invalid RT key count");
static inline void hhkb_rt_mask_default(hhkb_rt_mask_t *mask) {
    memset(mask->bytes, 0, sizeof(mask->bytes));
#define HHKB_RT_DEFAULT_SET(c,r,s) (void)hhkb_rt_mask_set(mask, (c) * MATRIX_ROWS + (r), 1);
    HHKB_RT_KEYS(HHKB_RT_DEFAULT_SET)
#undef HHKB_RT_DEFAULT_SET
}

static inline bool hhkb_rt_mask_is_default(const hhkb_rt_mask_t *mask) {
    hhkb_rt_mask_t def;
    hhkb_rt_mask_default(&def);
    return hhkb_rt_mask_equal(mask, &def);
}
#define HHKB_RT_SLOT_INIT(c,r,s) [(c) * MATRIX_ROWS + (r)] = (s) + 1,
static const uint8_t hhkb_rt_slot1[MATRIX_COLS * MATRIX_ROWS] = {
    HHKB_RT_KEYS(HHKB_RT_SLOT_INIT)
};
#undef HHKB_RT_SLOT_INIT

static inline uint8_t hhkb_rt_slot1_of(uint8_t col, uint8_t row) {
    return hhkb_rt_slot1[col * MATRIX_ROWS + row];
}

static inline const rt_scan_cfg_t *hhkb_rt_select_cfg(bool member,
        const rt_scan_cfg_t *scan, const rt_scan_cfg_t *classic) {
    return member && scan->cfg.rt_enabled ? scan : classic;
}
#endif
