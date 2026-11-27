"""A baseline sampled while the sensor still drifts must not be committed (aroum/dmk#18)."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from .hhkb_helpers import ROOT, function

SETTLED = 553

PREAMBLE = r'''
#include <assert.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "rapid_trigger.h"
#define MATRIX_COLS 15
#define MATRIX_ROWS 4
#define CAL_BASELINE_SAMPLES 16U
#define CAL_SETTLE_SCANS 16
#define CAL_MAX_CAPTURE_SCANS 128
#define CAL_DRIFT_ABS 8
#define CAL_DRIFT_MEAN_DIV 64
#define CAL_SPREAD_MAX 64
#define CAL_UNSTABLE_LIMIT 3
#define CAL_STATE_DONE 0xFFFFu
#define TOPRE_TYPICAL_TRAVEL_COUNTS 2370U
#define HHKB_CAL_BASE_MIN 20u
#define DEBUG_FLAG_CAL 8
#define MATRIX_MASK_WORDS ((MATRIX_COLS * MATRIX_ROWS + 31) / 32)
static bool s_calibration_mode, s_capture_baseline, s_custom_calibration, s_cal_unstable;
static uint8_t s_cal_baseline_samples, s_cal_settle_scans, s_cal_windows;
static uint32_t s_calibrated_mask[MATRIX_MASK_WORDS], s_cal_down_mask[MATRIX_MASK_WORDS];
static uint16_t s_cal_baseline[MATRIX_COLS][MATRIX_ROWS], s_cal_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_cal_press_start_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_capture_base[MATRIX_COLS][MATRIX_ROWS], s_capture_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_capture_first8[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_capture_min[MATRIX_COLS][MATRIX_ROWS], s_capture_max[MATRIX_COLS][MATRIX_ROWS];
static rt_key_t s_rt_keys[MATRIX_COLS][MATRIX_ROWS];
static bool hhkb_get_debug_flag(unsigned f){(void)f;return false;}
static void cal_log_push(uint8_t k,uint8_t r,uint8_t c,uint8_t n,uint16_t a,uint16_t b){(void)k;(void)r;(void)c;(void)n;(void)a;(void)b;}
static void hhkb_settings_mark_dirty(void){}
static uint8_t calibrated_key_count(void){return 0;}
static int16_t keyboard_get_flat_key_index(uint8_t row,uint8_t col){(void)row;(void)col;return 0;}
void rt_key_set_range(rt_key_t *k,uint16_t b,uint16_t p){k->base=b;(void)p;}
void rt_key_reset(rt_key_t *k){k->down=false;}
#define CAL_LOG_START 1
#define CAL_LOG_BASELINE 2
#define CAL_LOG_KEY 3
#define CAL_LOG_FINISH 4
#define CAL_LOG_PEAK 5
'''

TOUCH = r'''
static void touch_capture_state(void){
 // Referenced so the harness also compiles against the pre-fix logic.
 (void)s_cal_unstable;(void)s_cal_settle_scans;(void)s_cal_windows;
 (void)s_capture_first8;(void)s_capture_min;(void)s_capture_max;
}
'''


class CalibrationSagTest(unittest.TestCase):
    def build(self, main_body):
        source = (ROOT / 'keyboards/hhkb/modules/ec/ec_settings.c').read_text()
        code = (PREAMBLE
                + function(source, 'void hhkb_calibration_start(')
                + function(source, 'void hhkb_calibration_finish(')
                + function(source, 'void hhkb_cal_accumulate_baseline(')
                + function(source, 'void hhkb_cal_record_peak(')
                + function(source, 'bool hhkb_cal_is_capturing_baseline(')
                + function(source, 'void hhkb_cal_decrement_samples(')
                + TOUCH + main_body)
        return code

    def run_program(self, code):
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'sag.c'
            c.write_text(code)
            exe = Path(tmp) / 'sag'
            subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-I', str(ROOT / 'keyboards/hhkb/modules/ec'), str(c), '-lm', '-o', str(exe)],
                           check=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_drifting_baseline_is_not_committed(self):
        code = self.build(r'''
#define DEFAULT_BASE 800
#define SETTLED 553
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=DEFAULT_BASE;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 touch_capture_state();
 // Key (0,0): the sensor is still rising from 276 to the settled 553
 // (tau = 6 scans) while the window is sampled. Key (1,0): flat control.
 unsigned i;
 for(i=0;i<160 && hhkb_cal_is_capturing_baseline();i++){
  hhkb_cal_accumulate_baseline(0,0,(uint16_t)(SETTLED-277.0*exp(-(double)i/6.0)));
  hhkb_cal_accumulate_baseline(1,0,SETTLED);
  hhkb_cal_decrement_samples();
 }
 assert(!hhkb_cal_is_capturing_baseline());
 assert(s_cal_settle_scans==0);
 setvbuf(stdout,NULL,_IONBF,0);
 printf("sampled baseline: drifting key=%u (settled %u), flat key=%u\n",
        s_capture_base[0][0],SETTLED,s_capture_base[1][0]);
 // Press both keys through travel and release, as the user would.
 for(unsigned k=0;k<2;k++){
  hhkb_cal_record_peak(k,0,2500);
  hhkb_cal_record_peak(k,0,SETTLED);
 }
 hhkb_calibration_finish();
 printf("committed baseline: drifting key=%u, flat key=%u\n",
        s_cal_baseline[0][0],s_cal_baseline[1][0]);
 assert(s_cal_baseline[1][0]==SETTLED);   // control must still be accepted
 // Wanted: the drifting capture is rejected (old value kept) or within 5%% of settled.
 assert(s_cal_baseline[0][0]==DEFAULT_BASE || s_cal_baseline[0][0]>=SETTLED*95/100);
 return 0;
}
''')
        self.run_program(code)

    def test_persistent_instability_rejects_key(self):
        code = self.build(r'''
#define DEFAULT_BASE 800
#define SETTLED 553
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=DEFAULT_BASE;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 touch_capture_state();
 // Key (0,0) never stops drifting (+2 counts/scan); key (1,0) is flat.
 unsigned i;
 for(i=0;i<200 && hhkb_cal_is_capturing_baseline();i++){
  hhkb_cal_accumulate_baseline(0,0,(uint16_t)(400+2*i));
  hhkb_cal_accumulate_baseline(1,0,SETTLED);
  hhkb_cal_decrement_samples();
 }
 assert(!hhkb_cal_is_capturing_baseline());
 assert(s_cal_unstable);              // flagged "Cal: unstable"
 assert(s_capture_base[0][0]==0);     // no usable baseline for the drifting key
 hhkb_cal_record_peak(1,0,2500);
 hhkb_cal_record_peak(1,0,SETTLED);
 hhkb_cal_record_peak(0,0,2500);      // must not resurrect the rejected key
 hhkb_calibration_finish();
 printf("committed baseline: drifting key=%u, flat key=%u\n",
        s_cal_baseline[0][0],s_cal_baseline[1][0]);
 assert(s_cal_baseline[0][0]==DEFAULT_BASE);
 assert(s_cal_baseline[1][0]==SETTLED);
 return 0;
}
''')
        self.run_program(code)

    def test_short_press_does_not_commit(self):
        code = self.build(r'''
#define DEFAULT_BASE 800
#define SETTLED 553
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=DEFAULT_BASE;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 touch_capture_state();
 for(unsigned i=0;i<64 && hhkb_cal_is_capturing_baseline();i++){
  hhkb_cal_accumulate_baseline(0,0,SETTLED);
  hhkb_cal_accumulate_baseline(1,0,SETTLED);
  hhkb_cal_decrement_samples();
 }
 assert(!hhkb_cal_is_capturing_baseline());
 // Key (0,0) is pressed only to base+600: it trips the press latch
 // (base + a quarter of the typical travel) but stays well short of half
 // the typical Topre travel.
 hhkb_cal_record_peak(0,0,1153);
 hhkb_cal_record_peak(0,0,SETTLED);
 hhkb_cal_record_peak(1,0,2500);
 hhkb_cal_record_peak(1,0,SETTLED);
 hhkb_calibration_finish();
 printf("committed baseline: short-press key=%u, full-press key=%u\n",
        s_cal_baseline[0][0],s_cal_baseline[1][0]);
 assert(s_cal_baseline[0][0]==DEFAULT_BASE); // not committed without real travel
 assert(s_cal_baseline[1][0]==SETTLED);
 return 0;
}
''')
        self.run_program(code)

    def test_loader_self_heals_saved_sag(self):
        source = (ROOT / 'keyboards/hhkb/modules/ec/ec_settings.c').read_text()
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define TOPRE_TYPICAL_TRAVEL_COUNTS 2370U
''' + function(source, 'static bool cal_range_sagged(') + r'''
int main(void){
 setvbuf(stdout,NULL,_IONBF,0);
 // The saved 276/553 sag from aroum/dmk#18 must fall back to defaults.
 assert(cal_range_sagged(276,553,800));
 // A real press from a low base keeps its calibration.
 assert(!cal_range_sagged(276,3170,800));
 assert(!cal_range_sagged(553,3170,800));
 // Boundaries: default/2 is the floor, half travel the range gate.
 assert(cal_range_sagged(399,399+2370/2-1,800));
 assert(!cal_range_sagged(400,1584,800));
 assert(!cal_range_sagged(399,399+2370/2,800));
 printf("loader self-heal checks passed\n");
 return 0;
}
'''
        self.run_program(code)
