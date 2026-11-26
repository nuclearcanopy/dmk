# Host regression tests

From the repository root, with `clang` and `uv` installed:

```bash
bash tests/run_all_tests.sh
```

For a short core-only run, including both immediate and batched USB reports:

```bash
bash tests/run_runtime_tests.sh
DMK_TEST_SANITIZERS=1 bash tests/run_runtime_tests.sh
```

The runtime runner uses a temporary directory and removes its binaries on exit.
`CC` selects the compiler (clang by default). `DMK_TEST_SANITIZERS=1` enables
AddressSanitizer and UndefinedBehaviorSanitizer.

`run_all_tests.sh` compiles and runs the C tests (core, hold-tap, one-shot,
memory, Vial keycodes, and the HHKB tests for Rapid Trigger, scan processing,
travel curve, calibration requests, compact EEPROM storage, the SOF lock,
indicators and Grave Escape) and then the Python tests under `tests/`
(`python3 -m unittest discover`), which cover the HHKB flasher and HTML
patcher, VIA controls, reset scenarios and a check that the Hybrid sources
contain no radio code (`tests/hhkb_classic/test_no_bluetooth.py`).
The directory name `hhkb_classic` is historical; it holds the HHKB tests.

The **Core and HHKB Tests** workflow (`.github/workflows/core_hhkb_tests.yml`)
runs the full suite on Linux and the sanitizer run on Linux and macOS.

These are host tests with simulated peripherals. They do not establish ADC
settling, USB latency or current consumption. Physical validation is tracked
separately in the [hardware checklist](../docs/en/tests.md).
