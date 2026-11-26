import re
import unittest
from .hhkb_helpers import ROOT


class RTKeyLayoutTest(unittest.TestCase):
    def test_default_positions(self):
        source = (ROOT / "keyboards/hhkb/config.h").read_text()
        layout = source.split("#define LAYOUT {", 1)[1].split("#define LAYOUT_DEFAULT", 1)[0]
        positions = [tuple(map(int, x)) for x in re.findall(r"\{(\d+),\s*(\d+)\}", layout)]
        expected = {"K_W": (2, 1), "K_A": (3, 3), "K_S": (3, 1),
                    "K_D": (3, 2), "K_SPC": (0, 6), "K_LSFT": (0, 0),
                    "K_LCTL": (3, 0)}
        for layer in ("BASE", "BASE_2"):
            text = source.split(f"[{layer}] = {{", 1)[1].split("}", 1)[0]
            keys = [x.strip() for x in text.split(",")]
            self.assertEqual(len(keys), len(positions))
            mapping = dict(zip(keys, positions))
            self.assertEqual({k: mapping[k] for k in expected}, expected)
