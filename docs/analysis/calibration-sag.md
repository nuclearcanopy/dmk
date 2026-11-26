# Calibration baseline sag (aroum/dmk#18)

Base `aa4f01b2`. Paths under `keyboards/hhkb/modules/` (`ec/` and `via_settings/`).
Symptom: after calibration the resting raw value sits 250–500 counts above the saved
baseline (example base 276 vs settled ~553), is saved, and is reloaded on restart.
Nothing below is hardware-confirmed. Claims are marked **code-supported** (the code
shows the mechanism) or **speculative** (needs a measurement).

## 1. How a baseline is sampled

- `hhkb_calibration_start()` (`ec/ec_settings.c:448-458`) zeroes `s_capture_base`, sets
  `s_cal_baseline_samples = CAL_BASELINE_SAMPLES` (16, `:20`), arms `s_capture_baseline`
  and `s_calibration_mode`. It is applied by the matrix task at a scan boundary
  (`ec/matrix.c:158`, `:236`; `ec_settings.c:387-391`) from a request posted by VIA IDs 7/8
  (`via_settings/hhkb_via_controls.c:139-144`).
- Every full scan while `capture` is true feeds **all** populated keys into a plain sum:
  `s_cal_samples` is filled per key (`ec/classic_matrix.c:309`), replayed after the scan
  (`:328-337`) into `hhkb_cal_accumulate_baseline` (`:103`; `ec_settings.c:803-805`,
  `s_capture_base += val`, a `uint16_t`; 16*4095 = 65520 cannot overflow).
- One scan = one sample. `hhkb_cal_decrement_samples()` (`ec_settings.c:838-852`) counts 16
  scans down, then does `s_capture_base /= 16` (a plain mean) and sets peak = base.
  Minimum sample count is 16 scans, no more, no less.
- A timed-out ADC read (`classic_matrix.c:41`, `:98-100`) restarts the whole capture
  (`:340`); that is the only quality gate on the samples.
- No scans are skipped or discarded: scan 1 after the request already counts. No
  min/max/variance/drift is kept. Scans that took place before start do not count.
- Peak: after capture, `hhkb_cal_record_peak` (`ec_settings.c:806-836`) keeps the max raw;
  a key counts as "calibrated" once raw >= base + `RT_MIN_RANGE` (150, `rapid_trigger.h:21`).
  The detection threshold uses the captured base, so a low base makes "pressed" easy.

## 2. When the sampled baseline is below the settled value

The mean of 16 samples equals the settled value only if the raw value is already settled and
its level does not depend on the calibration regime. Mechanisms in the code:

1. **Scan-period change at calibration start (code-supported mechanism).** While
   calibrating at 1 kHz (rate 4) the divider becomes 2, so scans run at 2 ms instead of
   1 ms (`ec/matrix.c:41`; the period is applied at `:199-207`, which runs *after* the
   scan that started calibration, so sample 1 is taken at 1 ms and samples 2–16 at 2 ms).
   `update_scan_period` also zeros the phase and moves CCR1 (`:42`, `:203`).
   The sensor chain is power-cycled every scan: OpAmp on at the start
   (`classic_matrix.c:232`), off at the end (`:325`), per-key discharge/settle of 4 µs and
   3 µs (`:290`, `:222`), ADC sample time 1.5 cycles (`:157`). Any time-constant in that chain
   makes the raw level a function of the scan interval, so a baseline measured at 2 ms is
   not the 1 ms resting level. After finish (`ec_settings.c:484`) the period flips back
   (`matrix.c:199-200`) and rest reads high against the saved base. This is deterministic,
   which matches 5/5. Whether the offset has this size is **not shown by the code**.
2. **No settle gate (code-supported).** The 16 averaged scans start at the request, with
   no discard window after start (`ec_settings.c:448-458`) or after the period change
   above. 16 scans = 16–32 ms. Anything that is still rising for ~30 ms (the period-change
   transient, USB-activity-coupled supply noise, sensor-board power restore after power
   saving at `matrix.c:187-197`, which has only a 10 ms wait) is averaged in as low values,
   and nothing detects it. An exponential rise 276→553 with tau = 6 scans gives a mean
   of 447 (see the test).
3. **Keys still being released (code-supported, low).** Keys that are down during capture
   *raise* the sum (raw rises with travel), so a held key biases the base **up**, not down.
   Not a sag source. Presses during capture are not detected at all (peak/press logic is
   skipped while `capture`, `classic_matrix.c:103-104`).
4. **Oversampling toggle (code-supported, low).** `scan_adc_prepare` (`classic_matrix.c:171-196`)
   enables oversampling only when requested **and** rate != 4 (`:173`). Calibration does
   not change the rate or the request, so calibration itself never toggles it. It toggles
   only on a VIA write of ID 18 or 13 (`hhkb_via_controls.c`) or on load. A toggle runs an
   ADC disable/enable (`:175-186`) and changes the sample averaging, so a toggle within
   or just before the capture window would shift the baseline. Relevant at rates other
   than 1 kHz only.
