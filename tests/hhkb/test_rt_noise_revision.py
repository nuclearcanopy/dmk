import subprocess
import tempfile
import unittest
from pathlib import Path
from .hhkb_helpers import ROOT


class NoiseRevisionTest(unittest.TestCase):
    def test_revision_resets(self):
        source = (ROOT / "keyboards/hhkb/modules/ec/classic_matrix.c").read_text()
        start = source.index("    static uint32_t noise_curve_revision")
        end = source.index("#endif", start)
        block = source[start:end]
        program = r'''
#include <assert.h>
#include <stdint.h>
#include "rt_noise.h"
#define HHKB_RT_KEY_COUNT 7
static rt_noise_t s_rt_noise[7];
static uint32_t ec_curve_revision, rt_range_revision;
static void reset(void) {
BLOCK
}
int main(void) {
  for (int i=0;i<7;i++) s_rt_noise[i].n_q8=123;
  rt_range_revision=1; reset();
  for (int i=0;i<7;i++) assert(s_rt_noise[i].n_q8==0);
  s_rt_noise[0].n_q8=456; reset(); assert(s_rt_noise[0].n_q8==456);
  ec_curve_revision=1; reset(); assert(s_rt_noise[0].n_q8==0);
}
'''.replace("BLOCK", block)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.c"
            path.write_text(program)
            exe = Path(tmp) / "t"
            subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "keyboards/hhkb/modules/ec"),
                            str(path), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
