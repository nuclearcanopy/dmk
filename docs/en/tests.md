# Hardware validation checklist

Planned physical checks for the HHKB Hybrid Type-S (ANSI). Every item is
unchecked: **no hardware result is recorded in this repository.** Any
measurement made outside the repo (for example by the maintainer) is not
reproduced here and must not be cited as a result until its log is committed.

Record the firmware commit, host OS, USB topology, VIA settings and
measurement equipment with each result. Host tests ([tests/README.md](../../tests/README.md))
cover encoding, state machines and bounds only; they do not establish wire
timing, latency or power.

## USB SOF scheduling

Compare builds with `HHKB_SOF_LOCK=0` and `HHKB_SOF_LOCK=1` (default) on the
same unit, with `HHKB_SCAN_DIAGNOSTICS` (default) and **Polling Rate
Diagnostics** on. The lock can also be toggled for the session in VIA under
Scan Rate. `HHKB_SOF_MARGIN_US` defaults to 150.

- [ ] Record `[LAT]` (`age_avg`, `age_max`, `lock`) with the lock on and off during typing.
- [ ] Capture USB SOF, keyboard IN transactions and scan timing with a USB analyzer or logic analyzer before interpreting `[LAT]` as end-to-end latency.
- [ ] At 1000 Hz, compare locked and unlocked delay, jitter and missed polls under idle, typing, repeated presses and chords.
- [ ] Check reacquisition after connect, SOF interruption and host resume, with no stuck keys.
- [ ] Compare direct USB, hubs/dock and at least two hosts.
- [ ] Switch VIA scan rates 50/125/250/500/1000 Hz while connected; check no drift or starved USB work.
- [ ] Test suspend/resume, replug and connecting with a key held.

## EC sampling and calibration

- [ ] Record `[SCAN]`/`[RATE]` at 1000 Hz with Rapid Trigger and the travel curve off/on; confirm `work_max` has headroom and `miss` stays 0.
- [ ] Measure row strobe, discharge and ADC acquisition timing with a logic analyzer or oscilloscope.
- [ ] Calibrate every key; confirm each can be captured and values survive Finish and a cold power cycle.
- [ ] Calibrate at 500 and 1000 Hz targets with **Calibration Diagnostics** on and off; VIA stays connected and normal input resumes without a stuck key.
- [ ] Repeat the resting test with **EC Matrix Diagnostics** on and record any change in scan timing.

## Rapid Trigger and key actions

- [ ] Hold a key bottomed out for 30 s with varying finger pressure; with Bottom dead zone 0.5 mm there should be no unintended up/down events. Repeat with the travel curve and after save/replug.
- [ ] Test shallow actuation and repeated partial release/repress on several switches.
- [ ] Verify OS shortcuts with right-hand modifiers, hold-tap modifiers, One-Shot and `MK(...)`.
- [ ] Hold the same key or layer through two assignments and release in both orders; confirm the host sees the surviving hold and the final release.
- [ ] `KC_GESC` with each of Alt/Ctrl/GUI/Shift toggle on and off, and the Ignore-modifier setting.

## Power and USB detection

- [ ] On USB power, confirm Power Saving Mode turns off LEDs and sensors with no host or when suspended, and scanning resumes on reconnect.
- [ ] Unplug USB: confirm the keyboard stops sending, enters STOP, and replugging USB resets and restores typing.
- [ ] Measure current in USB-active, power-saving and battery-STOP states (none is measured in this repository).

## Update, recovery and persistence

- [ ] Flash the patched `.hfb` through the PFU Bank 1 path (Python and browser flasher); confirm `cafe:4014` enumerates with VIA and the HID console.
- [ ] Exercise the three VIA debug scenarios with SW6 OFF: return to stock keeping EEPROM, erase nxmk EEPROM and restart, return to stock after erase.
- [ ] SW6 recovery alone and SW5+SW6 erase, with full backups; confirm stock operation afterwards and that factory EEPROM is unchanged.
- [ ] Interrupt power during a settings save on a disposable setup with SWD recovery; confirm a valid previous or new configuration returns.
