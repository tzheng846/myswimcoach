# Phase Context

**Phase:** 77 — Fly Breakout Detection (arm-cycle *appearance*, butterfly)
**Discussed:** 2026-08-20 (`/paul:discuss`)
**Status:** Ready for `/paul:plan`. **Zero blocking questions.** Two forks decided this session.
**Sibling of:** Phase 76 (free/back breakout). This is the fly counterpart 76's CONTEXT explicitly
predicted and deferred ("Fly needs an arm-pull-*appearance* detector, not kick-disappearance … a
separate future phase, NOT a widening of 76").

---

## Goal

Place the butterfly **Underwater→Swim breakout** (`ip_end` / `stroke_start_s`) accurately, integrated
at the **same seam** 76-01 uses (a per-stroke `ip_end` override in `compute_session_metrics`), and
**refusing** when the signal is weak — never shipping a confident wrong answer. Same discipline as
free/back; only the underlying signal differs.

The breakout is the biggest limiter on the race-phase model (it blanks underwater metrics and gates
the kick window). 76-01 fixed free/back; **butterfly is still on the incumbent** `detect_swim_window`
`ip_end` (median |err| **2.43 s** — the bar to beat).

## Why 76-01's detector can't be reused (the mechanism, measured in 76)

> **Butterfly is a dolphin kick with arms bolted on.**

`detect_breakout_kickband` (metrics.py:872) finds the breakout by watching the ~2 Hz dolphin-kick band
**switch OFF** at the surface. For fly it never switches off — the surface stroke **IS** two dolphin
kicks per arm cycle (~2 Hz, same band, `Pk_uw/sf ≈ 1`, scalogram-confirmed). Kick-disappearance
scored **4.46 s median |err|, WORSE than the 2.43 s incumbent** on 17 fly sessions. Fly is an
**appearance** problem (an arm pull is ADDED), not a **disappearance** problem → different detector.

## The signal (from the user's annotation cues)

User: *"when a human annotates it's obvious which waveform belongs to which phase — they differ in
number of peaks (fly includes two beat peaks), amplitude, and sometimes overall frequency."*

Read as **underwater phase vs surface phase within fly**, all three cues are **one** structural change:
**a ~1 Hz arm-cycle appears on top of the ~2 Hz kick that keeps running.**

| cue | underwater | surface fly |
|---|---|---|
| peaks / "two beat peaks" | uniform ~2 Hz kick train, equal peaks | ~2 Hz kicks **grouped 2-per-arm-cycle** → big-small-big-small |
| amplitude | — | arm pull adds a bigger, arm-coupled surge → amplitude **modulation** |
| "**sometimes**" frequency | pure ~2 Hz | a **~1 Hz arm-cycle** turns on *underneath* the persistent ~2 Hz |

The word **"sometimes"** is the tell: the dominant frequency does **not** cleanly halve (which is why
every ridge-frequency detector was blind), but the ~1 Hz **modulation** is present even when it
doesn't. So the robust question is *"is there sustained ~1 Hz structure yet?"* (appearance), not
*"did the frequency shift?"*

## ✅ MEASURED (2026-08-20) — hypothesis A, refined to a band RATIO, WINS

Measure-first was run this session (scratch probes → to be hardened into `tools/breakout_band_probe.py`
as plan task 1). Scored against the 16 annotated fly `stroke_start_s` marks:

| detector | median \|err\| | ≤1 s | notes |
|---|---|---|---|
| incumbent (`detect_swim_window`) | 2.67 s | 2/16 | today |
| raw arm-band appearance (0.7–1.3 Hz ON) | ~weak | — | only 1.45× uw→sf; **rejected** |
| **`P(0.8–1.1 Hz) / P(1.1–1.5 Hz)` rise** | **0.35 s** | **12/15** | **WINNER** |

**The signal is a spectral REORGANIZATION, confirmed by a per-frequency `P_surface/P_uw` fingerprint
(the ratio cancels the CWT 1/f bias; freestyle is the positive control — its kick bands drop 0.19–0.29×):**

| band | fly sf/uw | reading |
|---|---|---|
| 0.8–1.1 Hz (arm cycle) | **1.81×** (14/16) | APPEARS |
| 1.1–1.5 Hz (uw kick fundamental) | **0.52×** (5/16) | DROPS |
| 1.5–2.0 Hz (2-beat harmonic) | **2.04×** (15/16) | APPEARS |

At breakout the single underwater ~1.2 Hz kick line **splits** into an arm cycle (~0.9 Hz) + two kick
beats (~2 Hz) — literally the user's "two beat peaks." The **ratio** (arm ÷ fundamental) beats raw
appearance because it encodes the appearance AND the disappearance in one scale-invariant number.

**Robustness / honesty (all measured):**
- Band-edge jitter: a 4×4 grid (arm ∈ {0.75–1.05…0.8–1.2}, fund ∈ {1.0–1.4…1.1–1.6}) stays 0.35–0.99 s,
  **every cell beats the 2.67 s incumbent** → physical, not a knife-edge fit.
- Production path holds: swapping the annotated underwater-start for the auto `detect_underwater_start`
  (75-02, never before validated on fly) gives an **identical 0.35 s** — the seam works on fly.
- Tail: 2 short-underwater sessions miss (+4.1, +2.0 s), 1 correctly refused. Same weak-underwater class
  freestyle's refuse-gate handles; tightening `min_low_s`/`hold` should convert the 2 misses → refusals.

**Approach for the plan** (single physical feature; the learned model D is NOT needed):
1. Add `detect_breakout_fly` = the arm÷fundamental **ratio rise-after-sustained-low** detector (the
   rise-after-low structure skips the push-off transient), refusing when the ratio never cleanly steps.
2. **Principled band edges (robustness refinement, not a blocker):** the fundamental (1.1–1.5) and arm
   (0.8–1.1) bands are physically-plausible but this-swimmer-specific. Prefer deriving the fundamental
   from each session's own underwater spectrum (peak-pick the uw window), then arm ≈ f0/1.3 and
   harmonic ≈ 2·f0 — swimmer-invariant. Falls back to fixed bands if the uw peak is unreadable. The
   fixed-band grid already survives jitter, so this is hardening, not rescue.

**Why not the learned model (pushback the user accepted, now vindicated by measurement):** 76-01 earned
trust by measuring levers and shipping the cheapest that worked; 59-05's lesson is that a learned model
is the highest overfit risk on a tiny corpus. Fly has **16 sessions from ONE swimmer** — even
leave-one-out is leave-one-*session*-out, so *nothing here is validated across swimmers regardless of
method.* A single physical ratio hit 0.35 s; a classifier is unwarranted.

## Integration (mirrors 76-01 exactly — the seam already exists)

New `detect_breakout_fly(t, vel, uw_start_idx, swim_end_idx=None) -> int | None`. Butterfly sibling
branch at the metrics.py:1084 seam, **after** `detect_swim_window` sets `ip_end`, **before** the manual
override:

```python
if stroke_type == "butterfly" and swim_end > b_end:
    uw = detect_underwater_start(t, vel, b_end)      # 75-02, already there (metrics.py:736)
    if uw is not None:
        bk = detect_breakout_fly(t, vel, uw, swim_end)
        if bk is not None:
            ip_end = min(max(int(bk), b_end), swim_end - 1)
            initial_phase["initial_phase_end_idx"] = ip_end
```

Refuse (`None`) → keeps the incumbent `detect_swim_window` `ip_end`. Manual `ip_end_idx` still wins
(Phase 47). Additive: `annotations.py` / `phase_metrics.py` / `api.py` untouched; **free/back
(76-01) and breaststroke byte-identical**; `None`/unknown stroke never enters the branch.

## Decisions locked

| # | Decision |
|---|---|
| **D1 — New Phase 77, not folded into 76** (user, 2026-08-20). | As 76's CONTEXT intended. 76 stays closed as free/back-only. Needs a ROADMAP row (`/paul:add-phase 77`, or add at plan time). |
| **D2 — Measure-first; single physical feature (A/B) leads; learned model (D) is a measured fallback only.** | Honors 76-01's measure-a-lever ethos + 59-05's no-overfit rule. |
| **D3 — Butterfly ONLY.** | Free/back stay on 76-01's kick-band detector; breaststroke untouched; `None`/unknown → incumbent `detect_swim_window`. The new detector is never called for them. |
| **D4 — Refuse, don't guess.** | Weak/absent ~1 Hz structure → `None` → incumbent stands. Same asymmetry as `_WINDOW_MIN_CYCLES` and 76-01-D2: a false refuse costs only the improvement; a false positive ships a confident wrong window. |
| **D5 — Band is fixed + physical, not fit per session.** | Set arm-band edges from measured fly `f_ref` (65-01/65-02 machinery) + a robustness sweep; do NOT fit constants to individual sessions. |
| **D6 — Comparability break + backfill for stored fly sessions.** | Same standing pattern as 57 / 59-03 / 61-01 / 65 / 76-01-D5. Separate post-approval step, NOT a task here. |
| **D7 — 75-03 (fly kick metrics) depends on a correct fly `stroke_start`.** | The kick window is `[underwater_start, stroke_start]`; mirrors 76-01-D6 for free/back. Flag at 75-03 apply time. |

## Constraints / risks

- **17 fly sessions, one swimmer.** No cross-swimmer validation is possible; prefer the physical
  detector. `segmentation_reliable` stays hardcoded `False` regardless.
- **Amplitude polarity is unknown** — is this swimmer's underwater dolphin *faster* or *slower* than
  their surface fly? Measure it in the probe (`Pk_uw/sf` column already exists); don't assume a sign.
- **`detect_underwater_start` was validated on free/back**, not fly — confirm in the probe that its
  window START behaves on fly before relying on it as the search origin.
- **Human-verify checkpoint owed** on real DB fly traces (mirror 76-01's `--plot` eyeball gate).

## Open questions (for plan/measurement, non-blocking)

1. Exact arm-band edges (~0.7–1.3 Hz?) — set from measured `f_ref`, confirmed by the sweep, not hand-fit.
2. Does **A** alone separate, or is **A+B** needed? The probe decides before any detector is written.
3. Is the appearance signal cleaner in velocity, or in `|CWT|²` of the ~1 Hz band? (probe both.)

## Success criteria

- [x] Mechanism recorded: why 76-01 fails on fly (appearance, not disappearance).
- [x] Signal identified from the user's cues: the ~1.2 Hz uw kick fundamental splits into arm (~0.9 Hz) + 2-beat harmonic (~2 Hz).
- [x] Approach locked: measure-first, single physical feature (band ratio); learned model not needed.
- [x] Home locked: new Phase 77; integration seam identified (butterfly branch at metrics.py:1084).
- [x] **Hypothesis MEASURED and validated (2026-08-20):** `P(0.8–1.1)/P(1.1–1.5)` rise → **0.35 s median
      |err|** (incumbent ~2.4–2.7 s), 12/15 ≤1 s, robust to band jitter, holds on the auto uw-start.
- [ ] `/paul:plan` → 77-01-PLAN.md: harden the probe → `detect_breakout_fly` (ratio + refuse-gate,
      + per-session f0 band as robustness) → butterfly seam → human-verify on real DB traces.
