#include <assert.h>
#include <stdio.h>
#include "rapid_trigger.h"

int main(void) {
    rt_noise_t n = {0};
    for (unsigned i = 0; i < 1000; ++i) rt_noise_feed(&n, 500, true);
    assert(n.n_q8 == 0 && rt_noise_db_pm(&n) == 0);
    n = (rt_noise_t){0};
    for (unsigned i = 0; i < 100; ++i) rt_noise_feed(&n, i * 5, true);
    assert(n.n_q8 == 0);
    n = (rt_noise_t){0};
    for (unsigned i = 0; i < 400; ++i) rt_noise_feed(&n, 500 + (i & 1) * 4, true);
    assert(rt_noise_db_pm(&n) == 24);
    for (unsigned i = 0; i < 400; ++i) rt_noise_feed(&n, (i & 1) * 1000, true);
    assert(rt_noise_db_pm(&n) == 125);
    uint16_t saved = n.n_q8;
    rt_noise_feed(&n, 300, false);
    assert(n.n_q8 == saved && n.hist == 1);

    rt_key_t a = {0}, b = {0};
    rt_key_set_range(&a, 800, 1800);
    b = a;
    rt_cfg_t cfg;
    rt_cfg_defaults(&cfg);
    cfg.rt_enabled = true;
    rt_scan_cfg_t scan;
    rt_prepare_scan(&scan, &cfg, NULL);
    /* A stable armed key has zero estimated noise and identical RT output. */
    for (unsigned i = 0; i < 1000; ++i) {
        uint16_t travel;
        bool x = rt_update_scan_sample(&a, &scan, 1650, &travel);
        bool y = rt_update_scan_sample_db(&b, &n, &scan, 1650, &travel, false);
        assert(x == y && a.down == b.down && a.ext == b.ext && a.latched == b.latched);
    }
    rt_key_reset(&a);
    rt_key_reset(&b);
    n = (rt_noise_t){0};
    for (unsigned i = 0; i < 1000; ++i) {
        uint16_t raw = 800 + (i % 1000), t;
        bool x = rt_update_scan_sample(&a, &scan, raw, &t);
        bool y = rt_update_scan_sample_db(&b, &n, &scan, raw, &t, false);
#if HHKB_RT_DEADBAND == 2
        assert(x == y && a.down == b.down && a.ext == b.ext && a.latched == b.latched);
#else
        (void)x; (void)y;
#endif
    }
    rt_key_reset(&a);
    rt_key_reset(&b);
    rt_noise_t other = {0};
    n = (rt_noise_t){0};
    for (unsigned i = 0; i < 2000; ++i) {
        uint16_t raw = 1500 + ((i * 73) % 300), t;
        bool x = rt_update_scan_sample_db(&a, &n, &scan, raw, &t, false);
        bool y = rt_update_scan_sample_db(&b, &other, &scan, raw, &t, true);
        assert(x == y && a.down == b.down && a.ext == b.ext && a.latched == b.latched);
        assert(n.n_q8 == other.n_q8);
    }
    puts("RT noise tests passed");
    return 0;
}
