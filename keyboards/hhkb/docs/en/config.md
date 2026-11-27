**Documentation:** [Install](install.md) • [Backup & restore](backup-restore.md) • [Build](build.md) • [Config](config.md) • [VIA & debug](via-debug.md)

# Configuration

Everything here is read from `keyboards/hhkb/config.h` and the modules under
`keyboards/hhkb/modules/` unless marked *unverified*.

## Build definitions

Pass extra definitions to `build_all.sh -d` after `HHKB_HYBRID`, comma
separated (see [Build](build.md)).

| Define | Default | Effect |
| --- | --- | --- |
| `HHKB_HYBRID` | required | Selects the only supported target. Enables the USB/battery source detection and battery STOP module. |
| `HHKB_SOF_LOCK` | `1` | Locks the scan to the USB frame so reports reach the host's next poll sooner. `-d ...,HHKB_SOF_LOCK=0` builds without it. |
| `HHKB_SOF_MARGIN_US` | `150` | Lead margin (microseconds) added to the tracked scan work time when the lock picks its target. |
| `HHKB_SCAN_DIAGNOSTICS` | defined (`1`) | Adds scan counters, the `[SCAN]`/`[LAT]` console lines and the SWD-visible counters. The code tests it with `#ifdef`, so passing `=0` does **not** turn it off; removing the default in `config.h` would. |
| `HHKB_SW6_REBOOT_TO_BANK1` | `1` | SW6/SW5+SW6 recovery at boot. With `0`, SW6 instead disables USB power saving (`dip_switch.c`). |

## Matrix and pins

ANSI: 4 rows x 15 columns, 60 keys (`NUM_ROWS`, `MATRIX_COLS`, `NUM_KEYS` in
`config.h`). The VIA definition reports 5 rows (`VIA_PROTOCOL_MATRIX_ROWS`).

- Rows: `PB0`, `PB1`, `PB2`, `PB10` (`HHKB_ROW_BITS`).
- Columns: two analog multiplexers, enabled by `PC6` (columns 0-7) and `PB15`
  (columns 8-14), with channel address lines `PB12`, `PB13`, `PB14`.
- Analog front end: `PC14` sensor power, `PC7` op-amp enable, `PC8`
  discharge, ADC channel 1 (`PA1`).
- DIP switches: `PA3`-`PA7` and `PC4`, active low (`HHKB_DIP_PINS`).
- LEDs: `PA8` (blue) and `PA9` (orange) (`LED_PINS`).

