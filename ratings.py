"""ratings.py — pure metric→coach-rating logic. No I/O.

Turns a session's metrics into a coach-friendly good / ok / needs-work read across four
headline pillars — Speed, Stroke length, Consistency, Endurance. Each pillar carries:
  - band:  "good" | "ok" | "needs_work" | "unknown" (primary metric missing/NaN, or stroke
           has no validated thresholds)
  - score: 0–100 position of the primary metric within its band range — drives the meter
           marker. Higher ALWAYS = better (inverted for lower-is-better metrics). None when band
           is "unknown".
  - trend: "improved" | "steady" | "declined" vs a caller-supplied baseline, or "first_session"
           when there's nothing to compare to. Direction-aware, ±5% deadband.
  - provisional: True when the verdict can't be trusted as absolute (segmentation flagged
           unreliable, or the stroke has no validated bands).
  - primary + contributing metrics (value / unit / explanation) for the expand view.

One source of truth shared by api.py (GET /sessions/{id}/ratings), the web + iOS clients, and
coach.py. Explanation copy and RATING_COLORS live here so every surface agrees on wording AND
color. Bands are DRAFT — breaststroke only, seeded from app.py's Phase-2 ranges — and owe a coach
review before they're customer-facing (same posture as drills.py).

The trend baseline is chosen by `select_baseline()` and passed in; `rate_session()` doesn't care
how it was picked. That keeps the future "let the coach choose the comparison scope" feature a
caller-only change.
"""
import math

# Verdict colors — single source so clients never hard-code per-component (shipped Phase-2 trio).
RATING_COLORS = {"good": "#2d9e5f", "ok": "#d4860a", "needs_work": "#c0392b"}

# ±5% change vs baseline before a metric counts as improved/declined (reuses the compare convention).
TREND_DEADBAND = 0.05


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (
        isinstance(v, float) and math.isnan(v)
    )


def _round(v):
    if not _is_num(v):
        return None
    return round(v, 2) if isinstance(v, float) else v


# ── Pillars ───────────────────────────────────────────────────────────────────
# primary_key drives the band + score; `metrics` are contributing context shown on expand.
# direction: "higher" = bigger is better, "lower" = smaller is better (CV, fatigue).
# Kick metrics are deliberately absent (kick_metrics_reliable is always False).
PILLARS = [
    {
        "key": "speed", "label": "Speed",
        "primary_key": "mean_vel_ms", "primary_label": "Average speed", "primary_unit": "m/s",
        "direction": "higher",
        "explanation": "How fast the swimmer moved through the lap — average pace, top speed, and how little they slow between strokes.",
        "metrics": [
            {"key": "max_vel_ms", "label": "Top speed", "unit": "m/s",
             "explanation": "Fastest instant in the lap."},
            {"key": "mean_trough_vel_ms", "label": "Min between strokes", "unit": "m/s",
             "explanation": "Slowest point between strokes — higher means fewer dead spots."},
            {"key": "stroke_rate_spm", "label": "Tempo", "unit": "spm",
             "explanation": "Strokes per minute — context for the speed."},
        ],
    },
    {
        "key": "stroke_length", "label": "Stroke length",
        "primary_key": "mean_dps_m", "primary_label": "Distance per stroke", "primary_unit": "m",
        "direction": "higher",
        "explanation": "How far each stroke carries the swimmer — efficiency. Long strokes at a sustainable tempo beat short, choppy ones.",
        "metrics": [
            {"key": "mean_impulse_m", "label": "Impulse per stroke", "unit": "m",
             "explanation": "Distance gained during the drive of each stroke."},
            {"key": "stroke_rate_spm", "label": "Tempo", "unit": "spm",
             "explanation": "The length-vs-tempo trade-off — long strokes shouldn't come from just slowing down."},
            {"key": "mean_coast_fraction", "label": "Glide", "unit": "",
             "explanation": "Share of each stroke spent gliding vs driving forward."},
        ],
    },
    {
        # Band driven by arm-peak CV (the Phase-2 validated metric). Rhythm/ISI CV is shown as
        # context only — it has no validated threshold yet, so it gets no band of its own.
        "key": "consistency", "label": "Consistency",
        "primary_key": "cv_arm_peak_vel", "primary_label": "Power consistency", "primary_unit": "",
        "direction": "lower",
        "explanation": "How repeatable each stroke is — is the swimmer producing the same power and rhythm every cycle, or drifting?",
        "metrics": [
            {"key": "cv_isi", "label": "Rhythm consistency", "unit": "",
             "explanation": "Variation in time between strokes (lower = steadier rhythm). Shown for context — no validated band yet."},
        ],
    },
    {
        "key": "endurance", "label": "Endurance",
        "primary_key": "fatigue_index_pct", "primary_label": "Fatigue", "primary_unit": "%",
        "direction": "lower",
        "explanation": "Did the swimmer hold their speed across the swim or fade? Pacing and conditioning.",
        "metrics": [],
    },
]

# ── Thresholds + score anchors (DRAFT — breaststroke only; coach review owed) ──
# Per band-driver: worst_anchor → ok → good → best_anchor. Bands seeded from app.py:56
# _METRIC_RANGES (Phase 2). For "higher" metrics worst<ok<good<best; for "lower" metrics the
# value axis runs the other way (worst is the highest/worst value), best is the lowest.
THRESHOLDS = {
    "breaststroke": {
        "mean_vel_ms":      {"worst": 0.40, "ok": 0.80, "good": 1.20, "best": 1.80},
        "mean_dps_m":       {"worst": 0.50, "ok": 1.00, "good": 1.50, "best": 2.20},
        "cv_arm_peak_vel":  {"worst": 0.30, "ok": 0.20, "good": 0.10, "best": 0.03},
        "fatigue_index_pct": {"worst": 40.0, "ok": 20.0, "good": 8.0, "best": 0.0},
    },
}


