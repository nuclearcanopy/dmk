#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "idle_scan.h"

#ifndef TEST_PERIOD_MS
#define TEST_PERIOD_MS 50
#endif
#define TIMEOUT_MS 180000U

/* Model of one matrix-task pass: the scan reports a new key state, the publish
 * step diffs it against what was last published (as matrix.c does), and only
 * then is the idle state updated. Rate/timer are modelled by tick spacing. */
typedef struct {
    idle_scan_t idle;
    uint32_t now_ms;
    uint16_t physical, published;
    unsigned reports;
    uint16_t last_report;
    unsigned scans;
} model_t;

static unsigned step_ms(const model_t *m) {
    return m->idle.slow ? TEST_PERIOD_MS : 1;
}

static void scan(model_t *m, bool calibrating) {
    bool changed = m->physical != m->published;
    if (calibrating) changed = false; /* calibration publishes releases only */
    if (!calibrating && m->physical != m->published) {
        m->published = m->physical;
        m->reports++;
        m->last_report = m->physical;
    }
    idle_scan_update(&m->idle, m->now_ms, TIMEOUT_MS, changed || m->physical != 0, calibrating);
    m->scans++;
}

static void run_until(model_t *m, uint32_t end_ms, bool calibrating) {
    while (m->now_ms < end_ms) {
        m->now_ms += step_ms(m);
        scan(m, calibrating);
    }
}

int main(void) {
    static_assert(IDLE_SCAN_DIVIDER(TEST_PERIOD_MS) * IDLE_SCAN_STEP_MS == TEST_PERIOD_MS,
                  "period must divide into whole slow steps");
    static_assert(IDLE_SCAN_DIVIDER(TEST_PERIOD_MS) >= 1 && IDLE_SCAN_DIVIDER(TEST_PERIOD_MS) <= 255,
                  "divider fits uint8_t");

    { /* (1) timer: full rate before the timeout, slow after it */
        model_t m = {0};
        idle_scan_init(&m.idle, 0);
        run_until(&m, TIMEOUT_MS - 1, false);
        assert(!m.idle.slow);
        run_until(&m, TIMEOUT_MS, false);
        assert(m.idle.slow);
        uint32_t before = m.scans;
        run_until(&m, TIMEOUT_MS + 1000, false);
        assert(m.scans - before == 1000 / TEST_PERIOD_MS); /* slow cadence */
    }
    { /* activity resets the idle timer */
        model_t m = {0};
        idle_scan_init(&m.idle, 0);
        run_until(&m, TIMEOUT_MS - 10, false);
        m.physical = 1; run_until(&m, m.now_ms + 20, false);
        m.physical = 0; run_until(&m, m.now_ms + 20, false);
        assert(!m.idle.slow);
        run_until(&m, m.now_ms + TIMEOUT_MS - 100, false);
        assert(!m.idle.slow);
        run_until(&m, m.now_ms + 200, false);
        assert(m.idle.slow);
    }
    { /* (2) wake: new press in slow mode reports and restores full rate */
        model_t m = {0};
        idle_scan_init(&m.idle, 0);
        run_until(&m, TIMEOUT_MS + 5000, false);
        assert(m.idle.slow && m.reports == 0);
        m.physical = 0x0004;
        uint32_t press_ms = m.now_ms;
        run_until(&m, m.now_ms + TEST_PERIOD_MS, false);
        assert(m.reports == 1 && m.last_report == 0x0004); /* first press not lost */
        assert(!m.idle.slow);
        assert(m.now_ms - press_ms <= TEST_PERIOD_MS);      /* delay <= P */
        uint32_t before = m.scans;
        run_until(&m, m.now_ms + 10, false);
        assert(m.scans - before == 10);                     /* 1 kHz again */
    }
    { /* (3) key held across the switch is not reported twice */
        model_t m = {0};
        idle_scan_init(&m.idle, 0);
        m.physical = 0x0010;
        run_until(&m, 10, false);
        assert(m.reports == 1);
        run_until(&m, TIMEOUT_MS * 3, false); /* held: never idle */
        assert(!m.idle.slow && m.reports == 1);
        m.physical = 0; run_until(&m, m.now_ms + 5, false);
        assert(m.reports == 2 && m.last_report == 0);       /* the release only */
        run_until(&m, m.now_ms + TIMEOUT_MS, false);
        assert(m.idle.slow);
        m.physical = 0x0010;
        run_until(&m, m.now_ms + TEST_PERIOD_MS, false);
        assert(m.reports == 3);
        run_until(&m, m.now_ms + 1000, false);              /* still held at full rate */
        assert(m.reports == 3 && !m.idle.slow);
    }
    { /* (4) calibration blocks slow mode and restarts the timer */
        model_t m = {0};
        idle_scan_init(&m.idle, 0);
        run_until(&m, TIMEOUT_MS * 2, true);
        assert(!m.idle.slow);
        run_until(&m, m.now_ms + TIMEOUT_MS - 1, false);
        assert(!m.idle.slow);
        run_until(&m, m.now_ms + 2, false);
        assert(m.idle.slow);
        /* calibration starting while slow leaves slow mode at once */
        scan(&m, true);
        assert(!m.idle.slow);
    }
    { /* tick counter wrap */
        idle_scan_t st;
        idle_scan_init(&st, UINT32_MAX - 100);
        assert(!idle_scan_update(&st, 1000, 5000, false, false));
        assert(idle_scan_update(&st, UINT32_MAX - 100 + 5000, 5000, false, false));
    }
    return 0;
}
