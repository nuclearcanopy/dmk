**Documentation:** [Install](install.md) • [Backup & restore](backup-restore.md) • [Build](build.md) • [Config](config.md) • [VIA & debug](via-debug.md)

# Build

nxmk builds one image: HHKB Hybrid (ANSI) for the STM32L072. Run from the
repository root.

## Requirements

`cmake`, `make` and `arm-none-eabi-gcc` (`build_all.sh` uses the "Unix
Makefiles" generator). `uv` is needed only for the flasher and the host tests.

CI pins **Arm GNU Toolchain 15.3.Rel2**
(`.github/actions/setup-hhkb-toolchain/action.yml`). The build is `MinSizeRel`
(`-Os`) and has to fit Bank 2 (64 KiB). Use the pinned version for comparable
sizes: a different compiler changes the size.

## Build

```bash
./build_all.sh -b hhkb -d HHKB_HYBRID -c    # -c = clean build
bash tools/nxmk/check_image.sh              # size and vector gates
```

- `-d HHKB_HYBRID` is the only accepted selector; any other model selector
  makes CMake fail with "nxmk only builds the HHKB Hybrid (ANSI)".
- Other `-d` values are passed to the compiler as `-D` definitions (comma
  separated), e.g. `-d HHKB_HYBRID,HHKB_SOF_LOCK=0` (see
  [Config](config.md#build-definitions)).
- `--build-dir PATH` changes the output directory (default
  `build/hhkb-script`); `-m` adds extra user module directories.
- The script enables arbitrary RT key selection. Use `--legacy-rt` to leave
  RT feature flags at their config defaults, or to supply fixed-seven
  experimental flags explicitly with `-d`.

Output: `build/hhkb-script/nxmk_hhkb_stm32l072.bin` (raw Bank 2 image) and the
ELF of the same name. The Hybrid build does not produce an `.hfb`; package it
with the patcher in [Install](install.md#2-patch-the-official-hybrid-ansi-update).
Compiling does not flash the keyboard.

### Image gates

`tools/nxmk/check_image.sh [build-dir]` fails if the `.bin` exceeds 65,536
bytes, `.data + .bss` exceeds 20,480 bytes, the initial stack pointer is not in
SRAM (`0x2000xxxx`, 8-byte aligned) or the reset vector is not a Thumb address in
`0x0801xxxx`. CI additionally fails the build if the ELF contains symbols
matching `bluetooth|_bt_|nrf|pairing|gatt` (`build_test.yml`).

### Size, as built in this session

One local build of this tree on 2026-11-26 (commit 7f4e0805, Hybrid ANSI,
`DMK_FW_VERSION=pin-1`, `./build_all.sh -d HHKB_HYBRID -c`) with
`arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203`
(the nix `gcc-arm-embedded` package, **not** the pinned 15.3.Rel2). The `.bin`
sha256 is `6358ddabfdfb0fafa8d52bbc1e0cf008ec4029ca2d6e8be731128e2f3725beca`.
That historical command predates the personal RT selection defaults. Use
`--legacy-rt` for compatible feature flags when reproducing it.

`arm-none-eabi-size` (Berkeley format) on the ELF, and the `.bin` size:

| Item | Bytes |
| --- | ---: |
| `.bin` | 54,644 |
| text | 54,636 |
| data | 8 |
| bss | 15,400 |
| dec (total) | 70,044 |

`arm-none-eabi-size -A -d` on the same ELF reports `.data` 3,288, `.bss`
13,348 and `._user_heap_stack` 2,052 bytes. These numbers are indicative only;
they change with compiler and options.

## Container layout (Hybrid)

The patcher (`tools/hhkb/patch_hybrid_hfb.py`) produces a 282,672-byte `.hfb`
(`HYBRID_HFB_SIZE` in `hhkb_flasher.py`):

```text
outer CRC-16/MCRF4XX (2 bytes, over everything after it)
inner CRC-16/MCRF4XX (2 bytes, over the 64 KiB STM32 image)
STM32 Bank 2 image, padded with 0xFF (65,536 bytes)
factory second-chip payload (preserved unchanged)
model ID "AHUX01" (6), version (4), 6 x 0xFF
```

The container version nxmk writes is `A0.50`; the stock template it needs is
`A0.48`. The PFU-style version in the container is only used by the update
protocol; the firmware version shown in VIA (`DMK_FW_VERSION`, set from
`DMK_FW_VERSION` env/tag/git hash in `CMakeLists.txt`) is independent.

## Host tests

```bash
bash tests/run_all_tests.sh
```

See [tests/README.md](../../../../tests/README.md).
