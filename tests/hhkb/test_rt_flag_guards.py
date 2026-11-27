import subprocess
import unittest
from .hhkb_helpers import ROOT


class RTFlagsTest(unittest.TestCase):
    def test_invalid_combinations(self):
        text = (ROOT / "keyboards/hhkb/config.h").read_text()
        text = text[text.index("#ifndef HHKB_RT_KEYMASK"):
                    text.index("#ifndef HHKB_SCAN_DIAGNOSTICS")]
        cases = [
            ["HHKB_RT_OVERSAMPLE=2"], ["HHKB_RT_DEADBAND=1"],
            ["HHKB_RT_KEYMASK=2"], ["HHKB_RT_KEYMASK=1", "HHKB_RT_OVERSAMPLE=1"],
            ["HHKB_RT_KEYMASK=1", "HHKB_RT_DEADBAND=3"],
            ["HHKB_RT_KEYMASK=1", "HHKB_RT_DEADBAND=-1"],
        ]
        for defines in cases:
            result = subprocess.run(["clang", "-E", "-x", "c", "-"] +
                                    ["-D" + d for d in defines],
                                    input=text, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0, defines)
            self.assertIn("error:", result.stderr)
        result = subprocess.run(["clang", "-E", "-x", "c", "-"],
                                input=text, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(["clang", "-E", "-x", "c", "-",
                                 "-DHHKB_RT_KEYMASK=1"],
                                input=text, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
