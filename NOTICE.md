# nxmk licensing notice

nxmk is a HHKB Hybrid (ANSI, STM32L072) only derivative of
[DMK](https://github.com/aroum/dmk) by aroum. It carries no other MCU
platforms, keyboards or Bluetooth code.

## Licences in this repository

- **nxmk's own code** (files created in this fork and nxmk's modifications to
  upstream files) is licensed **AGPL-3.0-or-later**. The full text is in
  `LICENSE`. Files created in this fork carry
  `SPDX-License-Identifier: AGPL-3.0-or-later`. Modified upstream files that
  have an MIT SPDX header keep it and add
  `Modifications Copyright (C) 2026 nuclearcanopy, licensed AGPL-3.0-or-later.`
  Other modified upstream files are covered by this notice: nxmk's
  modifications to them are AGPL-3.0-or-later and the upstream parts remain MIT.
- **Upstream DMK** (Copyright (c) 2026 aroum) is MIT. The original text is kept
  verbatim in `LICENSE-MIT-UPSTREAM.md`. Upstream copyright lines and MIT SPDX
  headers are never altered.
- **l3tnun's MIT-licensed code**: `keyboards/hhkb/modules/hybrid/LICENSE.protocol`
  (Copyright (c) 2026 l3tnun) stays MIT and unchanged; `hybrid_stop.c` is adapted
  from that code.
- **Third-party libraries** keep their own licences; see `THIRD_PARTY.md`.

MIT code is compatible with AGPL-3.0, so the combined work is distributed
under AGPL-3.0-or-later, while each MIT/BSD/Apache component stays available
under its own terms. AGPL section 13 applies to modified versions that users
interact with over a network.

## What differs from DMK

- **Hybrid-only.** The build accepts only `-d HHKB_HYBRID` (HHKB Hybrid /
  Hybrid Type-S, ANSI). All other platforms, keyboards, the config wizard and
  related tests and CI were removed. The pico-sdk submodule was replaced by a
  vendored TinyUSB `src/` (`lib/tinyusb`); `lib/u8g2` was removed.
- **No Bluetooth.** The Nordic nRF52832 SPI link, pairing/profile handling,
  battery reporting, BT output routing and related VIA settings/keycodes are
  removed. The Hybrid module keeps only USB/battery detection and a
  battery-only STOP state (wakes on USB, then resets).
- Product string `nxmk HHKB Hybrid-S`, manufacturer `nxmk`, firmware target
  `nxmk_hhkb_stm32l072`. USB VID/PID (`cafe:4014`) and VIA raw HID are
  unchanged.

The stock vendor Nordic firmware in the keyboard's own flash is not part of
this repository and is not modified by it.
