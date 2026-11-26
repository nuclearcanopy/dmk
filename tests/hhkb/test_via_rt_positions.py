"""Physical RT selection and VIA definition consistency."""
import ast
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from .hhkb_helpers import ROOT


class ViaRTPositionsTest(unittest.TestCase):
    def test_layout_and_json(self):
        config = (ROOT / "keyboards/hhkb/config.h").read_text()
        layout = config.split("#define LAYOUT {", 1)[1].split("#define LAYOUT_DEFAULT", 1)[0]
        positions = [tuple(map(int, p)) for p in re.findall(r"\{(\d+),\s*(\d+)\}", layout)]
        self.assertEqual(len(positions), 60)
        self.assertEqual(set(positions), {(r, c) for r in range(4) for c in range(15)})
        definition = json.loads((ROOT / "keyboards/hhkb/via.json").read_text())
        rapid = next(x for x in definition["menus"][0]["content"] if x["label"] == "Rapid Trigger")
        controls = [x for x in rapid["content"] if x.get("type") == "toggle"
                    and x["content"][0].startswith("id_hhkb_rt_key_")]
        # Multiword labels are kept explicit to avoid deriving names from keycodes.
        labels = ["Escape", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                  "Minus", "Equals", "Backslash", "Grave", "Tab", "Q", "W", "E",
                  "R", "T", "Y", "U", "I", "O", "P", "Left bracket", "Right bracket",
                  "Delete", "Left Ctrl", "A", "S", "D", "F", "G", "H", "J", "K",
                  "L", "Semicolon", "Quote", "Return", "Left Shift", "Z", "X", "C",
                  "V", "B", "N", "M", "Comma", "Period", "Slash", "Right Shift",
                  "Fn", "Left Option", "Left Command", "Space", "Right Command", "Right Option"]
        self.assertEqual([x["label"] for x in controls], labels)
        self.assertEqual([x["content"] for x in controls],
                         [[f"id_hhkb_rt_key_{i:02}", 0, 68 + i] for i in range(60)])
        mask_header = (ROOT / "keyboards/hhkb/modules/ec/rt_keymask.h").read_text()
        defaults = mask_header.split("#define HHKB_RT_KEYS(X)", 1)[1].split("_Static_assert", 1)[0]
        default_positions = {(int(row), int(col)) for col, row in
                             re.findall(r"X\((\d+),\s*(\d+),\s*\d+\)", defaults)}
        self.assertEqual({labels[i] for i, pos in enumerate(positions) if pos in default_positions},
                         {"W", "A", "S", "D", "Space", "Left Shift", "Left Ctrl"})
        self.assertEqual(len(default_positions), 7)
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
            self.assertEqual(all_commands.count((0, i)), 1)

    def test_dispatch(self):
        # Reuse the existing control test's comprehensive unrelated API mocks.
        source = (ROOT / "tests/hhkb/test_dmk_fmt_and_via_controls.py").read_text()
        tree = ast.parse(source)
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.name == "test_via_controls_dispatch_round_trip")
        assignment = next(n for n in method.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "code" for t in n.targets))
        prefix = ast.literal_eval(assignment.value.left.left)
        controls = (ROOT / "keyboards/hhkb/modules/via_settings/hhkb_via_controls.c").read_text()
        body = controls[controls.index("static void copy_str28("):]
        config = (ROOT / "keyboards/hhkb/config.h").read_text()
        layout = "#define LAYOUT {" + config.split("#define LAYOUT {", 1)[1].split("#define LAYOUT_DEFAULT", 1)[0]
        code = prefix + "\n#define HHKB_RT_ARBITRARY_SELECTION 1\n#define HHKB_RT_MASK_BITS 60\n#define MATRIX_ROWS 4\n" + layout + r'''
typedef enum { HHKB_RT_MASK_INVALID, HHKB_RT_MASK_UNCHANGED, HHKB_RT_MASK_CHANGED } hhkb_rt_mask_result_t;
static bool mask[60];
bool hhkb_rt_key_get(unsigned i, bool *v) { if (i >= 60) return false; *v = mask[i]; return true; }
hhkb_rt_mask_result_t hhkb_rt_key_set(unsigned i, unsigned v) {
    if (i >= 60 || v > 1) return HHKB_RT_MASK_INVALID;
    hhkb_rt_mask_result_t result = mask[i] == v ? HHKB_RT_MASK_UNCHANGED : HHKB_RT_MASK_CHANGED;
    mask[i] = v; return result;
}
''' + body + r'''
int main(void) {
    uint8_t req[32] = {0}, resp[32] = {0};
    for (unsigned ordinal = 0; ordinal < 60; ++ordinal) {
        unsigned index = via_rt_positions[ordinal][1] * 4 + via_rt_positions[ordinal][0];
        req[1] = 0; req[2] = 68 + ordinal; req[0] = 7; req[3] = 1;
        assert(via_custom_value_command_kb(req, resp) && mask[index]);
        req[0] = 8; assert(via_custom_value_command_kb(req, resp) && resp[3] == 1);
        req[0] = 7; req[3] = 2; assert(!via_custom_value_command_kb(req, resp) && mask[index]);
        req[3] = 0; assert(via_custom_value_command_kb(req, resp) && !mask[index]);
    }
    req[0] = 7; req[2] = 3; req[3] = 1;
    assert(via_custom_value_command_kb(req, resp) && s_rt[3] == 1);
    req[2] = 68; assert(via_custom_value_command_kb(req, resp) && s_rt[3] == 1);
    req[2] = 128; assert(!via_custom_value_command_kb(req, resp));
    req[2] = 68; req[1] = 1; assert(!via_custom_value_command_kb(req, resp));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            src, exe = Path(tmp) / "test.c", Path(tmp) / "test"
            src.write_text(code)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-DHHKB_COMPACT_STORAGE=1", "-fsanitize=address,undefined",
                            str(src), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
