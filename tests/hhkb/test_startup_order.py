"""Exercise the production startup and keyboard initialization bodies with host stubs."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from .hhkb_helpers import ROOT, function


class StartupOrderTest(unittest.TestCase):
    def test_compact_production_source_order(self):
        # Inspect preprocessed production function bodies, not runtime behavior:
        # calibration and mask restoration must precede Vial and USB exposure.
        def body(path, signature):
            source = function((ROOT / path).read_text(), signature)
            return subprocess.run(
                ["cc", "-E", "-P", "-x", "c", "-DVIAL=1",
                 "-DHHKB_COMPACT_STORAGE=1", "-DHHKB_RT_KEYMASK=1", "-"],
                input=source, text=True, capture_output=True, check=True,
            ).stdout

        def ordered_calls(source, *names):
            positions = []
            for name in names:
                matches = list(re.finditer(r"\b" + re.escape(name) + r"\s*\(", source))
                self.assertEqual(len(matches), 1, f"expected one call to {name}")
                positions.append(matches[0].start())
            self.assertEqual(positions, sorted(positions), f"incorrect call order: {names}")

        main = body("dmk_core/core/main.c", "int main(void)")
        platform = body("platforms/stm32l072/platform.c", "void platform_init(void)")
        hardware = body("keyboards/hhkb/modules/ec/classic_matrix.c",
                        "void hhkb_matrix_hardware_init(void)")
        calibration = body("keyboards/hhkb/modules/ec/ec_settings.c",
                           "void hhkb_calibration_load(void)")
        mask_init = body("keyboards/hhkb/modules/ec/ec_settings.c",
                         "static void rt_mask_init(void) {")
        keyboard = body("dmk_core/core/keyboard.c", "void keyboard_init(void)")

        ordered_calls(main, "platform_init", "vial_init", "usb_init")
        ordered_calls(platform, "hhkb_matrix_hardware_init")
        ordered_calls(hardware, "hhkb_calibration_load")
        ordered_calls(calibration, "rt_mask_init", "hhkb_compact_load_mask",
                      "hhkb_rt_mask_restore")
        ordered_calls(mask_init, "hhkb_rt_mask_default")
        # Compact storage was already loaded before USB, so later task init
        # must not reload it and overwrite changes made after exposure.
        self.assertNotRegex(keyboard, r"\bvial_init\s*\(")

    def test_compact_and_other_vial_startup(self):
        main = function((ROOT / "dmk_core/core/main.c").read_text(), "int main(void)")
        keyboard = function((ROOT / "dmk_core/core/keyboard.c").read_text(), "void keyboard_init(void)")
        harness = r"""
#include <assert.h>
#include <setjmp.h>
#include <stddef.h>
#include <string.h>
#define VIAL 1
#define configSUPPORT_STATIC_ALLOCATION 0
#define QUEUE_DEF_SIZE 1
#define TASK_STACK_KEYBOARD 1
#define TASK_STACK_MATRIX 1
#define TASK_PRIO_KEYBOARD 2
#define TASK_PRIO_MATRIX 2
#define pdPASS 1
#define pdFAIL 0
#define __NOP() ((void)0)
typedef int BaseType_t;
typedef int matrix_event_t;
static int s_active_keys[1], calibration, loads, exposed, state;
static void *matrix_queue;
static jmp_buf done;
static void platform_init(void) { assert(!exposed); ++calibration; }
static void led_init(void) {}
static void vial_init(void) { assert(calibration == 1); ++loads; state = 7; }
static void usb_init(void) {
    assert(calibration == 1);
#ifdef HHKB_COMPACT_STORAGE
    assert(loads == 1 && state == 7);
#else
    assert(loads == 0);
#endif
    exposed = 1;
}
static void *xQueueCreate(int n, size_t s) { (void)n; (void)s; return &state; }
static void keyboard_task(void *p) { (void)p; }
static void matrix_task(void *p) { (void)p; }
static int xTaskCreate(void (*f)(void *), const char *n, int s, void *p, int prio, void *h) {
    (void)f; (void)n; (void)s; (void)p; (void)prio; (void)h; return pdPASS;
}
static void split_init(void) {}
static void split_common_init(void) {}
static void hooks_dispatch_early_init(void) {}
static void vTaskStartScheduler(void) { longjmp(done, 1); }
static void layers_init(void) {}
static void hold_tap_init(void) {}
static void oneshot_init(void) {}
static void combos_init(void) {}
static void dmk_midi_init(void) {}
static void mouse_init(void) {}
static void gamepad_init(void) {}
static void keyboard_platform_init(void) {}
""" + keyboard + "\n" + main.replace("int main(void)", "int firmware_main(void)") + r"""
int main(void) {
    if (!setjmp(done)) firmware_main();
    assert(exposed && calibration == 1);
#ifdef HHKB_COMPACT_STORAGE
    /* Earliest dispatch occurs after USB exposure, and must survive task init. */
    assert(loads == 1 && state == 7);
    state = 42;
    keyboard_init();
    assert(loads == 1 && state == 42);
#else
    keyboard_init();
    assert(loads == 1 && state == 7);
#endif
    return 0;
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "startup.c"
            source.write_text(harness)
            for compact in (False, True):
                exe = Path(tmp) / "startup"
                flags = ["-DHHKB_COMPACT_STORAGE=1"] if compact else []
                subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                                *flags, str(source), "-o", str(exe)], check=True)
                subprocess.run([str(exe)], check=True)
