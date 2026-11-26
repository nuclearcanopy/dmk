#include <assert.h>
#include <stdio.h>
#define MATRIX_COLS 15
#define MATRIX_ROWS 4
#include "scan_cache.h"
#include "scan_transition.h"

int main(void) {
    static hhkb_scan_cache_t cache;
    static rt_key_t keys[MATRIX_COLS][MATRIX_ROWS];
    hhkb_rt_mask_t mask = {{0}}, snapshot;
    rt_cfg_t cfg = {.rt_enabled = true, .act_pm = 500, .press_pm = 50,
                    .release_pm = 100, .reset_pm = 50};
    rt_cfg_t fixed = cfg;
    fixed.rt_enabled = false;
    rt_scan_cfg_t rt, classic;
    uint16_t travel;
    rt_prepare_scan(&rt, &cfg, NULL);
    rt_prepare_scan(&classic, &fixed, NULL);
    for (unsigned c = 0; c < MATRIX_COLS; ++c)
        for (unsigned r = 0; r < MATRIX_ROWS; ++r)
            rt_key_set_range(&keys[c][r], 1000, 2000);

    /* A new snapshot restarts an incremental rebuild. The saved mask cannot
     * change when the writer modifies its own copy during the scan. */
    assert(hhkb_rt_mask_set(&mask, 0, 1));
    snapshot = mask;
    hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &snapshot, 1, 1, 1);
    assert(cache.rebuild_cursor == 2 && cache.key[0][0].rt_member);
    assert(hhkb_rt_mask_set(&mask, 0, 0));
    assert(hhkb_rt_mask_set(&mask, 59, 1));
    assert(hhkb_rt_mask_member(&snapshot, 0, 0));
    hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &snapshot, 1, 1, 1);
    assert(cache.rebuild_cursor == 4 && cache.key[0][0].rt_member);
    snapshot = mask;
    hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &snapshot, 2, 1, 1);
    assert(cache.rebuild_cursor == 2 && !cache.key[0][0].rt_member);
    while (cache.rebuild_cursor < HHKB_SCAN_CACHE_CELLS)
        hhkb_scan_cache_prepare(&cache, keys, &rt, &classic, &snapshot, 2, 1, 1);
    assert(cache.key[14][3].rt_member);

    hhkb_scan_transition_t transition = {0};
    rt_key_t *key = &keys[14][3];
    rt_raw_cache_t *entry = &cache.key[14][3];
    assert(!hhkb_scan_transition(&transition, key, entry, &rt, false, 1000));
    /* Classic key held, then select RT. Timeout and toggles cannot re-arm. */
    key->down = key->latched = true; key->ext = 700; key->lock = 3;
    assert(hhkb_scan_transition(&transition, key, entry, &rt, true, 1700));
    assert(transition.waiting && key->down && key->lock == 3);
    assert(hhkb_scan_transition(&transition, key, entry, &rt, true, UINT16_MAX));
    assert(hhkb_scan_transition(&transition, key, entry, &rt, false, 1700));
    assert(hhkb_scan_transition(&transition, key, entry, &rt, true, 1400));
    assert(transition.waiting);
    assert(hhkb_scan_transition(&transition, key, entry, &rt, true, 1050));
    assert(!transition.waiting && !key->down && !key->latched && !key->ext && !key->lock);
    assert(entry->last_raw == 1050);
    assert(!hhkb_scan_transition(&transition, key, entry, &rt, true, 1500));
    assert(rt_update_scan_sample(key, &rt, 1600, &travel));
    /* RT released logically but latched and physically held, then classic. */
    assert(!rt_update_scan_sample(key, &rt, 1450, &travel));
    assert(key->latched);
    assert(hhkb_scan_transition(&transition, key, entry, &rt, false, 1450));
    assert(transition.waiting);
    assert(hhkb_scan_transition(&transition, key, entry, &rt, false, 1050));
    assert(!transition.waiting && !key->latched);
    assert(!rt_update_scan_sample(key, &classic, 1400, &travel));
    assert(rt_update_scan_sample(key, &classic, 1600, &travel));
    assert(rt_update_scan_sample(key, &classic, 1450, &travel));
    assert(!rt_update_scan_sample(key, &classic, 1300, &travel));
    puts("scan mask transitions: ok");
}
