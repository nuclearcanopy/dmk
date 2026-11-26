"""Exercise the production debounce with a task deferred at the critical section."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from .hhkb_helpers import ROOT, function


class StorageDebounceTest(unittest.TestCase):
    def test_save_request_survives_consumer_clear(self):
        source = (ROOT / "dmk_core/features/vial.c").read_text()
        save = function(source, "void vial_eeprom_save(void)")
        task = function(source, "void vial_eeprom_task(void)")
        task = task.replace("if (save) s_eeprom_dirty = false;",
                            "if (save) { deferred = true; s_eeprom_dirty = false; }")
        code = r'''
#include <assert.h>
#include <stdbool.h>
typedef unsigned TickType_t;
#define pdMS_TO_TICKS(x) (x)
#define VIAL_EEPROM_SAVE_DELAY_MS 10
static bool s_eeprom_dirty, deferred, locked;
static unsigned s_eeprom_dirty_time, ticks, saves;
static unsigned xTaskGetTickCount(void) { return ticks; }
void vial_eeprom_save(void);
static void enter(void) { assert(!locked); locked=true; }
static void leave(void) {
    assert(locked); locked=false;
    if (deferred) { deferred=false; ticks=25; vial_eeprom_save(); }
}
#define taskENTER_CRITICAL() enter()
#define taskEXIT_CRITICAL() leave()
static void vial_keyboard_eeprom_task(void) {}
static void vial_platform_storage_poll(void) {}
static void vial_eeprom_save_now(void) { ++saves; }
''' + save + task + r'''
int main(void) {
    ticks=1; vial_eeprom_save(); ticks=20; vial_eeprom_task();
    assert(saves==1 && s_eeprom_dirty && s_eeprom_dirty_time==25);
    ticks=34; vial_eeprom_task(); assert(saves==1 && s_eeprom_dirty);
    ticks=35; vial_eeprom_task(); assert(saves==2);
}
'''
        # Only inject the competing task during the first clear.
        code = code.replace("deferred = true; s_eeprom_dirty = false;",
                            "if (!saves) deferred = true; s_eeprom_dirty = false;")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "debounce.c"
            exe = Path(tmp) / "debounce"
            src.write_text(code)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(src), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
