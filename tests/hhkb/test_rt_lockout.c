/* Host test for the leading-edge RT lockout; run via tests/run_all_tests.sh. */
#include "rapid_trigger.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

#define BASE 800
#define PEAK 1800 /* 1 count == 1 permille */

static rt_key_t key;

static void lk_reset(void) { rt_key_set_range(&key, BASE, PEAK); rt_key_reset(&key); }

/* One scan through the lockout, mirroring scan_process_pending. */
static bool step(bool in, bool *rep, uint8_t n) { *rep = rt_lockout(&key, in, *rep, n); return *rep; }

static unsigned rnd(void) { static uint64_t s = 88172645463325252ULL; s ^= s << 13; s ^= s >> 7; s ^= s << 17; return (unsigned)(s >> 32); }

int main(void) {
    bool rep;
    _Static_assert(sizeof(rt_key_t) == 12, "layout");

    /* a) first edge reported in the same scan. */
    lk_reset(); rep = false;
    assert(step(true, &rep, 15));

    /* b) press, RT release at +2, re-press at +5: stays down. */
    lk_reset(); rep = false;
    bool in[40] = {0};
    for (int t = 0; t < 40; t++) in[t] = (t < 2) || (t >= 5);
    int edges = 0; bool prev = false;
    for (int t = 0; t < 40; t++) { step(in[t], &rep, 15); if (rep != prev) edges++; prev = rep; }
    assert(edges == 1 && rep);

    /* c) release then bounce press/release within n: suppressed. */
    lk_reset(); rep = true; key.lock = 0;
    assert(!step(false, &rep, 15));              /* t0 release reported */
    for (int t = 1; t < 15; t++) assert(!step(t == 3 || t == 4 ? true : false, &rep, 15) && !rep);

    /* d) real 6-scan tap: release reported exactly at t+n. */
    lk_reset(); rep = false;
    int rel_at = -1;
    for (int t = 0; t < 60; t++) {
        bool v = t < 6;
        step(v, &rep, 15);
        if (t == 0) assert(rep);
        if (t > 0 && !rep && rel_at < 0) rel_at = t;
        if (t < 15) assert(rep == true);
    }
    assert(rel_at == 15 && !rep);

    /* e) mid-hold glitch: release is immediate, re-press waits until t+n (limitation:
     * a held key drops for up to n-1 scans when the lockout was idle). */
    lk_reset(); rep = true;
    assert(!step(false, &rep, 15));
    for (int t = 1; t < 15; t++) assert(!step(true, &rep, 15));
    assert(step(true, &rep, 15));                /* scan t+15 */

    /* f) random sequences. */
    static const uint8_t ns[] = {0, 1, 2, 10, 15};
    for (unsigned ni = 0; ni < sizeof ns; ni++) {
        uint8_t n = ns[ni], gap = n ? n : 1;
        lk_reset(); rep = false;
        bool input = false, prevrep = false;
        int last_edge = -1000, stable = 0, quiet = 1000;
        for (int t = 0; t < 100000; t++) {
            bool flip = (rnd() % (1 + (rnd() % 4 == 0 ? 3 : 40))) == 0;
            bool prev_in = input;
            if (flip) input = !input;
            stable = input == prev_in ? stable + 1 : 0;
            step(input, &rep, n);
            if (rep != prevrep) {
                assert(t - last_edge >= gap);
                if (quiet >= n) assert(rep == input);   /* zero delay after quiet */
                last_edge = t; quiet = 0;
            } else quiet++;
            if (t - last_edge >= n && stable >= n) assert(rep == input);
            prevrep = rep;
        }
    }

    /* g) rt_key_reset clears lock. */
    lk_reset(); rep = false; step(true, &rep, 15);
    assert(key.lock == 15);
    rt_key_reset(&key);
    assert(key.lock == 0);

    /* h) n = 0 and 1 match input exactly. */
    for (int n = 0; n <= 1; n++) {
        lk_reset(); rep = false;
        for (int t = 0; t < 100000; t++) {
            bool v = rnd() & 1;
            assert(step(v, &rep, (uint8_t)n) == v);
        }
    }

    /* i) bottom-out +/-noise traces through real RT, then lockout. */
    static const int pms[] = {25, 100};
    for (unsigned pi = 0; pi < 2; pi++) {
        rt_cfg_t cfg;
        rt_cfg_defaults(&cfg);
        cfg.rt_enabled = true;
        cfg.press_pm = cfg.release_pm = (uint16_t)pms[pi];
        lk_reset(); rep = false;
        int raw_edges = 0, out_edges = 0, last = -1000;
        bool praw = false, pout = false;
        for (int t = 0; t < 400; t++) {
            int pm = t < 20 ? 0 : t < 40 ? 1000 : 1000 - 150 * (t - 40) / 60; /* press, then slow release */
            if (t >= 20 && t < 140) pm = 1000;            /* bottomed out */
            else if (t >= 140 && t < 200) pm = 1000 - 15 * (t - 140);
            else if (t >= 200) pm = 0;
            if (t >= 20 && t < 140) pm += (int)(rnd() % (2 * (unsigned)pms[pi] + 1)) - pms[pi] - (pms[pi] > 50 ? 0 : 0);
            if (pm < 0) pm = 0;
            bool d = rt_update(&key, &cfg, (uint16_t)(BASE + pm));
            if (d != praw) raw_edges++;
            praw = d;
            step(d, &rep, 15);
            if (rep != pout) { out_edges++; assert(t - last >= 15); last = t; }
            pout = rep;
        }
        assert(out_edges <= raw_edges);
        assert(!rep);                                      /* ends released */
        assert(out_edges >= 2);                            /* real press and release got through */
    }
    puts("rt_lockout: ok");
    return 0;
}
