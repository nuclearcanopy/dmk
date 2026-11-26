# Third-party code

Each entry was verified against the licence file or in-file headers named
below. All are compatible with distribution inside an AGPL-3.0-or-later
combined work (MIT and BSD-3-Clause are permissive; Apache-2.0 is
one-way compatible with GPLv3/AGPLv3). Each keeps its own licence and notices.

| Component | Location | Licence | Verified from |
| --- | --- | --- | --- |
| TinyUSB (hathach, tinyusb.org), `src/` only; `portable/` trimmed to `st/stm32_fsdev`. One file there (`fsdev_ch32.h`, not compiled) carries an ST BSD-3-Clause header | `lib/tinyusb/` | MIT | `lib/tinyusb/LICENSE` ("The MIT License (MIT)", Copyright (c) 2018 hathach); ST header in `fsdev_ch32.h` |
| FreeRTOS Kernel V11.1.0 (Amazon.com, Inc.), including the Cortex-M0+ port in `platforms/stm32l072/freertos_port/` and `dmk_core/config/FreeRTOSConfig.h` | `lib/freertos/` | MIT | per-file `SPDX-License-Identifier: MIT` and MIT permission text; there is no standalone licence file |
| CMSIS Core (Arm Limited; `cmsis_iccarm.h` also IAR Systems) | `platforms/stm32l072/dep/cmsis_core/` | Apache-2.0 | per-file `SPDX-License-Identifier: Apache-2.0` and Apache licence text; no standalone licence file |
| CMSIS Device L0 (STMicroelectronics) | `platforms/stm32l072/dep/cmsis_device_l0/` | Apache-2.0 | `LICENSE.md` (Apache License 2.0, Copyright 2019 STMicroelectronics) |
| STM32L0xx HAL/LL driver (STMicroelectronics) | `platforms/stm32l072/dep/stm32l0xx_hal_driver/` | BSD-3-Clause | `LICENSE.md` (three-clause BSD, Copyright 2017 STMicroelectronics) |
| STOP/power sequence adapted into `hybrid_stop.c` (l3tnun) | `keyboards/hhkb/modules/hybrid/` | MIT | `LICENSE.protocol` (Copyright (c) 2026 l3tnun), unchanged |
| `scan_emu.py` development aid (aroum, adapted from blandjelly/dmk) | `tools/hhkb/` | MIT | `tools/hhkb/LICENSE.scan_emu` (Copyright (c) 2026 aroum) |

Upstream DMK code (aroum) is MIT; its text is in `LICENSE-MIT-UPSTREAM.md`.
See `NOTICE.md` for how nxmk's own code is licensed.

No vendored component is GPL-2.0-only or otherwise incompatible with AGPL-3.0.
