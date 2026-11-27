#include <assert.h>
#include <stdint.h>
#include <string.h>
#define EC_SETTINGS_MASK_HOST_TEST
#include "../../keyboards/hhkb/modules/ec/ec_settings.c"

static unsigned depth, enters, exits;
#if HHKB_RT_KEYMASK
static bool pending;
#endif
void test_enter(void) { assert(depth == 0); depth++; enters++; }
void test_exit(void) {
    assert(depth == 1);
    depth--; exits++;
#if HHKB_RT_KEYMASK
    if (pending) {
        pending = false;
        assert(hhkb_rt_key_set(59, 1) == HHKB_RT_MASK_CHANGED);
        s_rt_cfg.act_pm = 900;
    }
#endif
}

int main(void) {
#if HHKB_RT_KEYMASK
    rt_mask_init();
    hhkb_scan_snapshot_t snap;
    hhkb_get_scan_snapshot(&snap);
    assert(snap.revision == 0 && hhkb_rt_mask_valid(&snap.mask));
    unsigned count = 0;
    for (unsigned i = 0; i < 60; ++i) {
        bool value = false;
        assert(hhkb_rt_key_get(i, &value));
        assert(value == (i == 0 || i == 3 || i == 6 || i == 7 ||
                         i == 11 || i == 15 || i == 24));
        count += value;
    }
    assert(count == 7);
    assert(!hhkb_rt_mask_take_storage_event());
    assert(hhkb_rt_key_set(0, 1) == HHKB_RT_MASK_UNCHANGED);
    assert(hhkb_rt_key_set(60, 1) == HHKB_RT_MASK_INVALID);
    assert(!hhkb_rt_mask_take_storage_event());
    for (unsigned i = 0; i < 60; ++i) {
        bool old;
        assert(hhkb_rt_key_get(i, &old));
        uint32_t before = s_rt_mask_revision;
        assert(hhkb_rt_key_set(i, old) == HHKB_RT_MASK_UNCHANGED);
        assert(hhkb_rt_key_set(i, !old) == HHKB_RT_MASK_CHANGED);
        assert(s_rt_mask_revision == before + 1);
        bool now;
        assert(hhkb_rt_key_get(i, &now) && now == !old);
        assert(hhkb_rt_key_set(i, old) == HHKB_RT_MASK_CHANGED);
    }
    uint32_t revision = s_rt_mask_revision;
    assert(hhkb_rt_key_set(60, 1) == HHKB_RT_MASK_INVALID);
    assert(hhkb_rt_key_set(0, 2) == HHKB_RT_MASK_INVALID);
    assert(!hhkb_rt_key_get(60, &(bool){false}));
    assert(!hhkb_rt_key_get(0, NULL));
    assert(revision == s_rt_mask_revision && !s_settings_dirty);
    assert(hhkb_rt_mask_take_storage_event());
    assert(!hhkb_rt_mask_take_storage_event());
    s_rt_mask_revision = UINT32_MAX;
    assert(hhkb_rt_key_set(59, 1) == HHKB_RT_MASK_CHANGED);
    assert(s_rt_mask_revision == 0);
    assert(hhkb_rt_key_set(59, 0) == HHKB_RT_MASK_CHANGED);

    // 3-way Rapid Trigger mode: off, seven-key, full, round trip, validity.
    assert(!s_rt_cfg.rt_enabled && hhkb_rt_mask_is_default(&s_rt_mask));
    assert(hhkb_rt_mode_get() == 0);
    assert(hhkb_rt_mode_set(1));
    assert(hhkb_rt_mode_get() == 1 && s_rt_cfg.rt_enabled);
    assert(hhkb_rt_mask_is_default(&s_rt_mask));
    assert(hhkb_rt_mode_set(2));
    assert(hhkb_rt_mode_get() == 2 && s_rt_cfg.rt_enabled);
    assert(hhkb_rt_mask_is_full(&s_rt_mask) && hhkb_rt_mask_valid(&s_rt_mask));
    assert(!hhkb_rt_mode_set(2)); // full again: no change
    assert(hhkb_rt_mode_get() == 2);
    assert(hhkb_rt_mode_set(1));
    assert(hhkb_rt_mode_get() == 1 && hhkb_rt_mask_is_default(&s_rt_mask));
    assert(!hhkb_rt_mode_set(3)); // invalid mode rejected
    assert(hhkb_rt_mode_get() == 1);
    assert(hhkb_rt_mode_set(0));
    assert(hhkb_rt_mode_get() == 0 && !s_rt_cfg.rt_enabled);

    // Restore normalizes legacy custom masks, keeps the full mask.
    {
        hhkb_rt_mask_t custom;
        hhkb_rt_mask_default(&custom);
        (void)hhkb_rt_mask_set(&custom, 1, 1); // one extra non-default bit
        hhkb_rt_mask_restore(&custom);
        assert(hhkb_rt_mask_is_default(&s_rt_mask));
        hhkb_rt_mask_full(&custom);
        hhkb_rt_mask_restore(&custom);
        assert(hhkb_rt_mask_is_full(&s_rt_mask));
        hhkb_rt_mask_default(&custom);
        hhkb_rt_mask_restore(&custom);
        assert(hhkb_rt_mask_is_default(&s_rt_mask));
    }

    s_rt_cfg = (rt_cfg_t){.rt_enabled = true, .act_pm = 750,
                          .press_pm = 25, .release_pm = 50};
    s_classic_release_pm = 175;
    for (unsigned enabled = 0; enabled < 2; ++enabled) {
        for (unsigned calibrated = 0; calibrated < 2; ++calibrated) {
            s_rt_cfg.rt_enabled = enabled;
            s_custom_calibration = calibrated;
            rt_cfg_t rt, classic, single;
            hhkb_get_scan_cfgs(&rt, &classic);
            single = hhkb_get_scan_cfg();
            hhkb_get_scan_snapshot(&snap);
            assert(memcmp(&rt, &snap.rt, sizeof(rt)) == 0);
            assert(memcmp(&classic, &snap.classic, sizeof(classic)) == 0);
            assert(memcmp(&single, &rt, sizeof(rt)) == 0);
            assert(!classic.rt_enabled && classic.release_pm == 175);
            assert(rt.release_pm == (!enabled ? 175 : calibrated ? 50 : 100));
            assert(rt.press_pm == (enabled && !calibrated ? 100 : 25));
        }
    }
    s_rt_cfg.act_pm = 750;
    revision = s_rt_mask_revision;
    pending = true;
    hhkb_get_scan_snapshot(&snap);
    assert(!pending && snap.rt.act_pm == 750 && !hhkb_rt_mask_get(&snap.mask, 59));
    assert(snap.revision == revision);
    hhkb_get_scan_snapshot(&snap);
    assert(snap.rt.act_pm == 900 && hhkb_rt_mask_get(&snap.mask, 59));
    assert(snap.revision == revision + 1 && !s_settings_dirty);
#else
    s_rt_cfg.rt_enabled = true;
    s_rt_cfg.press_pm = 25;
    s_rt_cfg.release_pm = 25;
    s_custom_calibration = false;
    rt_cfg_t cfg = hhkb_get_scan_cfg();
    assert(cfg.press_pm == 100 && cfg.release_pm == 100);
    assert(!s_settings_dirty);
#endif
    assert(depth == 0 && enters == exits);
    return 0;
}
