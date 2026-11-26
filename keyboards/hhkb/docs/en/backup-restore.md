**Documentation:** [Install](install.md) • [Backup & restore](backup-restore.md) • [Build](build.md) • [Config](config.md) • [VIA & debug](via-debug.md)

# Backup & restore

Back up Flash, EEPROM and Option Bytes of **your own board** before the first
flash. EEPROM holds board-specific factory data plus nxmk's settings: never
copy EEPROM from another keyboard.

> The hardware procedures below (pad locations, DFU entry, SWD pinout) are
> inherited from upstream DMK notes. They have not been re-verified for this
> fork in this repository; identify the pads from your own board before
> shorting or soldering anything.

## Memory map (STM32L072)

| Area | Address | Purpose |
| --- | --- | --- |
| Bank 1 | `0x08000000-0x0800FFFF` | Factory PFU updater (do not overwrite) |
| Bank 2 | `0x08010000-0x0801FFFF` | Application: stock firmware or nxmk |
| EEPROM | `0x08080000-0x080817FF` (6 KiB) | Factory data, boot flags, nxmk settings |
| Option Bytes | `0x1FF80000-0x1FF8001F` | Protection and boot options |

Boot flag used by the recovery code on the Hybrid: EEPROM byte `0x08080360`
(`hhkb_enter_bank1()` in `dip_switch.c` writes `0x00`).

## STM32 ROM DFU

ROM DFU does not depend on Bank 1 or Bank 2. Upstream notes: open the case, and
while connecting USB short the right-hand pads of R6 and R85 to raise BOOT0;
the device should then enumerate as `0483:df11`. Remove the short afterwards.

```bash
dfu-util -l
dfu-util -a 0 -s 0x08000000:131072 -U hhkb-flash-full.bin   # Bank 1 + Bank 2
dfu-util -a 2 -s 0x08080000:6144   -U hhkb-eeprom.bin
dfu-util -a 1 -s 0x1FF80000:32     -U hhkb-option-bytes.bin
```

Restore Bank 2 only (raw `.bin`, not `.hfb`; same-board backup):

```bash
dfu-util -a 0 -s 0x08010000 -D hhkb-bank2-stock-firmware_64k.bin
```

Write an nxmk image directly:

```bash
dfu-util -a 0 -s 0x08010000 -D build/hhkb-script/nxmk_hhkb_stm32l072.bin
```

DFU does not update the PFU Bank 1 boot metadata, so Bank 1 can still refuse
the image. Prefer the PFU update path in [Install](install.md). A readback
only proves Flash contents, not Bank 1 acceptance:

```bash
dfu-util -a 0 -s 0x08010000:65536 -U bank2-readback.bin
cmp -n "$(wc -c < build/hhkb-script/nxmk_hhkb_stm32l072.bin)" \
  build/hhkb-script/nxmk_hhkb_stm32l072.bin bank2-readback.bin
```

Restore a full same-board backup by writing Flash and EEPROM separately; write
Option Bytes only if needed and only from the same board's backup.

## SWD / J-Link

Pads beside connector CN3 (upstream notes, two rows):

```text
GND  NRST  VCC
 SWCLK SWDIO
```

SWDIO = `PA13`, SWCLK = `PA14` (STM32L072 fixed functions). VCC to the J-Link
`VTref` only senses the 3.3 V reference when the keyboard is USB powered; do
not power the board from USB and the programmer at once.

`backup_jlink.jlink`:

```text
r
halt
savebin hhkb_full_flash_128k.bin 0x08000000 0x00020000
savebin hhkb_bank1_64k.bin       0x08000000 0x00010000
savebin hhkb_bank2_64k.bin       0x08010000 0x00010000
savebin hhkb_eeprom_6k.bin       0x08080000 0x00001800
savebin hhkb_option_bytes.bin    0x1FF80000 0x00000020
q
```

```bash
JLinkExe -device STM32L072RB -if SWD -speed 4000 -autoconnect 1 -CommanderScript backup_jlink.jlink
```

Restore Flash and EEPROM (Option Bytes deliberately excluded) with
`loadbin hhkb_full_flash_128k.bin 0x08000000` and
`loadbin hhkb_eeprom_6k.bin 0x08080000` between `r`/`halt` and `r`/`g`/`q`.

The Hybrid's other chip has its own flash; this firmware does not touch it,
and this document does not cover backing it up.

## SW6 recovery

With `HHKB_SW6_REBOOT_TO_BANK1=1` (default), `hhkb_early_dip_check()` samples
SW6 (`PC4`) at startup before the scheduler runs. If it reads ON for the full
debounce window (10 samples of about 1 ms), `hhkb_enter_bank1()`:

1. writes `0x00` to EEPROM byte `0x08080360` (Hybrid boot-enable flag),
2. erases the first 128-byte page of Bank 2 (`0x08010000`) from RAM,
3. resets into Bank 1.

The erased page holds the stack pointer and reset vector, so Bank 2 cannot
boot until a complete image is written back (PFU updater, DFU or SWD). Return
SW6 to OFF once the Bank 1 USB device appears and keep it OFF in normal use.
Then flash the stock or an nxmk `.hfb` as in [Install](install.md).

### SW5 + SW6: erase nxmk settings, then enter Bank 1

| SW5 | SW6 | Action at startup |
| --- | --- | --- |
| OFF | OFF | Normal startup |
| ON | OFF | Normal startup |
| OFF | ON | Enter Bank 1, keep nxmk EEPROM records |
| ON | ON | Erase recognized nxmk EEPROM records, then enter Bank 1 |

SW5 (`PA7`) is sampled only together with SW6. The erase
(`hhkb_storage_erase_early()`) removes the compressed slots and ownership
header plus recognized older DMK records; unknown records and factory data are
left alone (as documented upstream; see `hhkb_compact_storage.inc`). If an EEPROM write fails, Bank 2 is **not** erased and startup halts
(`hhkb_recovery_flash_error = 0x40000000`, readable over SWD): reconnect stable
power and retry. Do not remove power during the erase.

The VIA **Debug** buttons offer the same two outcomes without DIP switches
(they refuse to run unless SW6 is OFF; see
[VIA & debug](via-debug.md#reset-dmk-data-or-return-to-stock)).

## Restoring stock

Use SW6 to reach Bank 1, then write the official `HHKB800_FW_A048.hfb` with the
[Keymap Tool](https://happyhackingkb.com/download/) or `hhkb_flasher.py`. The
Keymap Tool cannot see a running nxmk.

Earlier DMK builds could overwrite factory EEPROM regions; whether anything in
this fork's storage ranges overlaps PFU data on your unit is *unverified*
without a full Hybrid EEPROM backup. This repository contains none. Keep your own.
