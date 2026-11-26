#ifndef HHKB_RT_NOISE_H
#define HHKB_RT_NOISE_H
#include <stdbool.h>
#include <stdint.h>

#ifndef RT_DB_ALPHA_SHIFT
#define RT_DB_ALPHA_SHIFT 5
#endif
#ifndef RT_DB_K_Q4
#define RT_DB_K_Q4 48
#endif
#ifndef RT_DB_MAX_PM
#define RT_DB_MAX_PM 125
#endif
typedef struct {
    uint16_t p1, p2, n_q8;
    uint8_t hist, peak;
} rt_noise_t;
_Static_assert(sizeof(rt_noise_t) == 8, "Unexpected noise state size");

static inline uint16_t rt_noise_db_pm(const rt_noise_t *n) {
    uint32_t db = ((uint32_t)n->n_q8 * RT_DB_K_Q4 + 2048) >> 12;
    return db > RT_DB_MAX_PM ? RT_DB_MAX_PM : (uint16_t)db;
}
static inline void rt_noise_feed(rt_noise_t *n, uint16_t value, bool armed) {
    if (!armed) n->hist = 0;
    if (n->hist >= 2) {
        int32_t d = (int32_t)value - 2 * (int32_t)n->p1 + n->p2;
        if (d < 0) d = -d;
        if (d > 255) d = 255;
        uint16_t target = (uint16_t)(d << 8);
        if (target > n->n_q8) n->n_q8 += (target - n->n_q8) >> RT_DB_ALPHA_SHIFT;
        else n->n_q8 -= (n->n_q8 - target) >> RT_DB_ALPHA_SHIFT;
    }
    n->p2 = n->p1;
    n->p1 = value;
    if (n->hist < 2) ++n->hist;
    uint16_t db = rt_noise_db_pm(n);
    if (db > n->peak) n->peak = db > 255 ? 255 : db;
}
#endif