def _band(value, thr, direction):
    if direction == "higher":
        if value >= thr["good"]:
            return "good"
        if value >= thr["ok"]:
            return "ok"
        return "needs_work"
    # lower is better
    if value <= thr["good"]:
        return "good"
    if value <= thr["ok"]:
        return "ok"
    return "needs_work"


def _score(value, thr, direction):
    """Piecewise-linear 0–100 so needs_work≈0–33, ok≈33–66, good≈66–100. Higher score = better
    for both directions; clamped to [0,100]."""
    pts = [(thr["worst"], 0.0), (thr["ok"], 33.0), (thr["good"], 66.0), (thr["best"], 100.0)]
    xs = [p[0] for p in pts]
    ascending = xs[0] < xs[-1]
    if ascending:
        if value <= xs[0]:
            return 0
        if value >= xs[-1]:
            return 100
    else:
        if value >= xs[0]:
            return 0
        if value <= xs[-1]:
            return 100
    for (x0, s0), (x1, s1) in zip(pts, pts[1:]):
        lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
        if lo <= value <= hi:
            if x1 == x0:
                return round(s1)
            return round(s0 + (value - x0) / (x1 - x0) * (s1 - s0))
    return round(pts[-1][1])


def _trend(value, baseline_value, direction):
    """Direction-aware change vs baseline with a ±TREND_DEADBAND deadband."""
    if not _is_num(value) or not _is_num(baseline_value):
        return "first_session"
    if baseline_value == 0:
        if value == 0:
            return "steady"
        pct = math.inf if value > 0 else -math.inf
    else:
        pct = (value - baseline_value) / abs(baseline_value)
    if abs(pct) < TREND_DEADBAND:
        return "steady"
    improved = pct > 0 if direction == "higher" else pct < 0
    return "improved" if improved else "declined"


def _rate_pillar(p, metrics, baseline, thr_table, seg_reliable):
    pk = p["primary_key"]
    pv = metrics.get(pk)
    thr = (thr_table or {}).get(pk)

    band, score = "unknown", None
    provisional = (not seg_reliable) or (thr_table is None) or (thr is None)
    if _is_num(pv) and thr is not None:
        band = _band(pv, thr, p["direction"])
        score = _score(pv, thr, p["direction"])

    bv = baseline.get(pk) if isinstance(baseline, dict) else None
    trend = _trend(pv, bv, p["direction"]) if baseline is not None else "first_session"

    contributing = []
    for c in p["metrics"]:
        cv = metrics.get(c["key"])
        if _is_num(cv):
            contributing.append({
                "key": c["key"], "label": c["label"], "value": _round(cv),
                "unit": c["unit"], "explanation": c["explanation"],
            })

    return {
        "key": p["key"], "label": p["label"],
        "band": band, "score": score, "trend": trend, "provisional": provisional,
        "explanation": p["explanation"],
        "primary": {"key": pk, "label": p["primary_label"],
                    "value": _round(pv), "unit": p["primary_unit"]},
        "metrics": contributing,
    }


def rate_session(session_metrics, baseline_metrics=None, stroke="breaststroke"):
    """Rate one session.

    session_metrics: flat dict of the session's metrics (metrics.py `session` keys) merged with
        the `data_quality` flags (so `segmentation_reliable` is visible here). Never client-supplied.
    baseline_metrics: the comparison session's flat metrics, or None for a first/only session.
        Chosen by select_baseline() — rate_session() is agnostic to how.
    stroke: lowercase stroke name. Only "breaststroke" has validated bands; other strokes get
        band="unknown"/score=None (trend-only) + provisional=True.
    """
    m = session_metrics or {}
    seg_reliable = bool(m.get("segmentation_reliable", False))
    thr_table = THRESHOLDS.get((stroke or "").lower())
    return {
        "stroke": stroke,
        "has_baseline": baseline_metrics is not None,
        "pillars": [_rate_pillar(p, m, baseline_metrics, thr_table, seg_reliable) for p in PILLARS],
        "rating_colors": dict(RATING_COLORS),
    }


def select_baseline(prior_sessions, mode="previous"):
    """Pick the baseline metrics dict from an athlete's earlier sessions.

    prior_sessions: list of flat metric dicts for sessions BEFORE the target, ordered newest-first.
    mode: "previous" (default — most recent prior session) | "first" (earliest) | "recent_avg"
        (per-metric mean across all priors). Modes beyond "previous" exist so a future
        coach-chosen comparison scope is a caller change only.
    Returns a metrics dict or None when there's no prior session.
    """
    if not prior_sessions:
        return None
    if mode == "previous":
        return prior_sessions[0]
    if mode == "first":
        return prior_sessions[-1]
    if mode == "recent_avg":
        agg, counts = {}, {}
        for s in prior_sessions:
            for k, v in (s or {}).items():
                if _is_num(v):
                    agg[k] = agg.get(k, 0.0) + v
                    counts[k] = counts.get(k, 0) + 1
        return {k: agg[k] / counts[k] for k in agg} or None
    raise ValueError(f"unknown baseline mode: {mode}")
