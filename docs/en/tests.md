# Hardware validation checklist

Planned physical checks for the HHKB Hybrid Type-S (ANSI). Every item is
unchecked; measured results are recorded in the dated session sections at the
end of this file, and only for the steps actually run. A result whose raw log
is not committed to the repository (for example the 2026-11-27 logs kept
under `/tmp` and `~/hhkb-test`) is provisional and must not be cited as a
verified measurement until its log is committed.

Record the firmware commit, host OS, USB topology, VIA settings and
measurement equipment with each result. Host tests
([tests/README.md](../../tests/README.md)) cover encoding, state machines and
bounds only; they do not establish wire timing, latency or power.

How to run: do the action, compare with the acceptance text of its procedure,
and write down what you saw under *Record*. If acceptance does not hold, stop
and note it; do not continue past a step that says **STOP**. Write "not
measured" rather than a guess. Save logs as described under
[Recording results](#recording-results).

Set up and flash first (the flash procedure is under
[Update, recovery and persistence](#update-recovery-and-persistence), listed
last because its checklist items are about flashing and recovery); after that
the measurement sections can run in any order. This file is the single source
of truth for hardware verification; it merges the former hardware test plan
(branch `docs/hardware-test-plan`). Procedures are the session steps only:
firmware reference material (VIA control IDs, console line formats,
calibration mechanics, EEPROM and recovery semantics) lives in
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md) and is linked, not
repeated.

## Test images and session setup

**Images.** Build each image you will flash from one tree and one commit with
only the listed flags differing
([Build](../../keyboards/hhkb/docs/en/build.md)), patch each `.bin` into its
own `.hfb` with `tools/hhkb/patch_hybrid_hfb.py` against your own official
`HHKB800_FW_A048.hfb`
([Install](../../keyboards/hhkb/docs/en/install.md); the patcher refuses any
other stock file), and never commit or share a patched `.hfb`.

| Image | Build flags | Needed for |
| --- | --- | --- |
| release | none (default) | everything except the checks that name another image |
| diagnostics | `HHKB_STALL_DIAG=1` | the `[STALL]` stall check (USB SOF section) |
| idle slow-scan | `HHKB_IDLE_SLOW_SCAN=1` | the idle scan check (EC section), optional |

Unless you override `DMK_FW_VERSION` the images share one version string (VIA
ID 28) and cannot be told apart by it. Record the `sha256` of every `.bin`
and `.hfb` you flash (`sha256sum` before every flash), identify an image by
that hash before flashing, and afterwards by `[STALL]` output (diagnostics)
or the idle scan rate (idle slow-scan).

**Safety and preconditions.**

1. Keep a second keyboard (the laptop's own) available: flashing and the
   Bank 1 return take the HHKB out of service until the smoke checks pass.
2. Host on AC power (or battery above 50 %) with sleep disabled for the
   session: a suspend during a flash is not acceptable.
3. HHKB on a direct USB port with a data cable, USB powered. Battery and
   Bluetooth operation is out of scope: the firmware shuts USB off on battery
   ([Config](../../keyboards/hhkb/docs/en/config.md#power-and-usb-detection)).
4. Flashing is slow and the total wall time is unverified. Do not unplug the
   keyboard, close the terminal or sleep the host until the flasher prints
   its result.
5. Model check: underside label Hybrid Type-S ANSI;
   `tools/hhkb/hhkb_flasher.py --info` must print a `PD-KB800...` model and
   the container model must be `AHUX01`. Do not use `--force`, `--skip-crc`
   or `--skip-model-check`.
6. Keep a full same-board backup (Flash, EEPROM, Option Bytes) before the
   first flash
   ([Backup & restore](../../keyboards/hhkb/docs/en/backup-restore.md); the
   DFU/SWD hardware procedures there are inherited from upstream and not
   re-verified) and keep the official `HHKB800_FW_A048.hfb` at hand for
   rollback. Never restore another board's EEPROM.
7. SW5/SW6 stay OFF except in the recovery steps that say otherwise.
8. Chromium on Linux needs the hidraw udev rule before VIA can open the
   keyboard
   ([VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#chromium-on-linux-cannot-open-the-device)).
9. Create the results directory for the session, for example
   `mkdir -p ~/hhkb-test/results/$(date +%F)`.

**VIA channel.** Scripted steps use the VIA raw HID channel (usage page
`0xFF60`, usage `0x61`, 32-byte packets on `cafe:4014`; the PFU/stock
interface is `04fe`): GET `08 00 <id>`, SET `07 00 <id> <val>`, and the reply
carries the value (or a 28-char string) from byte 3
(`via_custom_value_command_kb`). Control names and IDs are listed in
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#hhkb-settings-reference).
Sensitivity values (RT press/release, actuation, hysteresis, reset) are steps
of 0.1 mm at 4 mm travel (value x 25 per-mille); the bottom dead zone (ID 65)
uses the same scale, default value 5 = 0.5 mm. The `via.py` helper (see
[Helper scripts](#helper-scripts)) wraps this channel; the VIA web app with
`keyboards/hhkb/via.json` loaded does the same work manually.

## USB SOF scheduling and latency

- [ ] Record `[LAT]` (`age_avg`, `age_max`, `lock`) with the lock on and off during typing.
- [ ] Capture USB SOF, keyboard IN transactions and scan timing with a USB analyzer or logic analyzer before interpreting `[LAT]` as end-to-end latency.
- [ ] At 1000 Hz, compare locked and unlocked delay, jitter and missed polls under idle, typing, repeated presses and chords.
- [ ] Check reacquisition after connect, SOF interruption and host resume, with no stuck keys.
- [ ] Compare direct USB, hubs/dock and at least two hosts.
- [ ] Switch VIA scan rates 50/125/250/500/1000 Hz while connected; check no drift or starved USB work.
- [ ] Test suspend/resume, replug and connecting with a key held.

**Setup.** Compare builds with `HHKB_SOF_LOCK=0` and `HHKB_SOF_LOCK=1`
(default) on the same unit, with `HHKB_SCAN_DIAGNOSTICS` (default) and
**Polling Rate Diagnostics** on. The lock can also be toggled for the session
in VIA under Scan Rate. `HHKB_SOF_MARGIN_US` defaults to 150. Console line
formats (`[SCAN]`, `[LAT]`, `[RATE]`) are documented in
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#debug-console); keep
console settings identical between compared runs and ignore the first
interval after changing anything (logging itself changes timing). Per run,
capture 3 minutes of steady typing and 3 minutes idle (hands off) and save
the console text; each line type prints about 60 times per minute, so check
the line count to spot console truncation.

**Stall check (diagnostics image).** Flash the `HHKB_STALL_DIAG=1` image as
described under
[Update, recovery and persistence](#update-recovery-and-persistence). The
`[STALL]` line prints once per second beside `[SCAN]` while Polling Rate
Diagnostics is on, and exists only in this build (with
`HHKB_SCAN_DIAGNOSTICS`, default). Values are peaks/counters for the last
second and then cleared; at 12 ms or more the resolution is about 1 ms
because the timer wraps at 16.4 ms (`keyboards/hhkb/stall_diag.h`).

| Field | Meaning | Points to |
| --- | --- | --- |
| `eeprom_max` | longest `vial_eeprom_task()` call | flash write time (whole save job) |
| `tud_max` | longest `tud_task_ext()` call | USB job length |
| `flash n / fail / max` | EEPROM word writes, failures, longest single word write | flash write time |
| `wake_peak` | longest delay from the scan timer firing to the matrix task running | wake latency |
| `>5ms` | scans whose wake delay exceeded 5 ms | wake latency |
| `adc_to` | ADC conversions that timed out | scan problem |
| `scan_ovr` | scans containing at least one timed-out ADC read | scan problem |
| `susp`, `pwrsave`, `sens_down` | USB suspended, power saving enabled, sensor board powered down | context |

Search each capture for any second where `tud_max`, `eeprom_max`, `flash max`
or `wake_peak` is roughly 20000 us or more together with a non-zero `miss` or
`>5ms`, or `[LAT] age_max` around 20000 us or more. The threshold is a search
heuristic, not a target: no stall measurement is recorded in this repository.
Then attribute what you find: `tud_max` high with the rest small is the USB
job; `flash max`/`eeprom_max` high with `flash n` non-zero is a flash write
(trigger one deliberately by changing a VIA setting and waiting for the
deferred save); `wake_peak` high with `>5ms` non-zero and the others small is
the wake latency; several fields high at once: record all of them. All fields
small and `miss=0` for a whole capture means "not seen under these
conditions", not proof of absence.

**Record.** Per run: `age_avg`/`age_max`/`lock`, the stall search result and
which field carried it, the `[SCAN]`/`[RATE]` numbers, typing speed, whether
a VIA change was made during the window, and for the analyzer runs the
captured waveforms.

## EC sampling and calibration

- [ ] Record `[SCAN]`/`[RATE]` at 1000 Hz with Rapid Trigger and the travel curve off/on; confirm `work_max` has headroom and `miss` stays 0.
- [ ] Measure row strobe, discharge and ADC acquisition timing with a logic analyzer or oscilloscope.
- [ ] Calibrate every key; confirm each can be captured and values survive Finish and a cold power cycle.
- [ ] Calibrate at 500 and 1000 Hz targets with **Calibration Diagnostics** on and off; VIA stays connected and normal input resumes without a stuck key.
- [ ] Repeat the resting test with **EC Matrix Diagnostics** on and record any change in scan timing.

**Scan recording.** Use the captures from the USB SOF section (line meanings:
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#debug-console)) at
1000 Hz with the Rapid Trigger mode and the travel curve off and then on, and
again with **EC Matrix Diagnostics** (ID 19) on: `work_max` must keep headroom
below the scan period and `miss` must stay 0 in every combination. The
diagnostics image is not needed (`HHKB_SCAN_DIAGNOSTICS` is on by default).

**Calibration run.** Capture mechanics are in
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#key-calibration): the
matrix reports no keys to the host while calibration runs, so keep the second
keyboard in charge. Known hazard: the baseline can be captured too low and
saved, and the firmware accepts it; an analysis of the failure mode is in
`docs/analysis/calibration-sag.md` on the kept branches
(`analysis/calibration-sag`, `fix/calibration-sag`, `test/remote-wakeup`).
Its sag claims are not confirmed on hardware; the 2026-11-27 session
confirmed only the capture-gate reject mechanism (see
[2026-11-27](#2026-11-27)).

1. Record the current state and leave the keyboard idle about 10 s, all keys
   up, no VIA traffic.
2. Turn on **Use custom calibration** (ID 2), **EC Matrix Diagnostics** (ID
   19) and **Calibration Diagnostics** (ID 25), open the VIA HID Console, and
   record the "before" values. An `[EC]` line prints `r` (raw), `b`
   (baseline), `p`, `t` and the state for a key only when that key's raw
   moves about +/-40 counts or its state flips, so briefly press and release
   each key you want to read at rest.
3. **Start calibration** (ID 7), then check engagement before touching any
   key: the status (ID 26) must read `In progress: 0/60 keys` (or `N/60`).
   `Using defaults`, `Pending` or a `saved custom ranges` string means it did
   not start: do not press keys; repeat Start once, then stop. (IDs 7 and 8
   read back 0 always and cannot be used to check.)
4. Press every key fully to bottom-out with normal force, one at a time, and
   watch the status count to `60/60`, or use **Print status to HID Console**
   (ID 27) for the `[CAL] missing:` list.
5. **Before Finish and save** (ID 8), all keys released: if any key shows
   `DN` at rest in the console output, its baseline is sagged. Do not Finish;
   turn **Use custom calibration** off (back to defaults) and record the
   console. The rule of thumb from the analysis is that a resting key's `r`
   should sit within about 150 counts (`RT_MIN_RANGE`) of its `b`, but apply
   it only to keys that printed a line. Whether a started calibration can be
   abandoned without Finish is unverified; if the keyboard stays mute, replug
   it (nothing is saved until Finish) and record that.
6. **Finish and save** (ID 8). Expect `[CAL] Finished. Updated N/60 keys.`
   and, once the save lands, status `60/60 saved custom ranges` (`Pending`
   while the save is in flight). Typing must work again with no stuck key.
7. Verify: with ID 19 on, three keys at rest read `r` close to `b`, state
   `UP`; pressing each one rises `t=` and flips `DN`. Then repeat the Rapid
   Trigger hold and chatter check from the next section.
8. Replug (cold power cycle) and repeat step 7: the values must survive.

Repeat the full run at the 500 Hz and 1000 Hz scan-rate targets with
**Calibration Diagnostics** on and off (checklist item above).

Recovery if the baseline looks wrong: before Finish, turn ID 2 off; after a
bad save, **Erase DMK EEPROM and restart** (IDs 37 then 38,
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#reset-dmk-data-or-return-to-stock))
resets calibration, curve, settings, keymaps, macros and combos to defaults.
Record which recovery you used.

**Record.** `r`/`b` before and after for the watched keys, the status string
at each stage, all `[CAL]` lines, the mute duration, the 500/1000 Hz runs
with diagnostics on and off, and any scan-timing change with ID 19 on.

**Idle slow-scan (optional `HHKB_IDLE_SLOW_SCAN=1` image).** Behaviour from
the code (`keyboards/hhkb/config.h`, `modules/ec/idle_scan.h`,
`modules/ec/matrix.c`): after `HHKB_IDLE_TIMEOUT_S` (180 s) with no key
activity the matrix scans once per `HHKB_IDLE_SLOW_SCAN_PERIOD_MS` (50 ms,
about 20 Hz) instead of the configured rate. The first press ends slow mode
immediately and is reported from that scan, a held key keeps the full rate,
and calibration blocks slow mode. USB stays enumerated. By design a tap
shorter than the period can be missed, and the first press can be delayed by
up to one period.

1. Flash the idle image, turn on Polling Rate Diagnostics (ID 24) and idle
   190 s hands off: `[SCAN] actual=` must drop to about 20 Hz.
2. Transitions: the rate is unchanged before 180 s; after that it drops; one
   press and release brings the configured rate back on the next line; 180 s
   later it drops again; a 10 s hold keeps the full rate; starting
   calibration returns the full rate (check the status, ID 26).
3. First press after idle: 10 times, idle 190 s, then one normal press each
   time: 10/10 characters must arrive at the host.
4. Taps shorter than the period: at full rate (just after typing), tap one
   key 50 times as fast and lightly as you can and count characters; then
   idle 190 s and do one fast tap, repeated 30 times (30 idle periods; only
   the first tap of each counts) and count arrivals out of 30. Confirm
   full-rate behaviour returns after the first press. Report the hit rates;
   there is no target. The first-press delay needs an external time reference
   (for example a 240 fps camera on the key and a host clock); without one
   write "not measured" and do not estimate it from `evtest` timestamps.

**Record.** The rate transitions, the 10/10 count, the two tap hit rates, and
the camera result or "not measured".

## Rapid Trigger and key actions

- [ ] Hold a key bottomed out for 30 s with varying finger pressure; with Bottom dead zone 0.5 mm there should be no unintended up/down events. Repeat with the travel curve and after save/replug.
- [ ] Test shallow actuation and repeated partial release/repress on several switches.
- [ ] Verify OS shortcuts with right-hand modifiers, hold-tap modifiers, One-Shot and `MK(...)`.
- [ ] Hold the same key or layer through two assignments and release in both orders; confirm the host sees the surviving hold and the final release.
- [ ] `KC_GESC` with each of Alt/Ctrl/GUI/Shift toggle on and off, and the Ignore-modifier setting.

**Chatter check.** Set Rapid Trigger mode (ID 3) to Full board (2), or 7 keys
(1) when the keys under test are in that cluster (labels and ranges:
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#hhkb-settings-reference)),
RT press sensitivity (ID 4) and RT release sensitivity (ID 11) to 5 (0.5 mm),
and leave Bottom dead zone (ID 65) at its default 5 (0.5 mm) unless you are
deliberately testing something else. Read every value back and record it.
Capture raw events (`sudo evtest <event-kbd node> | tee <results
dir>/rt-chatter.txt`) and afterwards count release-to-repress gaps below
15 ms per key (the `chat.py` helper under
[Helper scripts](#helper-scripts) does this count).

For three keys (one alpha, one modifier, space): 500 deliberate short presses
each with varying finger pressure and shallow partial releases and re-presses
("rapid-trigger" style), then a 30 s bottomed-out hold per key with varying
finger pressure, then 2 minutes of normal typing. Repeat the bottomed-out
holds with the travel curve on and again after saving the settings and
replugging (checklist item above). A stuck key at any point is a failure:
record it and continue.

Chatter is a release followed by a re-press of the same key in under 15 ms.
Expect no up or down events during the 30 s bottomed-out holds and no stuck
keys. For the 500-press runs there is no chatter threshold recorded in this
repository: report your own press and chatter counts and the gap list as the
result, and do not adopt any number from outside this repository as a pass
mark.

**Record.** Presses and chatter counts, the gap list, the keys used, the
mode/sensitivities/dead zone in effect, the curve and save+replug repeats,
and the firmware commit.

## Power, suspend and current draw

- [ ] On USB power, confirm Power Saving Mode turns off LEDs and sensors with no host or when suspended, and scanning resumes on reconnect.
- [ ] Unplug USB: confirm the keyboard stops sending, enters STOP, and replugging USB resets and restores typing.
- [ ] Measure current in USB-active, power-saving and battery-STOP states (none is measured in this repository).

**Behaviour to expect** (from the code): Power Saving Mode is on by default
(ID 29). With it on and no USB host mounted or the bus suspended, the LEDs go
off, the sensor board powers down and scanning stops. A key press requests
USB remote wakeup only when power saving is off (`usb_enqueue_key_report`);
with power saving on the keyboard is not scanning, so keys do not wake the
host, by design. Remote wakeup is enabled in the descriptor
(`USB_REMOTE_WAKEUP_ENABLED 1`). Whether VIA traffic can wake the host is
host-side behaviour and unverified.

**Suspend sequence.** Run on USB power with the release image (the
diagnostics image adds `susp`, `pwrsave`, `sens_down` to `[STALL]`). Run each
of A (no autosuspend udev rule for the keyboard) and B (after the host's
autosuspend rule for it is applied and the keyboard replugged), recording the
keyboard's `power/control` and `power/autosuspend_delay_ms` from sysfs in
each case. For each of A and B:

1. Power saving on (ID 29 reads 1): typing works, LEDs as usual.
2. Suspend the host (`systemctl suspend`, on AC power) and wait 30 s. Expect
   the LEDs off and a suspended bus. "Scanning stopped" has no verified
   external indicator; LEDs off is the observable one.
3. Wake with the host's own keyboard or the lid. Record that the HHKB types
   again, the delay (stopwatch, seconds) and any stuck key.
4. Suspend again and wake by pressing a key on the HHKB: expect no wake (by
   design). Record the result.
5. Suspend again with VIA open from a second device if available; with a
   single host, mark "not testable". Alternative while awake: let the idle
   keyboard autosuspend (no rule) and check whether opening VIA brings it
   back (`dmesg -w`, `lsusb`); record the `dmesg` lines.
6. Power saving off (`set 29 0`), repeat step 4: a HHKB key press may now
   wake the host (remote wakeup is enabled in the descriptor; unverified on
   hardware). Set ID 29 back to 1 afterwards.
7. After every wake: type 1 minute, read the version string (ID 28), check
   for stuck keys, and note `dmesg` disconnect or reconnect lines.

For the current item there is no measurement procedure in this repository:
use a USB power meter in the three states and record the meter model, the
current and the conditions, or write "not measured".

**Record.** A and B results per step, `dmesg` excerpts, the autosuspend
settings, the current figures or "not measured", and any failure to return
after wake.

## Update, recovery and persistence

- [ ] Flash the patched `.hfb` through the PFU Bank 1 path (Python and browser flasher); confirm `cafe:4014` enumerates with VIA and the HID console.
- [ ] Exercise the three VIA debug scenarios with SW6 OFF: return to stock keeping EEPROM, erase nxmk EEPROM and restart, return to stock after erase.
- [ ] SW6 recovery alone and SW5+SW6 erase, with full backups; confirm stock operation afterwards and that factory EEPROM is unchanged.
- [ ] Interrupt power during a settings save on a disposable setup with SWD recovery; confirm a valid previous or new configuration returns.

**Baseline before flashing.** Plug in the keyboard and find out what is
running: `lsusb | grep -i -E '04fe|cafe'` and
`uv run --with hidapi python3 tools/hhkb/hhkb_flasher.py --info`.

- `04fe:...` with `--info` working: stock (or Bank 1) is running. Record the
  model and the version fields the flasher prints.
- `cafe:4014`: nxmk is already running (`--info` cannot see it). Record the
  version string (ID 28) and every control value on each VIA HHKB Settings
  page (IDs in
  [VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#hhkb-settings-reference))
  plus a screenshot per page. Calibration and settings live in EEPROM and
  survive a Bank 1 return, but note them anyway.

Save `lsusb -v -d cafe:4014` (or `04fe`) output into the results directory.

**Flash.** Build, patch and check the images as under
[Test images and session setup](#test-images-and-session-setup). The flasher
only sees the PFU interface (`04fe`): if nxmk is running, put the keyboard
into Bank 1 first, either the VIA route (SW6 OFF: **Arm reset / stock
recovery** ID 37, then **Return to stock Bank 1** ID 64,
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#reset-dmk-data-or-return-to-stock))
or the SW6 route ([Install](../../keyboards/hhkb/docs/en/install.md)). Both
routes erase the first 128-byte page of Bank 2, so the keyboard types nothing
until the next flash. Then run the Python or browser flasher as in
[Install](../../keyboards/hhkb/docs/en/install.md), for example:

```bash
uv run --with hidapi python3 tools/hhkb/hhkb_flasher.py keyboards/hhkb/local/nxmk_hybrid.hfb 2>&1 \
  | tee ~/hhkb-test/results/$(date +%F)/flash-release.log
```

Acceptance on top of the install steps: the flasher must report
`Container model: AHUX01; CRC check: passed; model check: passed`, finish
with `Transfer finished in <N>s.` and `Final command acknowledged; verify the
device after reboot.` If it says `No final acknowledgement` the result is
unconfirmed: continue with the checks below, do not reflash blindly. The
post-flash check waits only about 15 s before printing `Verified DMK device
(0xCAFE:0x4014)`; check `lsusb` for `cafe:4014` yourself before concluding.
End state: `cafe:4014` enumerates, VIA opens with `keyboards/hhkb/via.json`
loaded, the version string matches the build, typing works.

**STOP** if the keyboard does not enumerate as `cafe:4014` after 60 s: do not
power-cycle repeatedly; go to Rollback below.

**Smoke checks** (acceptance for the flash item):

| # | Action | Expect | Record |
| --- | --- | --- | --- |
| a | Type normal text for 2 minutes in a text editor | no dropped, doubled or stuck characters | error count |
| b | Press every key once (key-tester page or `evtest`), incl. Fn, modifiers, arrows | all 60 keys report once and each releases | missing/extra keys |
| c | Hold each modifier, then release | no key stays down after release | stuck key |
| d | Several 3-4 key chords | every key reported; no ghost keys | which chord ghosted |
| e | VIA: load `via.json`, open HHKB Settings | shows "nxmk HHKB Hybrid-S", `cafe:4014`; every control reads a value | screenshot |
| f | Read RT mode (3), sensitivities (4, 11) and the version string (28) | mode 0-2, sensitivities 1-45, version matches the build | values |
| g | Change one setting, wait for the Settings EEPROM label `Saved (compressed)`, replug | the setting persists | before/after |

Do not unplug while the EEPROM status is not `Saved (compressed)`
([VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#eeprom-storage)).

**Rollback and recovery** (only the routes in
[Install](../../keyboards/hhkb/docs/en/install.md),
[VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md) and
[Backup & restore](../../keyboards/hhkb/docs/en/backup-restore.md)):

- **Previous nxmk image:** into Bank 1 (VIA IDs 37 then 64 with SW6 OFF, or
  the SW6 route if VIA is unusable), then flash the earlier `.hfb` as above.
- **Stock firmware:** into Bank 1 the same way, then the official
  `HHKB800_FW_A048.hfb` with the Keymap Tool or the flasher ("Restoring
  stock" in backup-restore.md). The Keymap Tool cannot see running nxmk.
- **Reset settings only:** IDs 37 then 38 (**Erase DMK EEPROM and restart**):
  keeps the firmware, clears the nxmk settings.
- **The three VIA debug scenarios** (checklist item above, SW6 OFF): the two
  reset routes in via-debug.md and their sequence: return to stock keeping
  EEPROM, erase nxmk EEPROM and restart, and return to stock after an erase.
  Confirm which scenario ran and that the EEPROM content matches the
  documented outcome each time.
- **SW6 recovery alone and SW5+SW6 erase** (checklist item above): the DIP
  routes in backup-restore.md, with full backups at hand; afterwards confirm
  stock operation and that the factory EEPROM data is unchanged. The hardware
  procedures there are upstream-inherited and not re-verified.
- **VIA or keyboard dead, no Bank 1:** the DFU/SWD routes in
  backup-restore.md (the case must be opened, and DFU does not update the
  Bank 1 metadata). Stop and read that file first; use your own backup only.
- **Power cut during a settings save** (checklist item above): only on a
  disposable setup with SWD recovery ready; confirm that a valid previous or
  new configuration returns (writes are atomic snapshots, see
  [VIA & debug](../../keyboards/hhkb/docs/en/via-debug.md#eeprom-storage)).

**Record.** The flasher log and transfer seconds, the baseline capture, the
smoke results, the scenario or route used for every recovery step, its
outcome, and the final version string.

## Recording results

Save everything under a dated session directory (see
[Test images and session setup](#test-images-and-session-setup)), for example
`~/hhkb-test/results/<YYYY-MM-DD>/`:

- `flash-<image>.log` per image flashed
- `baseline.txt`: what ran before flashing, versions, settings, `lsusb`
- `rt-chatter.txt` and the chatter count output
- `calibration.txt`: console log, status strings, before/after `r`/`b`
- `stall-typing.txt`, `stall-idle.txt`, `idle-slowscan.txt`
- `suspend-A.txt`, `suspend-B.txt` with `dmesg` excerpts
- `summary.md`

In `summary.md`, per section: pass/fail/not run and every number its *Record*
text asks for, plus the context fields from the top of this checklist
(firmware commit, host OS and kernel, USB topology, VIA settings, measurement
equipment), the `sha256` of each image flashed, and anything that surprised
you. Never copy a result from another build or another session into the
summary as if it were measured here.

## Helper scripts

These two scripts were syntax-checked only and never run against hardware; if
one fails, do the step manually (the VIA web app replaces `via.py`, and the
chatter count can be done from the `evtest` log by hand). They are session
helpers, not part of the firmware or the host test suite.

`via.py` wraps the VIA channel (`uv run --with hidapi python3 via.py get ID`,
`via.py set ID VALUE`, `via.py str ID`):

```python
#!/usr/bin/env python3
"""Usage: via.py get ID | via.py set ID VALUE | via.py str ID   (VIA channel 0)"""
import sys
import hid

VID, PID = 0xCAFE, 0x4014

def open_via():
    for d in hid.enumerate(VID, PID):
        if d["usage_page"] == 0xFF60 and d["usage"] == 0x61:
            h = hid.device()
            h.open_path(d["path"])
            return h
    sys.exit("no cafe:4014 VIA interface found")

def xfer(h, op, vid, val=0):
    pkt = bytes([op, 0, vid, val]) + bytes(28)          # 32 bytes
    assert h.write(b"\x00" + pkt) == 33
    r = bytes(h.read(32, timeout_ms=2000))
    if len(r) != 32 or r[:3] != pkt[:3]:
        sys.exit(f"bad reply: {r[:8].hex(' ')}")
    return r

cmd, vid = sys.argv[1], int(sys.argv[2])
h = open_via()
if cmd == "get":
    print(xfer(h, 0x08, vid)[3])
elif cmd == "str":
    print(xfer(h, 0x08, vid)[3:].split(b"\0")[0].decode("ascii", "replace"))
elif cmd == "set":
    xfer(h, 0x07, vid, int(sys.argv[3]))
    print("ok")
```

`chat.py` counts presses and release-to-repress gaps below 15 ms per key from
`evtest` output:

```python
#!/usr/bin/env python3
"""Count presses and release->repress gaps < 15 ms per key from `evtest` output."""
import re, sys
rx = re.compile(r"time (\d+)\.(\d+), type 1 \(EV_KEY\), code (\d+) \((\w+)\), value ([01])")
rel, presses, chatter = {}, 0, 0
for line in sys.stdin:
    m = rx.search(line)
    if not m:
        continue
    t = int(m[1]) + int(m[2]) / 1e6
    code, val = m[4], m[5]
    if val == "1":
        presses += 1
        if code in rel and (t - rel[code]) * 1000 < 15:
            chatter += 1
            print(f"chatter {code}: {(t - rel[code]) * 1000:.1f} ms")
    else:
        rel[code] = t
print(f"presses={presses} chatter(<15ms)={chatter}")
```

## 2026-11-27

One session on the candidate image from branch `test/remote-wakeup`: commits
`b154d9f8` (upstream aroum/dmk `70b61f74` remote-wakeup cherry-pick,
conflicts resolved) and `4606470b` (build fix: GCC 15.2 arm-none-eabi `-flto`
ICE in IPA ICF when a weak `keyboard_usb_resume_cb` was called; replaced with
a registered function pointer `usb_set_keyboard_resume_cb`, behavior
unchanged). Image `~/hhkb-test/images/nxmk-wake-test.hfb`, sha256
`9d5d8420e13bf33926b3401dd00b46840fe3facc74bb173fec30a9f5c8936240`, 282672
bytes; `nxmk-wake-test.bin` sha256 `25b83a47`. Flashed 2026-11-27 with
`tools/hhkb/hhkb_flasher.py`, 165.08 s, device re-enumerated as `cafe:4014`,
VIA protocol 0x000C. Runtime identification: VIA custom value id 28 returns
"26.11.27-b154d9f"; USB serial `26.11.27-b154d9f`. The raw logs referenced
below live outside the repository (`/tmp/opencode/`, `~/hhkb-test/`), so
these results are provisional until those logs are committed.

### Remote wakeup / autosuspend: PASS

- Host Linux, USB `1-2`, autosuspend delay 2000 ms. 2026-11-27 19:50 wrote
  "auto" to `/sys/bus/usb/devices/1-2/power/control`.
- `runtime_status` timeline: suspended 19:50:27.428, active 19:50:33.016,
  suspended 19:50:40.627.
- The keypress landed 5.339 s into the capture window while the device was
  suspended: evdev code 30 (`KEY_A`) value 1 plus `MSC_SCAN` 458756 (scancode
  `0x1e`), release at 5.689 s; the character appeared on the host. Repeated
  presses at 6.190, 8.757 and 10.296 s all delivered while awake.
- No USB disconnect, reset or error in `dmesg` during the test window;
  `power/control` restored to "on" afterwards.
- Logs: `/tmp/opencode/wake.log` (evdev capture),
  `/tmp/opencode/rtstatus.log` (`runtime_status` samples). The repeated
  `hid-generic ... input1` lines in `dmesg` are the hidapi libusb backend
  detaching and the kernel re-probing usbhid on interface 1 on every
  VIA/console open, not a firmware defect.

### Full calibration on the same image: PARTIAL (capture defect)

Three complete passes (16 settle scans plus 16 counted baseline scans, then
the press phase) saved 44/60, 39/60 and 45/60 keys. Every pass ended with
status `Cal: unstable`. The rejected key set was different each pass (for
example pass 1: `2 9 - Z X V G H L . LCtrl LAlt Space RAlt`; pass 3:
`Esc Tab 1 2 3` plus `R0C3 R2C5 R2C6 R0C7 R1C5 R0C4 R1C7 R2C7 R1C2 R0C6`),
which rules out a key-specific reject and a press-pass error; the 14 keys
listed for pass 1 were typed successfully afterwards, so the matrix and
switches are healthy.

Mechanism (source review at `4606470b`): every counted scan accumulates per
cell, so "cell never sampled" is ruled out. The per-window cell gate in
`keyboards/hhkb/modules/ec/ec_settings.c` (around lines 1150-1157) rejects a
cell when `|mean(last8) - mean(first8)| > max(8, mean/64)` or
`max-min > 64` (`CAL_DRIFT_ABS`, `CAL_DRIFT_MEAN_DIV`, `CAL_SPREAD_MAX` are
unmeasured placeholders, as `docs/analysis/calibration-sag.md` notes). One
unstable cell restarts ALL cells in a fresh window, up to 8 windows; at the
cap the cells flagged in the final window are zeroed and `s_cal_unstable`
latches. A zero base makes `hhkb_cal_record_peak` return early
(`base < HHKB_CAL_BASE_MIN`), so that key can never be actuated for the rest
of the session, and finish rejects it, keeping the previously saved range.

Idle drift before any press falsely marked 3 to 12 keys as actuated because
the calibration press detector uses `base + RT_MIN_RANGE` (150 counts, about
6 percent of the 2370-count typical travel), while measured idle drift
reached +160. The finish gate (`peak >= base + 1185`) still refuses to save
those, so saved data is not corrupted: finish only overwrites
`s_cal_baseline` for accepted keys.

The sag fix is **not** validated on hardware. The sag-specific check (saved
base vs resting raw at +1 s and +60 s, 60/60) is still open, blocked by the
capture rejects. Unit test evidence stands: 83 tests green on the branch, and
the pre-fix tree fails the sag tests 3+1. Suggested fix direction (not
implemented): per-key retry that keeps stable cells instead of restarting the
whole window, count per-key instability across windows and zero only cells
unstable in several windows, calibrate the drift/spread gates from measured
per-key noise, and raise the calibration press threshold from `base+150` to a
travel fraction. Rich per-key logs from the first pass were lost when the
console listener truncated `/tmp/opencode/cal-step2.raw`; only
`/tmp/opencode/cal3.raw` (status plus unchanged list) remains.

### RT and actuation sweep: PASS

Same image (sha256 `9d5d8420...` above), 2026-11-27 evening. Method note:
values are 0.1 mm units on VIA channel 0 (0.4 mm = 4); RT press/release are
the `s_rt_cfg` values reached through `hhkb_rt_get`/`hhkb_rt_set`
(`keyboards/hhkb/modules/ec/ec_settings.c`).

| Setting | ID | Value | Result |
| --- | --- | --- | --- |
| RT scope | 3 | 1 (7 keys) | `W A S D Space LShift LAlt` |
| Global actuation point | 1 | 14 (1.4 mm) | kept at 1.4 mm, see below |
| RT press threshold | 4 | 13 (1.3 mm) | set at the user's direction ("even the rapid trigger keys, they should trigger at like 1.3mm") |
| RT release hysteresis | 11 | 4 (0.4 mm) | sweep below, left at 0.4 mm |
| Classic release hysteresis | 5 | 4 (0.4 mm) | unchanged |

The seven RT keys are `W A S D Space LShift LAlt` (`HHKB_RT_KEYS` in
`keyboards/hhkb/modules/ec/rt_keymask.h` with the LAYOUT mapping).

RT release hysteresis swept at RT press 1.3 mm: 0.5 mm clean, 0.4 mm clean,
0.3 mm produced chatter on quick taps of `W A S D` and `Space`. The floor is
0.4 mm; left at 0.4 mm (value 4).

Global actuation point: an initial mistake set it to 0.5 mm, which chattered
heavily on `l ; , m .` (a typed run of repeats). Restored to 1.4 mm (value
14) and the chatter stopped. Conclusion recorded: the global actuation point
stays at 1.4 mm, it is not part of the RT tuning, and short global actuation
is unusable.

Final saved config: actuation 1.4 mm, RT press 1.3 mm, RT release 0.4 mm, RT
on the 7 keys, classic hysteresis 0.4 mm. Settings are in EEPROM and survive
a flash as long as the settings region is not erased.

### Also open

- The claim that the keyboard kept typing during a calibration pass could not
  be reproduced or explained in source: the single key-event producer
  suppresses publication while `s_calibration_mode` is true
  (`keyboards/hhkb/modules/ec/matrix.c`, around lines 315-336) and the same
  flag gates peak recording in the same task iteration, so sustained typing
  during live `[CAL]` recording is a logical contradiction. Unconfirmed; not
  a documented defect.

### Second image, capture retry: calibration PARTIAL, runtime wake PASS, S3 wake FAIL (host EC storm)

Built from `test/remote-wakeup` `4606470b` plus the working-tree capture-retry
changes in `keyboards/hhkb/modules/ec/ec_settings.c` (per-key retry,
`CAL_UNSTABLE_LIMIT 3`, press gate at
`TOPRE_TYPICAL_TRAVEL_COUNTS/4`, release at /8; `CAL_SETTLE_SCANS 16` was
already in `4606470b`). Image `~/hhkb-test/images/nxmk-cal-retry.hfb`, sha256
`f122894667d6681d0602a6aeb81e93cb5aa3daf80279d41c6705ee5db763297c`; `.bin`
sha256 `3d33f2b78894ee3ab27d71026eb55be749a9bd523b9f18af2b9af2e86949b556`;
text 57468, data+bss 16488. Flashed 20:45 with the same flow as above (Bank 1
armed with VIA id 37=1 then 64=1, device `04fe:0021`, 165.07 s). Boot version
`26.11.27-4606470`, VIA protocol 0x000C.

Settings after the flash were retained: id 1 = 14, 2 = 1, 3 = 1, 4 = 13,
5 = 4, 11 = 4, 13 = 4, 29 = 1.

Calibration: two passes, 57/60 each. Pass 1 rejected A (R3 C3), 8 (R1 C11)
and Fn (R3 C13); pass 2 rejected Z (R0 C1), Option (R0 C3) and 1/! (R1 C3).
Rejects per pass fell from 14/18/21 on `9d5d8420` to 3, and the rejected set
differs per pass, so the residual is per-window noise, not key-specific.
Rejected keys keep the previously saved range and still type. 60/60 was not
reached; accepted for this image.

Runtime wake: PASS. With `power/control=auto` and `power/wakeup=enabled`,
`runtime_status=suspended`, three presses produced `KEY_Q` (16) at
21:06:46-47; the device returned to `suspended` with no re-enumeration.

S3 sleep with keyboard wake: PASS (21:34 run). Earlier attempts in this
session were read as instant spurious wakes; that reading was a logging
artifact and is retracted below.

Conditions: capture-retry image, `pm_debug_messages=1`, keyboard
`power/wakeup=enabled`, key events logged from `/dev/input/event2`
(`/tmp/opencode/evlog.py`), RTC alarm armed for +120 s as a fallback, all
other wake devices at their boot default (LID, SLPB, XHCI enabled).

- 21:34:33 `PM: suspend entry (deep)`.
- 21:34:58 `Timekeeping suspended for 23.526 seconds`, so the platform was in
  S3 for 23.5 s, not "about a second".
- `q` (KEY_Q, code 16) at 21:34:58.188 and `PM: suspend exit` at 21:34:59,
  with the RTC alarm still about 55 s away: the key press woke the host.

Correction for the earlier attempts (21:10:07, 21:11:57, 21:14:00): kernel
printk timestamps collapse across S3, so suspend and resume messages carry the
same resume second and journals cannot be read as "S3 left within a second".
The 21:14 attempt reports `Timekeeping suspended for 10.553 seconds`, so it
slept for 10.5 s and something woke it without a keyboard event; the EC GPE
(GPE16, `PNP0C09` `_GPE 0x16`) still fires 17 to 25/s, which is a candidate,
but it does not block sleep and no longer gates this validation.

Observation, not a defect claim: one `q` press at 21:34:58 produced five
repeated KEY_Q down reports (val=1, about 2 ms apart, 21:34:58.188 to
21:34:58.200) in the evdev log, matching the earlier triple-report seen at
21:06:46.

The first suspend request at 21:07:55 was refused silently because
`waybar-caffeine` held a block inhibitor; the user disabled Caffeine.
`pm_debug_messages` was set back to 0 after the diagnostic run.
