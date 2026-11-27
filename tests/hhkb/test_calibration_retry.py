"""Per-key calibration retry: one bad window must not condemn a key (aroum/dmk#18)."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from .hhkb_helpers import ROOT, function

DEFAULT_BASE = 800

PREAMBLE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "rapid_trigger.h"
#define DEFAULT_BASE 800
#define MATRIX_COLS 15
#define MATRIX_ROWS 4
#define CAL_BASELINE_SAMPLES 16U
#define CAL_SETTLE_SCANS 16
#define CAL_MAX_CAPTURE_SCANS 128
#define CAL_DRIFT_ABS 8
#define CAL_DRIFT_MEAN_DIV 64
#define CAL_SPREAD_MAX 64
#define CAL_UNSTABLE_LIMIT 3

/* Sentinel written to the per-key state slot when a key is resolved (accepted
 * with captured baseline, or frozen as rejected); matches the firmware. */
#define CAL_STATE_DONE 0xFFFFu
#define TOPRE_TYPICAL_TRAVEL_COUNTS 2370U
#define HHKB_CAL_BASE_MIN 20u
#define DEBUG_FLAG_CAL 8
#define MATRIX_MASK_WORDS ((MATRIX_COLS * MATRIX_ROWS + 31) / 32)
#define KIDX(c,r) ((c)*MATRIX_ROWS+(r))
#define DOWN(c,r) (s_cal_down_mask[KIDX(c,r)/32]&(1u<<(KIDX(c,r)%32)))
#define CALD(c,r) (s_calibrated_mask[KIDX(c,r)/32]&(1u<<(KIDX(c,r)%32)))
static bool s_calibration_mode, s_capture_baseline, s_custom_calibration, s_cal_unstable;
static uint8_t s_cal_baseline_samples, s_cal_settle_scans, s_cal_windows;
static uint32_t s_calibrated_mask[MATRIX_MASK_WORDS], s_cal_down_mask[MATRIX_MASK_WORDS];
static uint16_t s_cal_baseline[MATRIX_COLS][MATRIX_ROWS], s_cal_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_cal_press_start_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_capture_base[MATRIX_COLS][MATRIX_ROWS], s_capture_peak[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_capture_first8[MATRIX_COLS][MATRIX_ROWS];
static uint16_t s_capture_min[MATRIX_COLS][MATRIX_ROWS], s_capture_max[MATRIX_COLS][MATRIX_ROWS];
static uint8_t s_cal_stable_count[MATRIX_COLS][MATRIX_ROWS];
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
 (void)s_cal_stable_count;(void)s_cal_down_mask;
}
'''


class CalibrationRetryTest(unittest.TestCase):
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
            c = Path(tmp) / 'retry.c'
            c.write_text(code)
            exe = Path(tmp) / 'retry'
            subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-I', str(ROOT / 'keyboards/hhkb/modules/ec'), str(c), '-o', str(exe)],
                           check=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_one_bad_window_retries_only_that_key(self):
        code = self.build(r'''
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=DEFAULT_BASE;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 // Scans 0..15 settle (discarded), window 1 = 16..31, retry window = 32..47.
 // Stable keys read 500 in window 1 and 450 from window 2 on (the settled
 // level shifted between windows). Key (0,0) takes one noise spike in
 // window 1 only and is then flat like the rest.
 unsigned i;
 for(i=0;i<160 && hhkb_cal_is_capturing_baseline();i++){
  for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
   uint16_t v=(i<32)?500:450;
   if(c==0 && r==0 && i==24) v=700;
   hhkb_cal_accumulate_baseline(c,r,v);
  }
  hhkb_cal_decrement_samples();
 }
 setvbuf(stdout,NULL,_IONBF,0);
 assert(!hhkb_cal_is_capturing_baseline());
 assert(i==16+2*CAL_BASELINE_SAMPLES);   // settle + 2 windows, not the full budget
 assert(s_capture_base[0][0]==450);      // flagged key re-measured in its retry
 assert(s_capture_base[1][0]==500);      // neighbours keep their window-1 data
 assert(s_capture_base[14][3]==500);
 assert(!s_cal_unstable);                // no key lost its baseline
 printf("captured: noisy key=%u, neighbours=%u\n", s_capture_base[0][0], s_capture_base[1][0]);
 // Every key can still be pressed and saved.
 hhkb_cal_record_peak(0,0,2500); hhkb_cal_record_peak(0,0,450);
 hhkb_cal_record_peak(1,0,2500); hhkb_cal_record_peak(1,0,500);
 hhkb_calibration_finish();
 assert(s_cal_baseline[0][0]==450);
 assert(s_cal_baseline[1][0]==500);
 return 0;
}
''')
        self.run_program(code)

    def test_persistent_instability_rejects_key(self):
        code = self.build(r'''
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=DEFAULT_BASE;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 // Key (0,0) alternates 300/500 every scan in every window (spread fails the
 // gate forever); every other key is flat 500.
 unsigned i;
 for(i=0;i<160 && hhkb_cal_is_capturing_baseline();i++){
  for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++)
   hhkb_cal_accumulate_baseline(c,r,(c==0&&r==0)?((i&1)?500:300):500);
  hhkb_cal_decrement_samples();
 }
 setvbuf(stdout,NULL,_IONBF,0);
 assert(!hhkb_cal_is_capturing_baseline());
 assert(i==16+CAL_UNSTABLE_LIMIT*CAL_BASELINE_SAMPLES); // bounded retries
 assert(s_capture_base[0][0]==0 && s_capture_peak[0][0]==0); // rejected
 assert(s_cal_unstable);
 assert(s_capture_base[1][0]==500);      // the other keys are captured
 printf("rejected key kept 0, neighbour %u\n", s_capture_base[1][0]);
 // A press must not resurrect the rejected key.
 hhkb_cal_record_peak(0,0,2500); hhkb_cal_record_peak(0,0,300);
 assert(!CALD(0,0));
 hhkb_cal_record_peak(1,0,2500); hhkb_cal_record_peak(1,0,500);
 assert(CALD(1,0));
 hhkb_calibration_finish();
 assert(s_cal_baseline[0][0]==DEFAULT_BASE); // saved range kept
 assert(s_cal_baseline[1][0]==500);
 return 0;
}
''')
        self.run_program(code)

    def test_drift_only_is_not_a_press(self):
        code = self.build(r'''
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=DEFAULT_BASE;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 unsigned i;
 for(i=0;i<160 && hhkb_cal_is_capturing_baseline();i++){
  for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++)
   hhkb_cal_accumulate_baseline(c,r,400);
  hhkb_cal_decrement_samples();
 }
 assert(!hhkb_cal_is_capturing_baseline());
 setvbuf(stdout,NULL,_IONBF,0);
 // Idle drift of +160 counts: above the old base+150 press gate, far below a
 // quarter of the typical Topre travel.
 for(unsigned k=0;k<8;k++) hhkb_cal_record_peak(0,0,560);
 assert(!DOWN(0,0) && !CALD(0,0));       // drift is not actuation
 printf("drift-only key not actuated\n");
 // A real bottom-out press through travel still counts.
 hhkb_cal_record_peak(1,0,400+TOPRE_TYPICAL_TRAVEL_COUNTS);
 assert(CALD(1,0) && DOWN(1,0));
 hhkb_cal_record_peak(1,0,400);
 hhkb_calibration_finish();
 assert(s_cal_baseline[0][0]==DEFAULT_BASE); // drift-only key not saved
 assert(s_cal_baseline[1][0]==400);
 return 0;
}
''')
        self.run_program(code)

    def test_finish_refuses_never_actuated_key(self):
        code = self.build(r'''
int main(void){
 for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++){
  s_cal_baseline[c][r]=DEFAULT_BASE;s_cal_peak[c][r]=3170;
 }
 hhkb_calibration_start();
 unsigned i;
 for(i=0;i<160 && hhkb_cal_is_capturing_baseline();i++){
  for(unsigned c=0;c<MATRIX_COLS;c++)for(unsigned r=0;r<MATRIX_ROWS;r++)
   hhkb_cal_accumulate_baseline(c,r,400);
  hhkb_cal_decrement_samples();
 }
 assert(!hhkb_cal_is_capturing_baseline());
 // Key (0,0) is never pressed at all; key (1,0) gets a full press.
 hhkb_cal_record_peak(1,0,400+TOPRE_TYPICAL_TRAVEL_COUNTS);
 hhkb_cal_record_peak(1,0,400);
 assert(!CALD(0,0) && CALD(1,0));
 hhkb_calibration_finish();
 assert(s_cal_baseline[0][0]==DEFAULT_BASE); // never actuated: not saved
 assert(s_cal_baseline[1][0]==400);
 setvbuf(stdout,NULL,_IONBF,0);
 printf("unactuated key refused\n");
 return 0;
}
''')
        self.run_program(code)