5. **ADC sample time (not a trigger).** `SMPR = 0` (1.5 cycles) is constant
   (`classic_matrix.c:157`) and never changes during calibration. It makes the reading
   sensitive to source impedance/settling but is not by itself a cause of a regime-dependent
   offset.
6. **EEPROM write during capture (speculative).** See §4.

## 3. What validation checks, and why a low base passes

Identical in two places:

- `hhkb_calibration_finish` (`ec_settings.c:465-476`): key must be "calibrated" (pressed past
  base+150), `base >= 20` (`HHKB_CAL_BASE_MIN`, `:45`), `base <= 2000`,
  `peak > base + RT_MIN_RANGE (150)`, `peak <= 4095`.
- the loader (`:338-339`): same `20 <= base <= 2000`, `peak > base + 150`, `peak <= 4095`;
  failing values are replaced with defaults (800 / base + 2370, `:131-140`).

Base 276, peak 553 satisfies every range (276 in [20,2000]; 553 > 426; 553 <= 4095), as
does any base from 20 up. The checks only bound the range; they are absolute and do not
compare the base against the factory/default 800 or against the previously saved value,
and nothing looks at how the samples moved. `rt_key_set_range` (`rapid_trigger.c:22-30`)
applies another floor (range < 150 → 1000) but not for a low base. A peak of only 553
means the key was not pressed through its travel (typical travel is about 2370 counts,
`ec_settings.c:19`), so the range check `peak > base+150` is satisfied by a *drifting
resting signal* alone: with a base 276 the "pressed" threshold is 426, which the settled
resting value (553) already exceeds. The press detector (`:809-814`) therefore latches
every key as "down" and "calibrated" at rest without any press. That is consistent with
`peak == settled value` in the report (peak 553 = resting level): the peak is the resting
level, not a real key travel.

## 4. 500 ms save delay vs calibration

- Every VIA setter calls `hhkb_settings_mark_dirty()` (`ec_settings.c:186-190`);
  `vial_keyboard_eeprom_task` (`:369-379`) saves once 500 ms (`:21`) have elapsed. Start
  (`:448-458`) does **not** mark dirty or hold off a pending save.
- A save that falls due while `s_calibration_mode` is set is deferred, not written:
  `:195-203` re-marks dirty (restarting the 500 ms timer) and returns. Saves during
  calibration are therefore safe, with no partial write.
- Finish rewrites the tables without a lock (`:462-480`) and clears `s_calibration_mode`
  *after* (`:484`) then marks dirty (`:486`). The save snapshot (`:221-241`) is under
  `taskENTER_CRITICAL`, so it sees all-old or all-new data. A torn table is only possible if
  the save task preempts the matrix task inside finish; the matrix task runs one level above
  the shared priority while waiting for the scan (`matrix.c:215-217`), when `apply_pending`
  at `:236` runs, so this cannot happen when `MATRIX_SCAN_PRIO != TASK_PRIO_MATRIX`.
- **Gap (code-supported):** the `s_calibration_mode` check is made once at the top
  (`:195`). A save already past that check (word loop `:251-266`, 1 ms `vTaskDelay` per changed
  word, so up to ~100+ ms) is not stopped when calibration starts. It writes a coherent
  *old* snapshot. EEPROM programming on the STM32L0 can stall flash fetches
  (**speculative**: only measurement can say how much the scan or 1 kHz timer ISR, which are
  in flash, are delayed); the scan loop itself is in `.RamFunc` (`classic_matrix.c:208`). That
  could delay or jitter 1–2 captured scans, not produce a 250–500 count offset. Ranked low.
- Nothing saves *mid-capture state*; only `finish` makes a baseline persistent.

## 5. Ranked hypotheses

| # | Hypothesis | Status | Confirming measurement |
|---|---|---|---|
| 1 | Raw resting level depends on scan interval; calibration runs at 2 ms (`matrix.c:41`) but normal operation at 1 ms, so the base is measured in a different regime | code-supported (mechanism), speculative (magnitude) | At 1 kHz, VIA 24 (`DEBUG_FLAG_RATE`) and 19 (`DEBUG_FLAG_TOPRE`) on; read `[EC] ... raw=` (`ec_settings.c:703`, every 20 ms, `classic_matrix.c:253-259`) at rest before start, during the capture window and after finish. Repeat at rate 3 (2 kHz? `period_us[3]=2000`, no divider change) and rate 2: the sag should be absent there. A level that jumps at the start/finish boundary confirms |
| 2 | Averaging includes a settle transient after start (no discard window) | code-supported, speculative | Same `[EC]` raw trace, or fire VIA 25 (`DEBUG_FLAG_CAL`) and compare the `base=` printed at the first press of each key (`ec_settings.c:822-824`) with `raw=` at rest 1 s later. A repeat with the keyboard idle for 2 s then start vs. start immediately after USB traffic separates settle from regime |
| 3 | Sensor-board/OpAmp power restore after sleep (10 ms wait only, `matrix.c:187-197`) or other analog warm-up | speculative | Start calibration immediately after USB resume, vs. 10 s after |
| 4 | Oversampling toggle/ADC re-enable within the capture window (`classic_matrix.c:171-196`) | speculative (low) | VIA 18 readback; does the sag disappear with oversampling off and rate 4? |
| 5 | Save in flight at start stalls flash fetch (`ec_settings.c:195-266`) | speculative (low) | Enable VIA 29? No: `DEBUG_FLAG_EEPROM` (0x20) logs `[EEPROM] settings saved`; correlate its timestamp with the start request. Skip the 500 ms wait before start: sag unchanged ⇒ rule out |

