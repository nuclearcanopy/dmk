**Documentation:** [Install](install.md) • [Backup & restore](backup-restore.md) • [Build](build.md) • [Config](config.md) • [VIA & debug](via-debug.md)

# VIA & debug

The firmware speaks VIA protocol v3 (`VIA_V3 1` in `config.h`) over a raw HID
interface; a second HID interface carries the debug console
(`ITF_NUM_VIAL`, `ITF_NUM_CONSOLE` in `dmk_core/drivers/usb_descriptors.c`).
Custom settings are value commands on channel 0
(`modules/via_settings/hhkb_via_controls.c`), described by
[`via.json`](../../via.json).

## Load the custom definition

1. Open the [VIA web app](https://www.usevia.app/).
2. **Settings** -> enable **Show Design tab**.
3. **Design** -> **Load Draft Definition** -> select `keyboards/hhkb/via.json`.
4. Connect the keyboard (**Authorize device**) and open **HHKB Settings**.

The keyboard appears as **nxmk HHKB Hybrid-S**, `cafe:4014`. Reload the
definition after updating firmware. If layer 0 legends are blank, switch to
layer 1 and back (VIA client rendering issue noted upstream, unverified here).

## Check USB detection

Use a data cable. In Chrome, `chrome://device-log` (watch connect events while
retrying **Authorize device**) and `chrome://usb-internals` (product, VID,
PID) show whether nxmk enumerated. Expect VID `0xCAFE`, PID `0x4014`. The
factory PFU interface uses VID `0x04FE`; the HHKB Keymap Tool cannot see
running nxmk (see [Install](install.md)). Outside Chrome use `lsusb` (Linux),
System Information (macOS) or Device Manager (Windows).

### Chromium on Linux cannot open the device

Give the active session user access to the hidraw node:

```bash
sudo tee /etc/udev/rules.d/70-hhkb-via.rules >/dev/null <<'EOF'
SUBSYSTEM=="hidraw", KERNEL=="hidraw*", ATTRS{idVendor}=="cafe", ATTRS{idProduct}=="4014", TAG+="uaccess"
EOF
sudo udevadm control --reload-rules
```

Replug the keyboard, reload VIA and authorize it again.

## VIA vs Vial

`vial.json` supports keymap editing in Vial. Vial cannot show the custom
controls below; use VIA for them.

## Systems

Assign **System 1** / **System 2** from the VIA keycode picker, or *Any*
`0x7E00` / `0x7E01` (`indicators_system.c`). System 1 uses layers 0 and 1,
System 2 layers 2 and 3. Put a selector reachable from each system.

## HHKB Settings reference

Value IDs are the `id` in `via.json` (channel 0).

### Scan Rate

| Control | ID | Notes |
| --- | ---: | --- |
| USB SOF phase lock (this session) | 61 | Toggle for the current session; not saved to EEPROM (`sof_lock.c`). |
| Target scan rate | 13 | 50 / 125 / 250 / 500 / 1000 Hz. |
| ADC oversampling (4x) | 18 | Ignored at 1000 Hz (`classic_matrix.c`). |

### Behavior

| Control | ID | Notes |
| --- | ---: | --- |
| Tapping term | 14 | 5-50 in 10 ms units (50-500 ms), default 22. |
| Permissive hold | 15 | |
| Tap preferred | 16 | |
| Quick tap | 17 | 0-50 in 10 ms units, 0 disables, default 15. |
| Always Escape with Alt / Ctrl / GUI / Shift | 57-60 | Grave Escape, see [Config](config.md#grave-escape). |
| Ignore modifier in reports | 66 | None / Alt / Ctrl / GUI. |

### Calibration

| Control | ID |
| --- | ---: |
| Use travel curve | 30 |
| ADC at 1 / 2 / 3 mm (%) | 31 / 32 / 33 |
| Maximum travel | 34 |
| Smoothing | 35 |
| Use custom calibration | 2 |
| Start calibration | 7 |
| Finish and save | 8 |
| Print status to HID Console | 27 |
| Actuation point | 1 |
| Release hysteresis (RT off) | 5 |

Ranges (from `via.json`): actuation, hysteresis and RT sensitivities
0.1-4.5 mm in 0.1 mm steps; ADC points 2-94% (1 mm), 4-96% (2 mm), 6-98%
(3 mm); maximum travel 3.1-4.5 mm; smoothing 0.0-1.0. The travel-curve
controls are shown only when **Use travel curve** is on.

### Rapid Trigger

| Control | ID | Range |
| --- | ---: | --- |
| Rapid Trigger | 3 | toggle |
| RT press sensitivity | 4 | 0.1-4.5 mm |
| RT release sensitivity | 11 | 0.1-4.5 mm |
| Top dead zone | 6 | 0.0-0.6 mm |
| Bottom dead zone | 65 | 0.0-1.0 mm, default 0.5 mm |

The sensitivity and dead zone controls are shown only with Rapid Trigger on. The bottom dead zone is
how far above bottom-out the release anchor stops following finger pressure
(`bottom_dz * 25` per-mille in `rapid_trigger.c`).

The physical-position toggles (channel 0, IDs 68-127) require a build with
`HHKB_RT_KEYMASK=1` and `HHKB_RT_ARBITRARY_SELECTION=1`. The shared definition
also displays them on other builds, where those IDs are unsupported. Positions
follow the ANSI layout, not keycodes or layers. The default selection is W, A,
S, D, Space, left Shift and left Ctrl. Selection is independent of master ID 3:
when it is off, selected keys also use classic behavior; unselected keys always
use classic behavior. The mask is saved in the compact EEPROM snapshot; older
snapshots without a mask use the default selection. The VIA definition has not
been validated in the GUI, and this does not add a Vial custom-settings UI.

### LED

**Blue LED (PA8)** ID 9 and **Orange LED (PA9)** ID 10, each: Off, Debug
heartbeat (1 Hz), Caps Lock, Fn layer, System 2.

### Power Saving

**Power Saving Mode** (ID 29, default on): with no USB host mounted or the bus
suspended, LEDs off, sensor board off, scanning stopped
([Config](config.md#power-and-usb-detection)).

### Debug

| Control | ID |
| --- | ---: |
| Firmware Version (read only) | 28 |
| EC Matrix Diagnostics | 19 |
| VIA Telemetry Diagnostics | 23 |
| Polling Rate Diagnostics | 24 |
| Calibration Diagnostics | 25 |
| USB Report Diagnostics | 62 |
| EEPROM Write Diagnostics | 67 |
| Arm reset / stock recovery | 37 |
| Erase DMK EEPROM and restart | 38 |
| Return to stock Bank 1 | 64 |

The six diagnostic toggles are flags saved with the other settings; all
default off. Dynamic labels (curve status, calibration status, EEPROM status)
are read only when you switch menu or reload VIA.

## Travel curve

When enabled, a monotonic piecewise cubic curve through 0 mm, the three ADC
points, and the maximum travel maps raw readings to travel (`dmk_core/features/ec_curve.c`).
The points and both endpoints must be at least 2 percentage points apart
(status `Points need 2% spacing` otherwise); a slope above 32 table units per step
is rejected as `Curve too steep (max 4x)`. A rejected or disabled curve falls
back to the linear scale (status `Disabled`; `Active` when in use). The curve
applies to actuation, hysteresis and Rapid Trigger. To preview it:

```bash
uv run tools/ec_curve_visualizer.py
```

## Key calibration

The Hybrid has no factory table in this firmware, so calibrate every key (see
[Config](config.md#calibration-data)).

1. Turn on **Use custom calibration** and release all keys.
2. **Start calibration**: baseline capture takes 16 samples per key. While
   calibrating the matrix reports no keys to the host (`ec/matrix.c`). The
   upstream notes say pressed positions still light up in VIA's **Key Tester ->
   Test Matrix**; that is unverified here. At a 1000 Hz target the
   scan runs at 500 Hz for the duration.
3. Fully press every key to bottom-out with normal force.
4. **Print status to HID Console** lists `[CAL] missing:` keys while
   calibrating, and `[CAL] unchanged:` keys afterwards.
5. **Finish and save** writes the new baseline/peak for keys with a valid
   range. Outside a calibration session the saved range does not expand.

Recalibrate after changing domes, rings or switches. Enable **Calibration
Diagnostics** to see progress in the console.

## Debug console

In VIA: **Settings** -> **Show HID Console tab**. Debug output is off by
default.

- **EC Matrix Diagnostics:** `[EC] R<row>C<col> r=<12-bit ADC> b=<baseline> p=<peak> t=<percent>% DN|UP`.
  Only the latest changed sample is sent, and only when raw moves more than
  +/-40 counts or the state flips.
- **Calibration Diagnostics:** `[CAL]` lines: baseline capture, per-key peak
  updates (`[CAL] R<r> C<c> peak: <old> -> <new>`), progress, final count.
- **Polling Rate Diagnostics:** `[RATE] matrix=<Hz>, usb_loop=<Hz>` and
  `[SCAN] actual=<Hz> | raw=<us> (max <us>) work_max=<us> | miss=<n> q_full=<n> (usb=<n>)`
  and `[LAT] age_avg=<us> age_max=<us> err=<us> lock=<n> lead=<us> in=<us>`.
  `matrix` is the measured scan rate; `usb_loop` is the USB task loop, not the
  HID polling rate. `work_max` should stay below the scan period with headroom;
  `miss` should stay 0; `q_full` counts failed matrix-queue submissions.
  `lock=0` means the SOF lock is off or not acquired.
- **USB Report Diagnostics:** once per second while USB is active,
  `[USB] s d b dr rs q` (submitted, done, busy, dropped, resync, queued) (cumulative counters for keyboard and
  consumer reports; VIA and console traffic excluded). `dr` counts reports
  abandoned after bounded retries; `rs` counts overflow-recovery
  snapshots.
- **VIA Telemetry Diagnostics:** `[VIA] rx tx_sub tx_cpl tx_fail pend` (values only, in that order)
  for VIA v3 traffic.
- **EEPROM Write Diagnostics:** `[EEPROM]` lines for save and write failures.

When comparing runs, keep console settings identical (logging itself affects
timing) and ignore the first interval after changing settings or calibrating
(the threshold cache is rebuilt).

### Scan diagnostics

`HHKB_SCAN_DIAGNOSTICS` is on in the default build, so no special build is
needed. For an instruction-level estimate of scan cost there is an optional
emulator (`tools/hhkb/scan_emu.py`, MIT, `tools/hhkb/LICENSE.scan_emu`):

```bash
uv run --with unicorn --with pyelftools tools/hhkb/scan_emu.py time build/hhkb-script/nxmk_hhkb_stm32l072
```

It needs `arm-none-eabi-nm` on `PATH` and estimates peripheral timing: use it
for relative comparisons only. No hardware scan-timing result is recorded in
this repo; `[SCAN]` on a unit is the way to check headroom.

## Reset DMK data or return to stock

**HHKB Settings -> Debug**, with SW6 OFF: enable **Arm reset / stock recovery**,
then one of:

- **Erase DMK EEPROM and restart:** clears the recognized nxmk/DMK records
  (calibration, curve, settings, keymaps, macros, combos) and restarts with
  defaults.
- **Return to stock Bank 1:** performs the same Bank 1 transition as SW6
  recovery ([Backup & restore](backup-restore.md#sw6-recovery)): the nxmk
  EEPROM is kept and the first 128-byte page of Bank 2 is erased.

Both require arming and consume it. The status line reads `Ready`, `Armed`,
`Resetting DMK...`, `Returning to Bank 1...`, `Restarting...`,
`Reset failed; retry`, or `Set SW6 to OFF` (`dmk_core/features/vial.c`).

## EEPROM storage

Keymaps (4 layers), combos, the macro buffer, calibration, curve and settings
are stored as one atomic compressed snapshot. Layout
(`modules/via_settings/hhkb_compact_storage.inc`):

- Two 880-byte slots, each with a 20-byte header and 860 bytes of payload, plus
  a small ownership header; physically fragmented across several ranges of the
  6 KiB EEPROM (the table is in `c_word()`).
- A generation number, checksum and commit marker validate a slot; the
  previous slot stays valid until the replacement is committed.
- Writes are deferred about 0.5 s after the last change
  (`HHKB_SETTINGS_SAVE_DELAY_MS`) and unchanged snapshots are skipped.
- Status (`Settings EEPROM`): `Pending`, `Saving`, `Saved (compressed)`,
  `Occupied: not saved` (an unknown nonzero word blocked enrollment),
  `Full: not saved` (the configuration does not compress into a slot),
  `Write failed: retrying`.

Do not unplug until it reports `Saved (compressed)`. These EEPROM address
ranges were chosen from an upstream map; this repo has no full Hybrid EEPROM
dump, so treat "free" ranges as *unverified* and keep a backup (see
[Backup & restore](backup-restore.md)).
