#include <assert.h>
#include <stdio.h>
#define MATRIX_COLS 15
#define MATRIX_ROWS 4
#include "scan_cache.h"

int main(void) {
    static hhkb_scan_cache_t cache;
    static rt_key_t keys[MATRIX_COLS][MATRIX_ROWS];
    const uint8_t expected[7][2] = {{1,2},{3,3},{1,3},{2,3},{6,0},{0,0},{0,3}};
    hhkb_rt_mask_t mask, copy;
    hhkb_rt_mask_default(&mask);
    copy = mask;
    assert(hhkb_rt_mask_valid(&mask) && hhkb_rt_mask_equal(&mask, &copy));
    for (unsigned i = 0; i < 60; ++i) {
        bool expected_member = false;
        for (unsigned j = 0; j < 7; ++j)
            expected_member |= i == expected[j][0] * MATRIX_ROWS + expected[j][1];
        assert(hhkb_rt_mask_get(&mask, i) == expected_member);
        assert(hhkb_rt_mask_member(&mask, i / MATRIX_ROWS, i % MATRIX_ROWS) == expected_member);
        assert(hhkb_rt_mask_set(&copy, i, 1));
        assert(hhkb_rt_mask_get(&copy, i));
        assert(hhkb_rt_mask_set(&copy, i, 0));
        assert(!hhkb_rt_mask_get(&copy, i));
    }
    assert(!hhkb_rt_mask_set(&copy, 60, 1));
    assert(!hhkb_rt_mask_set(&copy, 0, 2));
    assert(!hhkb_rt_mask_get(&copy, 60));
    assert(!hhkb_rt_mask_member(&copy, MATRIX_COLS, 0));
    assert(!hhkb_rt_mask_member(&copy, 0, MATRIX_ROWS));
    assert(hhkb_rt_mask_is_default(&mask));
    assert(!hhkb_rt_mask_is_full(&mask));
    hhkb_rt_mask_full(&copy);
    assert(hhkb_rt_mask_is_full(&copy) && hhkb_rt_mask_valid(&copy));
    assert(!hhkb_rt_mask_is_default(&copy));
    for (unsigned i = 0; i < 60; ++i) assert(hhkb_rt_mask_get(&copy, i));
    copy.bytes[7] = 0xf0;
    assert(!hhkb_rt_mask_valid(&copy));
    unsigned seen = 0;
    for (unsigned c = 0; c < MATRIX_COLS; ++c)
        for (unsigned r = 0; r < MATRIX_ROWS; ++r) {
            uint8_t slot = hhkb_rt_slot1_of(c, r);
            if (slot) {
                assert(slot <= 7 && !(seen & (1u << (slot - 1))));
                assert(expected[slot-1][0] == c && expected[slot-1][1] == r);
                seen |= 1u << (slot-1);
            }
            rt_key_set_range(&keys[c][r], 800, 1800);
        }
    assert(seen == 127 && sizeof(rt_raw_cache_t) == 8);
    rt_cfg_t cfg;
    rt_cfg_defaults(&cfg);
    cfg.rt_enabled = true;
    cfg.act_pm = 750;
    cfg.release_pm = 30;
    rt_scan_cfg_t rt, classic;
    rt_prepare_scan(&rt, &cfg, NULL);
    cfg.rt_enabled = false;
    cfg.release_pm = 200;
    rt_prepare_scan(&classic, &cfg, NULL);
    for (int i = 0; i < 30; ++i)
        hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &mask, 0, 1, 1);
    assert(cache.rebuild_cursor == 60);
    assert(cache.key[1][2].rt_member && !cache.key[2][2].rt_member);
    assert(hhkb_rt_select_cfg(true, &rt, &classic) == &rt);
    assert(hhkb_rt_select_cfg(false, &rt, &classic) == &classic);
    uint16_t old = cache.key[2][2].release_raw;
    cfg.release_pm = 400;
    rt_prepare_scan(&classic, &cfg, NULL);
    hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &mask, 0, 1, 1);
    assert(cache.rebuild_cursor == 2);
    for (int i = 0; i < 29; ++i)
        hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &mask, 0, 1, 1);
    assert(cache.key[2][2].release_raw < old);
    rt.cfg.rt_enabled = false;
    assert(hhkb_rt_select_cfg(true, &rt, &classic) == &classic);
    hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &mask, 0, 1, 1);
    cache.key[1][2].last_raw = 1400;
    cache.key[2][2].last_raw = 1500;
    keys[2][2].ext = 123;
    rt.cfg.rt_enabled = true;
    hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &mask, 0, 1, 1);
    assert(keys[1][2].ext == 600 && keys[2][2].ext == 123);
    /* Frequent slider invalidation must not expose stale cache membership or
       classic thresholds while the cursor is partway through the sweep. */
    static rt_key_t reference[MATRIX_COLS][MATRIX_ROWS];
    for (unsigned c = 0; c < MATRIX_COLS; ++c)
        for (unsigned r = 0; r < MATRIX_ROWS; ++r) {
            rt_key_reset(&keys[c][r]);
            reference[c][r] = keys[c][r];
        }
    unsigned random = 1234567;
    for (unsigned pass = 0; pass < 500; ++pass) {
        if (pass && pass % 37 == 0) {
            bool enable = !rt.cfg.rt_enabled;
            if (enable) {
                for (unsigned c = 0; c < MATRIX_COLS; ++c)
                    for (unsigned r = 0; r < MATRIX_ROWS; ++r)
                        if (hhkb_rt_slot1_of(c, r)) {
                            uint16_t v = rt_scan_normalize(&reference[c][r], cache.key[c][r].last_raw, &rt);
                            reference[c][r].ext = v > RT_FULL_SCALE ? RT_FULL_SCALE : v;
                        }
            }
            rt.cfg.rt_enabled = enable;
        }
        if (pass % 7 == 0) {
            cfg.release_pm = 100 + (pass % 200);
            rt_prepare_scan(&classic, &cfg, NULL);
        }
        hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &mask, 0, 1, 1);
        for (unsigned c = 0; c < MATRIX_COLS; ++c)
            for (unsigned r = 0; r < MATRIX_ROWS; ++r) {
                bool valid = hhkb_scan_cache_entry_valid(&cache, c, r);
                bool member = valid ? cache.key[c][r].rt_member : hhkb_rt_slot1_of(c, r);
                const rt_scan_cfg_t *selected = hhkb_rt_select_cfg(member, &rt, &classic);
                random = random * 1664525u + 1013904223u;
                uint16_t raw = 800 + ((random >> 16) % 1100), travel;
                bool expected_down = rt_update_scan_sample(&reference[c][r], selected, raw, &travel);
                bool actual;
                if (!valid) {
                    actual = rt_update_scan_sample(&keys[c][r], selected, raw, &travel);
                    if (!selected->cfg.rt_enabled) cache.key[c][r].last_raw = raw;
                } else if (selected->cfg.rt_enabled)
                    actual = rt_update_scan_cached(&keys[c][r], &cache.key[c][r], selected, raw, NULL);
                else actual = rt_update_raw_cached(&keys[c][r], &cache.key[c][r], raw);
                assert(actual == expected_down);
                assert(keys[c][r].down == reference[c][r].down);
                assert(keys[c][r].latched == reference[c][r].latched);
                if (!selected->cfg.rt_enabled) assert(cache.key[c][r].last_raw == raw);
            }
    }
    puts("RT key mask and cache tests passed");
    return 0;
}
