"""A baseline sampled while the sensor still drifts must not be committed (issue #18)."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from .hhkb_helpers import ROOT, function


class CalibrationSagTest(unittest.TestCase):
    def test_drifting_baseline_is_not_committed(self):
        source = (ROOT / 'keyboards/hhkb/modules/ec/ec_settings.c').read_text()
        code = r'''
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
#define HHKB_CAL_BASE_MIN 20u
#define DEBUG_FLAG_CAL 8
#define MATRIX_MASK_WORDS ((MATRIX_COLS * MATRIX_ROWS + 31) / 32)
static bool s_calibration_mode, s_capture_baseline, s_custom_calibration;
static uint8_t s_cal_baseline_samples;
static uint32_t s_calibrated_mask[MATRIX_MASK_WORDS], s_cal_down_mask[MATRIX_MASK_WORDS];
static uint16_t s_cal_baseline[MATRIX_COLS][MATRIX_ROWS], s_cal_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_cal_press_start_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_capture_base[MATRIX_COLS][MATRIX_ROWS], s_capture_peak[MATRIX_COLS][MATRIX_ROWS];
static rt_key_t s_rt_keys[MATRIX_COLS][MATRIX_ROWS];
static bool hhkb_get_debug_flag(unsigned f){(void)f;return false;}
static void cal_log_push(uint8_t k,uint8_t r,uint8_t c,uint8_t n,uint16_t a,uint16_t b){(void)k;(void)r;(void)c;(void)n;(void)a;(void)b;}
static void hhkb_settings_mark_dirty(void){}
static uint8_t calibrated_key_count(void){return 0;}
void rt_key_set_range(rt_key_t *k,uint16_t b,uint16_t p){k->base=b;(void)p;}
void rt_key_reset(rt_key_t *k){k->down=false;}
#define CAL_LOG_START 1
#define CAL_LOG_BASELINE 2
#define CAL_LOG_FINISH 4
#define CAL_LOG_KEY 3
#define CAL_LOG_PEAK 5
''' + function(source, 'void hhkb_calibration_start(') \
    + function(source, 'void hhkb_calibration_finish(') \
    + function(source, 'void hhkb_cal_accumulate_baseline(') \
    + function(source, 'void hhkb_cal_record_peak(') \
    + function(source, 'bool hhkb_cal_is_capturing_baseline(') \
    + function(source, 'void hhkb_cal_decrement_samples(') + r'''
#define SETTLED 553
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=800;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 // Key (0,0): sensor rises from 276 to the settled 553 (tau = 6 scans) during
 // the 16-scan window. Key (1,0): control, flat at the settled value.
 for(unsigned i=0;i<16 && hhkb_cal_is_capturing_baseline();i++){
  hhkb_cal_accumulate_baseline(0,0,(uint16_t)(SETTLED-277.0*exp(-(double)i/6.0)));
  hhkb_cal_accumulate_baseline(1,0,SETTLED);
  hhkb_cal_decrement_samples();
 }
 assert(!hhkb_cal_is_capturing_baseline());
 setvbuf(stdout,NULL,_IONBF,0);printf("sampled baseline: drifting key=%u (settled %u), flat key=%u\n",s_capture_base[0][0],SETTLED,s_capture_base[1][0]);
 // Press both keys to 2500 and release, as the user would.
 for(unsigned k=0;k<2;k++){
  hhkb_cal_record_peak(k,0,2500);
  hhkb_cal_record_peak(k,0,SETTLED);
 }
 hhkb_calibration_finish();
 printf("committed baseline: drifting key=%u, flat key=%u\n",s_cal_baseline[0][0],s_cal_baseline[1][0]);
 assert(s_cal_baseline[1][0]==SETTLED);   // control must still be accepted
 // Wanted: the drifting capture is rejected (old value kept) or within 5% of settled.
 assert(s_cal_baseline[0][0]==800 || s_cal_baseline[0][0]>=SETTLED*95/100);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'sag.c'; c.write_text(code)
            exe = Path(tmp) / 'sag'
            subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-I', str(ROOT / 'keyboards/hhkb/modules/ec'), str(c), '-lm', '-o', str(exe)],
                           check=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
