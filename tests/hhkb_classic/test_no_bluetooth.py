"""nxmk: the Hybrid image must not build or expose any Bluetooth/radio code."""
import json
import re
import unittest

from .hhkb_helpers import ROOT

BANNED = re.compile(r'bluetooth|\bBLE\b|nordic|nrf52|hhkb_bt_|pairing|hhkb_hybrid_(report|request_slot|'
                    r'consumer_report|output_bluetooth|battery_level|pairing)', re.I)
SOURCES = [
    'keyboards/hhkb/modules/hybrid/hybrid.c',
    'keyboards/hhkb/modules/hybrid/hybrid.h',
    'keyboards/hhkb/modules/hybrid/hybrid_stop.c',
    'keyboards/hhkb/modules/ec/matrix.c',
    'keyboards/hhkb/modules/ec/ec_settings.c',
    'keyboards/hhkb/modules/ec/ec_settings.h',
    'keyboards/hhkb/modules/ec/classic_matrix.c',
    'keyboards/hhkb/modules/via_settings/hhkb_via_controls.c',
    'keyboards/hhkb/modules/indicators_system/indicators_system.c',
]


class NoBluetoothTest(unittest.TestCase):
    def test_hybrid_sources_have_no_radio_references(self):
        for path in SOURCES:
            text = (ROOT / path).read_text()
            # Tolerate the comments that document the removal itself.
            code = '\n'.join(l for l in text.split('\n') if not l.lstrip().startswith('//'))
            self.assertIsNone(BANNED.search(code), path)

    def test_via_definition_has_no_bluetooth(self):
        text = (ROOT / 'keyboards/hhkb/via.json').read_text()
        self.assertNotRegex(text, r'(?i)bluetooth|id_hhkb_bt|\bBT\b')
        names = [k['name'] for k in json.loads(text)['customKeycodes']]
        self.assertEqual(names, ['System 1', 'System 2'])

    def test_usb_identity_unchanged(self):
        via = json.loads((ROOT / 'keyboards/hhkb/via.json').read_text())
        self.assertEqual((via['vendorId'].lower(), via['productId'].lower()), ('0xcafe', '0x4014'))
        self.assertIn('#define VIAL_PRODUCT_ID 0x4014', (ROOT / 'keyboards/hhkb/config.h').read_text())

    def test_hybrid_only_hhkb_target(self):
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        self.assertIn('NXMK_ALLOW_UPSTREAM_TARGETS', cmake)
        self.assertIn('nxmk only builds', cmake)


if __name__ == '__main__':
    unittest.main()