The first raw trace to take: record raw for one key at rest across `start → +100 ms → finish → +1 s`.
There is no direct raw-sample stream during capture other than `[EC] raw=` at 50 Hz (20 ms
gate, `classic_matrix.c:253-259`), which only shows 1 key at 1/10th the capture rate; a
debug hook that logs `s_capture_base/16` per key at CAL_LOG_BASELINE (`ec_settings.c:848-850`,
nothing is logged today) would be the direct measurement and is part of the proposed change.
Readback that confirms a calibration *engaged*: VIA ID 7/8 read back 0 always
(`hhkb_via_controls.c:139-140`), so use ID 26 (`:97-100`, `hhkb_get_cal_status_str`
`ec_settings.c:739-746`: "In progress: N/M keys" while the request is pending or
`s_calibration_mode`). ID 27 prints it to the console.

## 6. Proposed fix (not implemented)

(a) **Drift-aware capture + validation**, keeping the 16-scan average but adding per
key: `first8` and `last8` sums (scan index 0–7 and 8–15), plus `min`/`max`.
- Discard the first `CAL_SETTLE_SCANS` (proposed 16) scans after start and after any
  scan-period change; do not count them.
- At the end of capture reject (and extend, up to ~128 scans, then flag `Cal: unstable`)
  when any key satisfies `|mean(last8) - mean(first8)| > max(8, mean/64)` (≈ 1.5 % of
  full scale; 8 counts as a floor, to be tuned with the §5 trace) **or** `max - min > 64`.
  `finish` then must not commit those keys (clear their mask bit as for an invalid range,
  `ec_settings.c:473-476`).
- Do not "calibrate" a key unless a press reached `base + RT_MIN_RANGE` *and*
  `peak >= base + TOPRE_TYPICAL_TRAVEL_COUNTS/2` (≈1185) (§3); at rest 553 vs. 276 base
  currently counts as a press.
- Loader (`:338`): when `base` is below `default/2` (400) and `peak - base < 1185`, fall
  back to defaults, so an already-saved bad baseline from earlier firmware self-heals.
- Calibrate in the normal scan regime: remove the `rate == 4 && calibrating` divider
  (`matrix.c:41`) or, if the USB window is really needed, do the 16 capture scans at 1 ms
  and only slow down after `s_capture_baseline` clears (hypothesis 1).
- Hold off a pending save when a start request is posted: call `hhkb_settings_mark_dirty()`
  in `request_start` or re-check `s_calibration_mode` inside the word loop (`:251`).
- Log the captured base per key at `CAL_LOG_BASELINE`.

(b) **Test:** `tests/hhkb_classic/test_calibration_sag.py` extracts the real start / accumulate /
decrement / record-peak / finish functions from `ec_settings.c` and feeds synthetic
samples: key (0,0) rises 276→553 (tau 6 scans) across the 16-scan window, key (1,0) is
flat 553. Wanted: flat key committed as 553; the drifting key either rejected (old 800 kept)
or within 5 % of 553.
**Result on current code: fails.** Output: sampled baseline drifting key = 447 (settled
553), flat key = 553; committed baseline drifting key = 447. The assertion `base == 800 ||
base >= 525` fails. The control assertion passes, so the test fails only on the drift.
(Build with `cc`/`-lm`; the neighbouring `test_calibration_ranges.py` invokes `clang`,
absent on this host, and uses a `uint32_t` `s_capture_base` while the firmware uses
`uint16_t`.)

## Needs hardware

1. A raw trace at rest/start/finish (hypotheses 1–3), at rates 4 and 3 (are the two regimes
   different at all).
2. Drift size/noise floor per key to set the thresholds (8 counts, 1/64, 64 spread are
   placeholders).
3. Whether a flash write stalls the scan (hypothesis 5).
4. What the 276/553 *peak* represents (resting level vs. actual press): the `[CAL]` log at
   the first press prints peak/base (`ec_settings.c:822-824`).
