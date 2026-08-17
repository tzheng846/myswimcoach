# 65-01 FINDINGS — underwater breakout misdetection

**Measured 2026-08-16** via `tools/underwater_probe.py` (read-only, live DB). Corpus: **12 annotated
sessions — 8 butterfly, 4 freestyle, 0 backstroke** (backstroke has no annotations; n=0, as in Phase
59). ⚠ **The reported session "indigo ray" is NOT in the corpus** — see the gap below.

⚠ **This measurement partially REFUTES the assumed root cause.** The reported bug ("dive + dolphin
kicks segmented as stroke cycles") does not reproduce the way Phase 65's CONTEXT assumed. The real
picture is two distinct modes, and the discriminator hypotheses mostly fail.

## Per-session detector behaviour

| session | stroke | b_end | swim_window fires? | fallback ip | **final ip** | true breakout | **ip error** | cycles before breakout |
|---|---|---|---|---|---|---|---|---|
| 06fb64ad | fly | 6.3 | Y | 9.4 | 11.6 | 9.98 | **+1.67** | 0 |
| c0cdfc25 | fly | 1.3 | Y | 1.6 | 7.2 | 5.20 | **+2.02** | 0 |
| e166b8fe | fly | 0.9 | Y | 1.1 | 6.2 | 4.58 | **+1.58** | 0 |
| bc064b9d | fly | 0.8 | Y | 1.4 | 8.9 | 4.76 | **+4.11** | 0 |
| butterfly 4 | fly | 1.2 | Y | 1.4 | 7.5 | 6.27 | **+1.25** | 0 |
| butterfly 3 | fly | 1.2 | Y | 1.6 | 10.7 | 6.31 | **+4.40** | 0 |
| butterfly 2 | fly | 1.8 | Y | 3.5 | 7.3 | 4.87 | **+2.42** | 0 |
| butterfly 1 | fly | 0.0 | Y | 0.4 | 6.7 | 5.91 | **+0.82** | 0 |
| d25c578f | free | 2.2 | **N** | 5.2 | 5.2 | 6.48 | **−1.32** | **1** |
| 7dc0386a | free | 4.3 | Y | 4.9 | 10.5 | 8.33 | **+2.16** | 0 |
| edbcef83 | free | 0.8 | Y | 1.1 | 7.8 | 4.80 | **+3.00** | 0 |
| 4219daea | free | 9.3 | Y | 11.7 | 15.6 | 12.31 | **+3.25** | 0 |

(All fs ≈ 90 Hz.)

## Root cause — TWO modes, neither the assumed one

**Mode A — `detect_swim_window` FIRES (11/12): `ip_end` is ~2 s LATE, not early.** Median signed
error **+2.1 s**; 0 spurious pre-breakout cycles. This is the *known* 59-03 residual — the
frequency-settle rule (`_WINDOW_HOLD_CYCLES = 1.0`) waits ~1 cycle for rhythm to establish, so it
marks where stroking is *settled*, ~1–2 cycles after the coach's first-stroke mark. **It loses the
first stroke or two; it does NOT segment kicks as cycles.**

**Mode B — `detect_swim_window` returns `None` (1/12, freestyle d25c578f): the trough fallback lands
EARLY and produces a spurious cycle.** ip_end −1.32 s, **1 cycle before the breakout**. **THIS is the
reported failure mode** — and it comes from `detect_initial_phase`'s first-deep-trough rule
(`metrics.py:611`), reached only because `detect_swim_window` bailed (ridge failure or the
`_WINDOW_MIN_CYCLES = 4.0` plausibility gate). The dive + kicks live in the trough detector's search
window, so its first trough lands among them.

## The D8 2×-harmonic hypothesis is REFUTED (as measured)

| session | f_ref (steady, Hz) | underwater-span ridge (Hz) | uw / ref |
|---|---|---|---|
| fly (8 sessions) | 0.51–1.71 | 0.26–0.38 | 0.18–0.75 |
| free (4 sessions) | 0.91–1.21 | 0.31–0.42 | 0.31–0.38 |

D8 predicted the ridge locks **high** (≈2× the stroke rate) over the kicks, making `f_ref` the kick
rate. The opposite is observed: `f_ref` (0.5–1.7 Hz) is a **plausible stroke rate**, and the
underwater span rails **low** (~0.3 Hz) — the DP ridge-tracker's low-band floor over the aperiodic
dive transient, not a kick harmonic. ⚠ Caveat: this span includes the dive and (in Mode A) runs to a
late `final_ip`, so it is not a clean "kick-only" ridge measurement.

## Discriminating signals — amplitude fails, acceleration inconclusive

- **Mean |vel|**: underwater ≈ surface on every session (e.g. 1.25 vs 1.25; 0.88 vs 0.85). **Velocity
  amplitude cannot separate kicks from strokes** — confirms 59-03 ("fast but aperiodic"). A
  mean-velocity-drop detector is out.
- **Acceleration surge**: peak +accel underwater ≥ surface (freestyle ratio ~0.3, i.e. underwater
  *larger*). ⚠ **Confounded by the dive**: the underwater peak is the block-push transient, not the
  kicks, so this does NOT cleanly test "arm-pull surge vs kick." **Inconclusive** — a cleaner test
  must window out the dive (measure accel only over the kick span, which needs the breakout we are
  trying to find). Phase 66's smooth accel makes this test *possible*; it wasn't decisive here.
- **Frequency step-down** remains the only lever with theory behind it (59-03), but the ridge's
  low-band railing over the dive means the *front* of the window is unreliable — which is exactly
  where `ip_end` must be placed.

## ⭐ The reported session ("indigo ray", `6ececa0f`) — a THIRD mode, and it IS the bug

Measured 2026-08-16 via `--id` (it is a **generated display name, not a stored `sessions.name`**, so it
could only be reached by uuid — see the to-do below).

| session | stroke | b_end | win? | **f_ref** | **final ip** | cycles |
|---|---|---|---|---|---|---|
| 6ececa0f (indigo ray) | fly | 2.7 | **Y** | **0.33 Hz** | **2.7 (= b_end)** | **15** |

**Mode C — `detect_swim_window` FIRES but its `f_ref` RAILS LOW, collapsing `ip_end` to `b_end`.** The
CWT ridge railed to its low-frequency floor (~0.33 Hz — implausible for butterfly, real rate ~0.8–1.2
Hz) across the whole trace, so `f_ref` (back 60%) is ~3× too low. The frequency-settle rule then finds
"settled near 0.33 Hz" from the very start, so `ip_end` clamps to `b_end` (2.7 s) — segmentation runs
over the **dive + pulldown + underwater kicks**, producing **15 cycles** (inflated). ⭐ **THIS is the
reported "dive + kicks segmented as cycles" bug**, and its mechanism is a **broken `f_ref` inside
`detect_swim_window`** (the ridge's low-band rail) — NOT the trough fallback (Mode B) and NOT a 2×
harmonic (D8). The trough fallback here would have landed at 16.6 s — also wrong, so falling back is
not a fix.

## Recommendation: Option A — repair `detect_swim_window` (decisive)

"indigo ray" confirms the reported bug lives INSIDE `detect_swim_window`: a low-railed ridge makes
`f_ref` wrong, collapsing `ip_end` to `b_end`. The fix is a **frequency-robustness guard**, not a new
detector:
- Make `f_ref` / the ridge robust to the low-band rail — e.g. reject an implausibly-low `f_ref` (below
  a butterfly-plausible stroke-rate floor) and re-estimate, or constrain `_cwt_ridge`'s low-band bias
  so it tracks the stroke fundamental instead of railing to the floor.
- ⚠ Do NOT "fix" it by rejecting the window to the trough fallback — on indigo ray the fallback is
  16.6 s (worse). The repair must keep `detect_swim_window` producing a correct `ip_end`.
- The 2×-harmonic guard the CONTEXT anticipated (D8) is the wrong fix — the failure is the ridge
  railing LOW, not locking to a high harmonic.

**Option B (new arm-pull-surge detector) is NOT indicated:** the bug is a broken frequency estimate in
the existing detector; the accel/amplitude discriminators do not cleanly separate kicks from strokes
(amplitude refuted; accel dive-confounded). A new detector would not address the ridge rail.

Mode A's ~2 s late-settle (11/12) and Mode B's fallback-early (1/12) are separate, milder residuals;
65-02 should center on the Mode C ridge/`f_ref` robustness, then revisit the settle/fallback second.

## To-do surfaced (not this phase): persist generated session names

"indigo ray" could not be found by name because Phase 61-05 derives the mnemonic at render time and
never writes `sessions.name`. Recorded as a separate product to-do: **store the generated name into
`sessions.name` on creation, so it is stable and queryable, unless the user overwrites it.** Logged to
the ROADMAP.

---
*Phase 65-01 — measurement only, no product code touched. Input to 65-02.*
