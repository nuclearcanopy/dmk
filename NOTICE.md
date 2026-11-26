# nxmk

nxmk is a derivative of [DMK](https://github.com/aroum/dmk) by aroum
(`upstream` remote), distributed under the same MIT license (see `LICENSE`).
The original copyright notice is retained. Third-party notices stay in place
(for example `keyboards/hhkb/modules/hybrid/LICENSE.protocol`, MIT, l3tnun,
covering the STOP/power sequence that `hybrid_stop.c` is adapted from).

## What differs from DMK

- **Hybrid-only.** The build accepts only `-d HHKB_HYBRID` (HHKB Hybrid /
  Hybrid Type-S, ANSI). Other HHKB models and the JIS layout are rejected by
  CMake unless `-DNXMK_ALLOW_UPSTREAM_TARGETS=ON`. Other keyboards' sources are
  kept only so upstream changes still merge cleanly.
- **No Bluetooth.** The Nordic nRF52832 SPI link, pairing/profile handling,
  battery reporting, BT output routing and all related VIA settings/keycodes
  are removed from the build. The Hybrid module keeps only USB/battery
  detection and a battery-only STOP state (wakes on USB, then resets).
- Product string `nxmk HHKB Hybrid-S`, manufacturer `nxmk`, firmware target
  `nxmk_hhkb_stm32l072`. USB VID/PID (`cafe:4014`) and VIA raw HID are
  unchanged.

The stock vendor Nordic firmware that lives in the keyboard's own flash is not
part of this repository and is not modified by it.
