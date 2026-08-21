# Phase Context

**Phase:** 76 — Breakout Detection (kick-band disappearance, free / back)
**Discussed:** 2026-08-20 (`/paul:discuss`) — a *why-it-works* discussion, not a scoping one
**Status:** Ready for `/paul:plan` — **but 76-01-PLAN.md already exists and this discussion CONFIRMS it.**
**Decision this session:** 1 (fly stays deferred). **Zero open blocking questions.**

⚠ **This CONTEXT is retroactive.** The plan (`76-01-PLAN.md`) was written first, off an already-run
validation (`tools/breakout_band_probe.py`, 33 annotated DB sessions). The user then asked *why* the
detector wins on freestyle and fails on butterfly. That question is answered here, and the answer
**upholds** the plan's freestyle-only scope + fly exclusion as principled, not a punt.

---

## The question

> *"The 7th lever works well for free but doesn't for fly. I'm curious why. I don't think it should
> matter — fly and free's waveform fundamentally differs from that of dolphin kick. Does CWT take
> advantage of waveform information? Also: are there more dolphin kicks in free than fly, causing it
> to perform better on free?"*

The "7th lever" = the user's own kick-band-disappearance hypothesis (6 prior levers failed: amplitude
/ mean-vel step / accel surge / 2× harmonic / rhythm step-down / first-deep-trough). Measured result:
**freestyle median |err| 2.07 → 0.30 s (11/16 within 0.5 s); butterfly 2.43 → 4.46 s, WORSE.**

---

## The answer (verified against the probe + 65-01)

**The detector is not a waveform detector — it is a one-band energy gate.** `detect_breakout_kickband`
takes `|CWT|²`, averages it across the **1.8–3.2 Hz** bins into a single scalar per timestep
(`_band_power`), and calls the breakout where that scalar collapses below `0.35 × run-peak` and holds.
The only information it acts on is *"how much ~2 Hz energy is here right now."* Everything about the
shape of the trace is discarded before the decision.

**Why free works / fly doesn't — one sentence:**

> **Butterfly is a dolphin kick with arms bolted on. Freestyle is arm strokes with the dolphin kick
> removed at the surface.**

| | underwater | surface | kick band at breakout | `Pk_uw/sf` |
|---|---|---|---|---|
| **free** | dolphin kick, ~2 Hz, in-band | arm strokes ~1 Hz (65-01 `f_ref` 0.91–1.21 Hz, **below** band) + low-amp flutter | **collapses** | **≫ 1** |
| **fly** | dolphin kick, ~2 Hz, in-band | undulation = **2 kicks per arm cycle** → ~2 Hz, **in-band**, same amplitude | **never drops** | **≈ 1** (scalogram-confirmed) |

The user's premise — *"the waveform fundamentally differs, so it shouldn't matter"* — is **right about
the waveforms and wrong about what the detector sees.** In the *one band* the detector reads,
fly-surface and dolphin-kick are identical. The detector already threw away the dimension that would
let the difference matter.

**Does CWT take advantage of waveform info? — As used here, NO.** (1) A Morlet CWT is a filterbank; a
scale reports ~*f*-Hz energy localized in time. Waveform *shape* lives in the phase relationships
between harmonics, and `|CWT|²` largely discards phase. (2) The detector then averages `|CWT|²` over
one band into a scalar — a time-localized band-pass energy meter, zero shape sensitivity. And even a
*full* scalogram wouldn't rescue fly: fly-surface and dolphin-kick aren't "same frequency, different
shape" — they are **nearly the same motion.** What's different at the fly breakout is that an **arm
pull is ADDED**, not that the kick changed. Fly is therefore an **appearance** problem, not a
**disappearance** problem → a fundamentally different detector.

**"More dolphin kicks in free?" — polarity is backwards.** It is not count, it is **contrast**. Both
strokes dolphin-kick underwater in comparable numbers (governed by the swimmer + 15 m rule, not the
surface stroke); if anything **fly has more total kick energy** because it never stops. The
discriminator is whether the band **switches off** at the surface — free yes, fly no.

**Honest caveat on the free win:** it is not "the band goes to zero." A 6-beat flutter puts some energy
near the top of the band; free survives only because flutter is **low-amplitude in the hip/COM velocity
the wheel measures**, so it drops under the `0.35×` line. The margin is **amplitude, not frequency** —
which is exactly why the 3 freestyle misses are "swimmer keeps dolphin-kicking past the breakout," and
why the refuse gate (`_KICK_MIN_RUN_S`, `_KICK_HOLD_S`) is load-bearing, not decoration.

---

## Decision

| # | Decision |
|---|---|
| **D1 — free-only, defer fly** (user, 2026-08-20). | Ship 76-01 as written: freestyle + backstroke (back n=0 → flagged unvalidated, 59-05 stance). Butterfly & breaststroke byte-identical, detector never called. Fly is NOT a tuning problem — it needs a different detector (below), so it is a separate future phase, not a widening of 76. |

This is the same conclusion `76-01-PLAN.md` already encodes (its D1). Nothing in the plan changes.

---

## Deferred — the fly breakout, when it comes (future phase, NOT scoped here)

Fly needs an **arm-pull-appearance** detector, not kick-disappearance. The signal is the arm pull
*added on top of* a continuing ~2 Hz undulation — a distinct, larger, lower-frequency propulsive surge.
Precedent already in the codebase: **Phase 59-05's `_learned_boundaries`** dropped the wavelet for
butterfly *segmentation* and used a logistic model over shape features `[v, dv, d²v, v−local_mean,
local_std]` for exactly this reason — the wavelet can't see the arm on top of the undulation. A fly
breakout detector would likely reuse that shape-feature approach against the 17 annotated fly sessions.
Recorded so it is not re-attempted as a band-power tweak.

---

## Not pursued this session (offered, user chose free-only)

- **Scope fly into 76 now** — declined; different detector, own measurement pass, bigger phase.
- **Pull per-session `Pk_uw/sf` distributions (free vs fly) before deciding** — not needed; the plan's
  single summary (`Pk_uw/sf ≈ 1` for fly) + the mechanism above were sufficient. The probe already
  prints that column (`breakout_band_probe.py:216,233`) if empirical confirmation is ever wanted.

---

## Success criteria

- [x] Mechanism understood and recorded: band-power gate (not waveform); fly retains the kick band
      because its surface stroke *is* dolphin kicking; free's kick band collapses (amplitude margin).
- [x] Fly-scope decision locked: free-only, fly deferred to a future arm-pull-appearance phase.
- [x] Existing `76-01-PLAN.md` confirmed consistent — no re-plan required.
- [ ] `/paul:plan` (or straight to approval): 76-01 is ready to APPLY as-is.
