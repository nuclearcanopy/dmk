# nxmk

nxmk is a radio-free, HHKB Hybrid (ANSI, STM32L072) only derivative of
[DMK](https://github.com/aroum/dmk). It builds one firmware image and carries
no other MCU platforms, keyboards or Bluetooth code. Licensing: see
[NOTICE.md](NOTICE.md) and [THIRD_PARTY.md](THIRD_PARTY.md). nxmk's own code is AGPL-3.0-or-later (`LICENSE`); upstream DMK MIT text is in `LICENSE-MIT-UPSTREAM.md`.

## Build

```bash
./build_all.sh -b hhkb -d HHKB_HYBRID -c   # needs cmake, make, uv, arm-none-eabi-gcc
bash tools/nxmk/check_image.sh              # size and vector gates
```

Output: `build/hhkb-script/nxmk_hhkb_stm32l072.bin`.

## Layout

- `dmk_core/` shared firmware core
- `platforms/stm32l072/` MCU platform (CMSIS/LL drivers, FreeRTOS port, linker script)
- `lib/freertos`, `lib/tinyusb` vendored libraries
- `keyboards/hhkb/` HHKB firmware modules, VIA/Vial definitions and [docs](keyboards/hhkb/README.md)
- `tools/hhkb/` flasher and Hybrid patcher, `tools/vial/` layout generation, `tools/nxmk/` image gates
- `tests/` host tests: `bash tests/run_all_tests.sh` (see [tests/README.md](tests/README.md))
