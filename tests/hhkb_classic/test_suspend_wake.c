#include <assert.h>
#include <stdbool.h>
#include <stdint.h>

static bool suspended, mounted = true;
static int wake_calls;
bool tud_suspended(void) { return suspended; }
bool tud_mounted(void) { return mounted; }
bool tud_remote_wakeup(void) { ++wake_calls; return true; }
#include "../../keyboards/hhkb/modules/ec/suspend_wake.h"

int main(void) {
    // Not suspended: never wakes.
    hhkb_suspend_wake_note(true);
    assert(!hhkb_suspend_wake_fire(true) && wake_calls == 0);
    // Suspended but host did not enable remote wakeup: never wakes.
    suspended = true;
    hhkb_suspend_wake_note(false);
    assert(!hhkb_suspend_wake_fire(true) && wake_calls == 0);
    // Suspended, enabled, no key: no wake.
    hhkb_suspend_wake_note(true);
    assert(!hhkb_suspend_wake_fire(false) && wake_calls == 0);
    // Suspended, enabled, key: wakes once.
    assert(hhkb_suspend_wake_fire(true) && wake_calls == 1);

    // Poll gating.
    assert(hhkb_suspend_wake_should_poll(true));
    assert(!hhkb_suspend_wake_should_poll(false));
    mounted = false;
    assert(!hhkb_suspend_wake_should_poll(true));
    mounted = true;
    suspended = false;
    assert(!hhkb_suspend_wake_should_poll(true));
    suspended = true;
    hhkb_suspend_wake_note(false);
    assert(!hhkb_suspend_wake_should_poll(true));
    hhkb_suspend_wake_note(true);

    // Edge detection: a key held at suspend entry does not wake.
    uint16_t prev[3] = {0, 4, 0}, cur[3] = {0, 4, 0};
    assert(!hhkb_suspend_wake_edge(cur, prev, 3));
    cur[2] = 1; // new key
    assert(hhkb_suspend_wake_edge(cur, prev, 3));
    assert(!hhkb_suspend_wake_edge(cur, prev, 3)); // still held
    cur[2] = 0; // release is not a wake
    assert(!hhkb_suspend_wake_edge(cur, prev, 3));
    cur[2] = 1; // re-press wakes
    assert(hhkb_suspend_wake_edge(cur, prev, 3));
    return 0;
}