The scanner is timer driven (TIM2) and its hot path lives in RAM
(`.RamFunc`). Periods come from `update_scan_period()` in `ec/matrix.c`:
50 Hz (a 10 ms timer with a divide-by-2), 125, 250, 500 and 1000 Hz
(8, 4, 2, 1 ms). While calibrating at a 1000 Hz target the scan runs at half
rate (500 Hz). The CPU runs at 32 MHz (`platforms/stm32l072/platform.c`).
Whether 1000 Hz is actually sustained is not guaranteed: check `[SCAN]` and
`[RATE]` in the HID console (see [VIA & debug](via-debug.md#scan-diagnostics)).

## Defaults

Values at first boot or after an EEPROM erase (`ec/ec_settings.c`,
`ec/rapid_trigger.c`, `config.h`):

| Setting | Default |
| --- | --- |
| Target scan rate | 1000 Hz |
| ADC oversampling 4x | off (and always bypassed at 1000 Hz) |
| Actuation point | 1.4 mm nominal (350 per-mille) |
| Release hysteresis (RT off) | 0.4 mm nominal (100 per-mille) |
| Rapid Trigger | 7 keys (W, A, S, D, Space, left Shift, left Ctrl) |
| RT press / release sensitivity | 0.1 mm nominal (25 per-mille each) |
| RT top dead zone | 50 per-mille (0.2 mm nominal) |
| RT bottom dead zone | 0.5 mm |
| Tapping term / quick tap | 220 ms / 150 ms |
| Permissive hold / tap preferred | on / off |
| LEDs | PA8 = Caps Lock, PA9 = Fn layer |
| USB power saving | on |
| Debug flags | all off |

"Nominal" millimetres assume 4 mm over the calibrated range, or the travel
curve's maximum travel when the curve is enabled. While *Use custom
calibration* is off, RT press/release below 0.4 mm are raised to 0.4 mm
(`hhkb_get_scan_cfg()`).

## Calibration data

The Hybrid has no factory threshold mapping in this firmware: `ec_settings.c`
returns no factory baseline (`get_factory_baseline` returns 0 under
`HHKB_HYBRID`). Without saved calibration every key uses a default baseline of
800 ADC counts and a peak of baseline + 2370, so run the calibration
procedure in [VIA & debug](via-debug.md#key-calibration) before relying on
actuation or Rapid Trigger.

Calibration stores per-key baseline and peak (accepted baseline 20-2000
counts, peak at most 4095 and more than 150 above baseline) in the
[compressed EEPROM snapshots](via-debug.md#eeprom-storage).

## USB SOF lock

`ec/sof_lock.c` uses the CRS SYNC interrupt (which tracks USB SOF) to measure
the 1 ms frame period and the host's IN-poll phase, then times the scan so a
published report is armed shortly before the next poll. The lead is the tracked
worst-case scan work plus `HHKB_SOF_MARGIN_US`, clamped in the source. It can be
switched off for the current session from VIA (**Scan Rate -> USB SOF phase
lock**, value ID 61). With `HHKB_SCAN_DIAGNOSTICS`, `[LAT]` shows
`age_avg`/`age_max` (timer compare of a publishing scan to the USB report
completion callback), `err`, `lock`, `lead` and `in`.

No measurement of this fork's SOF behaviour is recorded in this repository.
Any measurement made outside this repository is not reproduced here. Verify on your unit with
the [checklist](../../../../docs/en/tests.md).

## Power and USB detection

`modules/hybrid/`: `PC13` reads low on USB power and high on battery.

- **USB:** normal operation. With **Power Saving Mode** on (default) and no USB
  host mounted, or the bus suspended, LEDs go off and the sensor board is
  powered down (`PC14`, `PC7` low) and scanning stops; scanning resumes when the
  host returns.
- **Battery:** there is no output path, so the keyboard stops scanning,
  releases published keys, blanks the LEDs, shuts down USB and the ADC, and
  enters STOP (`hybrid_stop.c`). A change of `PC13` to USB power wakes it and
  resets the MCU (`NVIC_SystemReset`). The power button on `PC5` is not
  referenced anywhere in the firmware.
- In STOP the IWDG is refreshed after each LPTIM1 wake-up (about every
  1.7 s per the comment in `hybrid_stop.c`).

Current draw in any of these states has not been measured in this repo.

## Hold-tap and layers

One `HT(hold, tap)` model is used internally; VIA Mod-Tap / Layer-Tap convert
to it (see [keycodes](../../../../docs/en/keycodes.md#universal-hold-tap)). Four
layers exist (`DYNAMIC_KEYMAP_MAX_LAYERS 4`): layers 0/1 are system 1 and
layers 2/3 are system 2. The keycodes **System 1** and **System 2**
(`0x7E00`, `0x7E01`) switch between them
(`modules/indicators_system/indicators_system.c`).

## Grave Escape

`KC_GESC` (`0x7C16` through VIA *Any*; `modules/grave_escape`) sends Escape with
no modifier. Four toggles (Alt, Ctrl, GUI, Shift) force Escape when that
modifier is held; otherwise Grave is sent. **Ignore modifier in reports**
(None, Alt, Ctrl, GUI; value ID 66) suppresses that modifier in the report for
a GESC press. Settings are stored in EEPROM with the other settings. The
value `0x7C16` is not defined in this repository's code: it is the VIA/QMK
`QK_GESC` code, `unverified` here.
