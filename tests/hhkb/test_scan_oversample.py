"""Exercise the production oversampling block with mocked conversions."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from .hhkb_helpers import ROOT


class OversampleTest(unittest.TestCase):
    def test_sampling_guards_and_rounding(self):
        source = (ROOT / "keyboards/hhkb/modules/ec/classic_matrix.c").read_text()
        start = source.index("#if HHKB_RT_OVERSAMPLE == 2")
        end = source.index("#endif", start) + len("#endif")
        block = source[start:end].replace("&snapshot.mask", "&rt_mask")
        harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#define HHKB_RT_OVERSAMPLE 2
#define HHKB_RT_KEYMASK 1
#define MATRIX_ROWS 4
#define MATRIX_COLS 15
#include "rt_keymask.h"
static rt_key_t s_rt_keys[15][4];
static hhkb_rt_mask_t rt_mask;
static int starts;
static uint16_t second;
static void adc_start_sample(void) { ++starts; }
static uint16_t adc_finish_sample(void) { return second; }
static unsigned run(bool on, bool cal, bool autoff, int rate, int first_timeout,
                    int second_timeout) {
  starts = 0;
  rt_cfg_t scan_cfg = {.rt_enabled=on};
  bool is_calibrating=cal, adc_autoff=autoff;
  unsigned lock_rate=rate;
  for (uint8_t col=0; col<15; ++col) for (uint8_t row=0; row<4; ++row) {
    ++starts;
    uint16_t val = first_timeout && col==1 && row==2 ? UINT16_MAX : 1000;
    second = second_timeout ? UINT16_MAX : 1003;
    BLOCK
    if (on && !cal && !autoff && rate==4 && hhkb_rt_mask_member(&rt_mask, col, row) &&
        s_rt_keys[col][row].latched && val != UINT16_MAX) {
      assert(val == (second_timeout ? 1000 : 1002));
    }
  }
  return starts;
}
int main(void) {
  hhkb_rt_mask_default(&rt_mask);
  assert(run(true,false,false,4,0,0)==60);
  for (int c=0;c<15;++c) for(int r=0;r<4;++r) s_rt_keys[c][r].latched=true;
  assert(run(true,false,false,4,0,0)==67);
  assert(run(true,false,false,4,1,0)==66);
  assert(run(true,false,false,4,0,1)==67);
  assert(run(false,false,false,4,0,0)==60);
  assert(run(true,true,false,4,0,0)==60);
  assert(run(true,false,true,4,0,0)==60);
  assert(run(true,false,false,3,0,0)==60);
}
'''.replace("    BLOCK", block)
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / "test.c"
            c.write_text(harness)
            exe = Path(tmp) / "test"
            subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "keyboards/hhkb/modules/ec"),
                            str(c), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
