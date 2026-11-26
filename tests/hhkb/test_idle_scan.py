"""Idle slow-scan: logic test at several periods, config guard and wiring."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from .hhkb_helpers import ROOT

EC = ROOT / 'keyboards/hhkb/modules/ec'
CFG = ROOT / 'keyboards/hhkb'
PERIODS = (20, 50, 100, 250, 500, 1000)


class IdleScanTest(unittest.TestCase):
    def build(self, tmp, period):
        exe = Path(tmp) / f'idle_{period}'
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                        f'-DTEST_PERIOD_MS={period}', '-I', str(EC),
                        str(ROOT / 'tests/hhkb_classic/test_idle_scan.c'), '-o', str(exe)],
                       check=True)
        return exe

    def test_logic_all_documented_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            for period in PERIODS:
                with self.subTest(period=period):
                    subprocess.run([self.build(tmp, period)], check=True)

    def config_check(self, *defs):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'pin_defs.h').write_text('')
            return subprocess.run(['clang', '-fsyntax-only', '-x', 'c', '-I', tmp,
                                   *defs, str(CFG / 'config.h')],
                                  capture_output=True, text=True)

    def test_config_defaults_and_period_values(self):
        for period in PERIODS:
            with self.subTest(period=period):
                r = self.config_check(f'-DHHKB_IDLE_SLOW_SCAN_PERIOD_MS={period}', '-DHHKB_IDLE_SLOW_SCAN=1')
                self.assertEqual(r.returncode, 0, r.stderr)
        for bad in (0, 5, 15, 3000):
            with self.subTest(bad=bad):
                r = self.config_check(f'-DHHKB_IDLE_SLOW_SCAN_PERIOD_MS={bad}')
                self.assertNotEqual(r.returncode, 0)
        text = (CFG / 'config.h').read_text()
        self.assertIn('#define HHKB_IDLE_SLOW_SCAN 0', text)
        self.assertIn('#define HHKB_IDLE_SLOW_SCAN_PERIOD_MS 50', text)
        self.assertIn('#define HHKB_IDLE_TIMEOUT_S 180', text)

    def test_matrix_wiring_is_gated_and_after_publish(self):
        src = (EC / 'matrix.c').read_text()
        self.assertIn('#if HHKB_IDLE_SLOW_SCAN\n#include "idle_scan.h"', src)
        scan = src.index('hhkb_matrix_scan_raw(s_matrix_state)')
        publish = src.index('published_state[row] = state;')
        idle = src.index('idle_scan_update(')
        self.assertLess(scan, publish)
        self.assertLess(publish, idle)  # press is queued before the rate changes
        self.assertIn('hhkb_is_calibrating());\n            if (s_idle.slow != was_slow)', src)
        self.assertIn('if (s_idle.slow && !s_scan_calibrating)', src)
        self.assertEqual(src.count('hhkb_matrix_scan_raw('), 1)  # one detector, reused


if __name__ == '__main__':
    unittest.main()
