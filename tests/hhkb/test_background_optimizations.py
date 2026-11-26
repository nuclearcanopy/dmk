"""Exercise production wait policies and SSP DMA sequencing with host peripherals."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from .hhkb_helpers import ROOT, function


def run_c(code):
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'test.c'
        out = Path(tmp) / 'test'
        src.write_text(code)
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(src), '-o', str(out)], check=True)
        subprocess.run([str(out)], check=True)


class BackgroundOptimizationTest(unittest.TestCase):
    def test_eeprom_wait_tracks_settings_and_incremental_writes(self):
        source = (ROOT / 'dmk_core/features/vial.c').read_text()
        settings = (ROOT / 'keyboards/hhkb/modules/ec/ec_settings.c').read_text()
        compact = (ROOT / 'keyboards/hhkb/modules/via_settings/hhkb_compact_storage.inc').read_text()
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
typedef unsigned TickType_t;
#define pdMS_TO_TICKS(x) (x)
#define VIA_FULL_SETTINGS_RESET
#define C_RESET 42
#define taskENTER_CRITICAL() ((void)0)
#define taskEXIT_CRITICAL() ((void)0)
static bool s_reset_pending,s_eeprom_dirty,s_settings_dirty,c_pending,c_packing,c_mutation_event;
static int c_target=-1,c_active=-1;
static bool c_abandoned,c_blocked,c_keymap_ready=true,c_cal_ready=true;
static uint32_t owner=1;
static uint32_t *c_phys(unsigned off){(void)off;return &owner;}
'''
        code += function(compact, 'bool hhkb_compact_busy(')
        code += function(settings, 'bool vial_keyboard_eeprom_busy(')
        code += function(source, 'TickType_t vial_eeprom_poll_interval(')
        code += r'''
int main(void){
 assert(vial_eeprom_poll_interval()==1000);
 s_settings_dirty=true;assert(vial_eeprom_poll_interval()==2);s_settings_dirty=false;
 s_eeprom_dirty=true;assert(vial_eeprom_poll_interval()==2);s_eeprom_dirty=false;
 s_reset_pending=true;assert(vial_eeprom_poll_interval()==2);s_reset_pending=false;
 c_pending=true;assert(vial_eeprom_poll_interval()==2);c_pending=false;
 c_packing=true;assert(vial_eeprom_poll_interval()==2);c_packing=false;
 c_target=1;assert(vial_eeprom_poll_interval()==2);c_target=-1;
 c_active=0;owner=0;assert(vial_eeprom_poll_interval()==2);
 owner=C_RESET;assert(vial_eeprom_poll_interval()==2);
 owner=1;assert(vial_eeprom_poll_interval()==1000);
 c_pending=true;c_abandoned=true;assert(vial_eeprom_poll_interval()==1000);c_abandoned=false;
 c_pending=true;c_blocked=true;assert(vial_eeprom_poll_interval()==1000);
}
'''
        run_c(code)
