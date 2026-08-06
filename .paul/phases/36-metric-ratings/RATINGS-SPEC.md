# Coach-Friendly Metric Ratings — Shared Spec

The single contract every surface implements: backend (`ratings.py` + `GET /sessions/{id}/ratings`),
web (36-02), iOS (later phase), and the AI chat (`coach.py`). **Do not re-derive thresholds, colors,
or wording per client** — consume the payload.

Status: bands are **DRAFT** (breaststroke only, seeded from `app.py` Phase-2 ranges). Coach review
owed before customer-facing.

## The four pillars
Raw metrics roll up into four headline concepts coaches reason about. Each = one good/ok/needs-work
badge. Tempo, glide, start/underwater are contributing metrics or live in the advanced view.

| Pillar | Band driver (primary) | Direction | Contributing (expand) |
|--------|----------------------|-----------|------------------------|
| **Speed** | `mean_vel_ms` (Average speed) | higher better | `max_vel_ms`, `mean_trough_vel_ms`, `stroke_rate_spm` |
| **Stroke length** | `mean_dps_m` (Distance per stroke) | higher better | `mean_impulse_m`, `stroke_rate_spm`, `mean_coast_fraction` |
| **Consistency** | `cv_arm_peak_vel` (Power consistency) | lower better | `cv_isi` (rhythm — context only, no validated band) |
| **Endurance** | `fatigue_index_pct` (Fatigue) | lower better | — |

Kick metrics (`pct_cycles_with_kick`, `mean_arm_kick_ratio`, `mean_arm_kick_delay_s`) are excluded
(`kick_metrics_reliable` is always False).

## Verdict = hybrid (band + trend)
- **band** — `good | ok | needs_work | unknown`. Absolute, from `THRESHOLDS[stroke][primary]`.
  `unknown` when the primary metric is missing/NaN or the stroke has no validated thresholds.
- **score** — `0–100` continuous position of the primary within its band range; **higher always =
  better** (inverted for lower-is-better metrics). Drives the meter marker. `null` when band unknown.
  Piecewise-linear: needs_work ≈ 0–33, ok ≈ 33–66, good ≈ 66–100, clamped.
- **trend** — `improved | steady | declined | first_session` vs a baseline session. Direction-aware,
  ±5% deadband. `first_session` when there's no baseline (or the metric is missing in either).
- **provisional** — `true` when the verdict isn't trustworthy as absolute: `segmentation_reliable ==
  false` (always today → ship reading "provisional"; flips automatically once 16-06 validates) OR the
  stroke has no validated bands.

## Thresholds (DRAFT — breaststroke only)
`worst_anchor → ok → good → best_anchor`. Bands from `ok`/`good`; anchors define the score ramp.
| Metric | worst | ok | good | best |
|--------|-------|----|----|------|
| `mean_vel_ms` (higher) | 0.40 | 0.80 | 1.20 | 1.80 |
| `mean_dps_m` (higher) | 0.50 | 1.00 | 1.50 | 2.20 |
| `cv_arm_peak_vel` (lower) | 0.30 | 0.20 | 0.10 | 0.03 |
| `fatigue_index_pct` (lower) | 40 | 20 | 8 | 0 |

Non-breaststroke strokes have NO entry → all pillars `band=unknown`, `score=null`, `provisional=true`,
**trend still computed** (trend-only behavior until thresholds are validated).

## Trend baseline (pluggable)
`select_baseline(prior_sessions, mode="previous")` picks the comparison; `rate_session` is agnostic.
Modes: `"previous"` (default — most recent prior session) · `"first"` (earliest) · `"recent_avg"`
(per-metric mean across priors). A future "coach chooses comparison scope" feature = pass a different
`mode`, nothing else changes. Backend currently always uses `"previous"`.

## Payload (GET /sessions/{id}/ratings)
```json
{
  "stroke": "breaststroke",
  "has_baseline": true,
  "rating_colors": { "good": "#2d9e5f", "ok": "#d4860a", "needs_work": "#c0392b" },
  "pillars": [
    {
      "key": "speed", "label": "Speed",
      "band": "good", "score": 69, "trend": "improved", "provisional": true,
      "explanation": "How fast the swimmer moved through the lap …",
      "primary": { "key": "mean_vel_ms", "label": "Average speed", "value": 1.25, "unit": "m/s" },
      "metrics": [
        { "key": "max_vel_ms", "label": "Top speed", "value": 2.99, "unit": "m/s",
          "explanation": "Fastest instant in the lap." }
      ]
    }
  ]
}
```
Auth + ownership enforced before the body is built. Foreign/unknown session → 403/404; unauth → 401.

## Visual system (web 36-02 + iOS — match the approved mockup)
- **Fixed traffic-light band, identical on every card.** The meter always renders all three segments
  in the SAME colors regardless of score (no per-card desaturation): `needs_work` red `#c0392b` ·
  `ok` amber/yellow `#d4860a` · `good` green `#2d9e5f`. Source = `rating_colors` in the payload
  (= `ratings.RATING_COLORS`); never hard-code colors per component.
- **Marker** at `score`% along the band = "is this swim good" (absolute). **Trend chip** (↑ improved /
  → steady / ↓ declined, semantic-colored) = "is it improving" (relative). Two glances = the hybrid.
- **Card collapsed**: pillar name + band meter + verdict word (in band color) + trend chip. Numbers
  hidden. **Expanded (tap)**: explanation + contributing metrics (`primary` + `metrics`, value/unit).
- **Linear band**, not a dial — cleaner at 4-up and on mobile.
- **Verdict word** from `band`: good → "Good", ok → "OK", needs_work → "Needs work", unknown →
  hide the band / show "Not enough data".
- **Provisional**: show a small "Provisional" chip on the card group (or per card) when any pillar
  is provisional, so a coach knows the absolute read is tentative.
