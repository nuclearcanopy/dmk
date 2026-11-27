"""Rapid Trigger mode selector and VIA definition consistency."""
import json
import re
import unittest
from pathlib import Path

from .hhkb_helpers import ROOT


class ViaRTPositionsTest(unittest.TestCase):
    def test_mode_selector_and_layout(self):
        config = (ROOT / "keyboards/hhkb/config.h").read_text()
        layout = config.split("#define LAYOUT {", 1)[1].split("#define LAYOUT_DEFAULT", 1)[0]
        positions = [tuple(map(int, p)) for p in re.findall(r"\{(\d+),\s*(\d+)\}", layout)]
        self.assertEqual(len(positions), 60)
        self.assertEqual(set(positions), {(r, c) for r in range(4) for c in range(15)})

        definition = json.loads((ROOT / "keyboards/hhkb/via.json").read_text())
        rapid = next(x for x in definition["menus"][0]["content"] if x["label"] == "Rapid Trigger")
        selector = next(x for x in rapid["content"] if x["content"][0] == "id_hhkb_rapid_trigger")
        self.assertEqual(selector["type"], "dropdown")
        self.assertEqual(selector["content"], ["id_hhkb_rapid_trigger", 0, 3])
        self.assertEqual([opt[1] for opt in selector["options"]], [0, 1, 2])

        # The per-key toggles (VIA IDs 68-127) are gone.
        controls = [x for x in rapid["content"] if x.get("type") == "toggle"
                    and x["content"][0].startswith("id_hhkb_rt_key_")]
        self.assertEqual(controls, [])

        mask_header = (ROOT / "keyboards/hhkb/modules/ec/rt_keymask.h").read_text()
        defaults = mask_header.split("#define HHKB_RT_KEYS(X)", 1)[1].split("_Static_assert", 1)[0]
        default_positions = {(int(row), int(col)) for col, row in
                             re.findall(r"X\((\d+),\s*(\d+),\s*\d+\)", defaults)}
        self.assertEqual(len(default_positions), 7)

        # The seven-key default matches the physical W, A, S, D, Space, LShift, LCtrl.
        layer0 = config.split("[BASE] = {", 1)[1].split("}", 1)[0]
        keys = [x.strip() for x in layer0.split(",")]
        self.assertEqual(len(keys), 60)
        key_to_pos = dict(zip(keys, positions))
        expected = {key_to_pos[k] for k in ("K_W", "K_A", "K_S", "K_D", "K_SPC", "K_LSFT", "K_LCTL")}
        self.assertEqual(default_positions, expected)

        via_positions = [tuple(map(int, key.split("\n")[0].split(",")))
                         for row in definition["layouts"]["keymap"] for key in row
                         if isinstance(key, str)]
        self.assertEqual(positions, via_positions)

        def commands(value):
            if isinstance(value, dict):
                content = value.get("content")
                if isinstance(content, list) and len(content) >= 3 and isinstance(content[1], int):
                    yield tuple(content[1:3])
                for item in value.values():
                    yield from commands(item)
            elif isinstance(value, list):
                for item in value:
                    yield from commands(item)
        all_commands = list(commands(definition["menus"]))
        for i in range(68, 128):
            self.assertEqual(all_commands.count((0, i)), 0)
        self.assertEqual(all_commands.count((0, 3)), 1)
