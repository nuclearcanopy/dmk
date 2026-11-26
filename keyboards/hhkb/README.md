# nxmk: HHKB Hybrid Type-S (ANSI) firmware

Personal, wired-only firmware for the HHKB Hybrid Type-S (ANSI) on its original
STM32L072 controller. It is a derivative of [DMK](https://github.com/aroum/dmk)
and is licensed AGPL-3.0-or-later (see [NOTICE.md](../../NOTICE.md)).

- **Hardware:** HHKB Hybrid Type-S, ANSI, STM32L072 (Bank 2 at `0x08010000`).
  `CMakeLists.txt` rejects any other model selector.
- **Transport:** USB only. There is no radio code in the image: on battery
  power the keyboard has no output path and goes to a low-power STOP state until
  USB power returns (see [Config](docs/en/config.md#power-and-usb-detection)).
- **USB identity:** manufacturer `nxmk`, product `nxmk HHKB Hybrid-S`,
  VID:PID `cafe:4014`.

**Documentation:** [Install](docs/en/install.md) •
[Backup & restore](docs/en/backup-restore.md) • [Build](docs/en/build.md) •
[Config](docs/en/config.md) • [VIA & debug](docs/en/via-debug.md) •
[Hardware checklist](../../docs/en/tests.md)

## Features

- [VIA](https://www.usevia.app/) (protocol v3 over the raw HID interface) for
  keymaps and custom settings via [`via.json`](via.json); `vial.json` gives
  keymap editing only in Vial.
- Selectable matrix scan rate: 50, 125, 250, 500 or 1000 Hz; optional 4x ADC
  oversampling (bypassed at 1000 Hz).
- Per-key user calibration, optional 5-point travel curve.
- Actuation point and release hysteresis, or Rapid Trigger with press/release
  sensitivity and top/bottom dead zones.
- USB SOF lock (`HHKB_SOF_LOCK`, on by default) that aligns scans to the USB
  frame.
- Mod-Tap / Layer-Tap (hold-tap) with configurable timing, Grave Escape, two
  base/Fn layer pairs (System 1 / System 2), two configurable LEDs.
- HID console debug channels (EC stream, calibration, scan rate, USB, VIA,
  EEPROM) and `[SCAN]`/`[LAT]` scan diagnostics.
- Settings, keymaps, macros, combos and calibration stored in compressed
  EEPROM snapshots.

## Layout of this directory

- `config.h`: pins, matrix geometry, default keymap, build defaults.
- `modules/ec/`: matrix scan, ADC, calibration, Rapid Trigger, SOF lock.
- `modules/via_settings/`: VIA custom values, compact EEPROM storage.
- `modules/hybrid/`: USB/battery source detection and battery STOP.
- `modules/indicators_system/`: LEDs and the System 1/2 selector.
- `modules/grave_escape/`, `modules/dip_switch/`.
- `via.json`, `vial.json`: definitions (generated parts come from `config.h`).

## DIP switches

All six DIP switches are read (`HHKB_DIP_PINS` in `config.h`). SW6 (with SW5)
triggers the Bank 1 recovery path described in
[Backup & restore](docs/en/backup-restore.md#sw6-recovery). SW1-SW5 have no
other firmware function.

## Acknowledgements

Upstream [DMK](https://github.com/aroum/dmk) by aroum; the STOP sequence in
`hybrid_stop.c` is adapted from [l3tnun/hhkb_hybrid](https://github.com/l3tnun/hhkb_hybrid)
(MIT, `modules/hybrid/LICENSE.protocol`).
