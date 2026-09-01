"""
phase_metrics.py — race-phase metric registry + compute engine (Phase 75-01).

Pure module, no I/O (same convention as metrics.py / annotations.py / ratings.py).

Started (75-01) as the "define + provide space" skeleton: one MetricSpec per taxonomy
metric so every metric had a registry slot, key, unit, and effort tier, all
status="planned" with compute=None. Step 2 then filled them in batches — 75-02/75-03
underwater, 75-04 start, 75-06 swim + whole race. Every spec is now implemented except
streamline_drag; `breathing_dip` was removed rather than implemented (see REGISTRY).

The phase model (three phases, matching the existing annotation contract in
annotations.py): start (dive | push-off) -> underwater (dolphin kicks | breaststroke
pulldown) -> swim (strokes; the first stroke is the breakout, marked special but still
a stroke). "whole" is a fourth, cross-phase bucket for whole-race metrics.

api.py calls compute_phases(ctx) in two places: /process (fresh session, D-write) and
POST /sessions/{id}/recompute (rebuild from stored profiles, D16 backfill seam).
"""

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

# metrics.py is pure and does NOT import phase_metrics, so this is not a cycle.
import metrics

PHASES = ("start", "underwater", "swim", "whole")
TIERS = ("low", "medium", "high")
STATUSES = ("planned", "implemented")

SCHEMA_VERSION = 4  # 2 (75-02): added the resolved `boundaries` object.
                    # 3 (75-06): added the per-metric `provisional` flag (cycle-derived
                    # metrics computed off auto — not coach-annotated — stroke cycles).
                    # 4 (83-02): added `kick_bands` — per-downkick spans for the inset.

# Arithmetic-sanity floor for the underwater window: narrower than this and
# distance/duration ratios are numerical noise rather than a measurement. It is NOT a
# trust gate (75-02 P3) — a wide-but-wrong window is still computed and reported.
_MIN_UW_DURATION_S = 0.5

# Distance floor for splits_remainder (88-01 D3): a swim that crosses 20 m and stops within
# this many metres is arithmetically fine but physically meaningless — not sample-starved
# (~0.5 m at race speed is ~26 samples at 89.5 Hz), just too short a tail to mean anything.
# ⚠ MEASURED, not reasoned: D3 first picked 1.0 m on the premise that a 25-yard lap leaves
# ~1.9 m past the 20 m mark. It does not. finish_s clamps before the wall touch and dist_m
# already runs short of it (tether on the waist), so across the 56 stored sessions that reach
# 20 m the tail is MEDIAN 0.872 m (p25 0.486, p75 1.839) — 1.0 m sat above the median and filled
# only 23 of 56, failing the plan's own two-thirds stop condition. 0.5 m fills 42 of 56 and is
# about half a torso: below it the chord is measuring the touch itself, not a stretch of swimming.
_MIN_REMAINDER_M = 0.5


@dataclass(frozen=True)
class MetricSpec:
    """One registry entry. A 'planned' spec reserves the metric's key/phase/unit/tier
    with no compute function; an 'implemented' spec must supply one. compute(ctx) takes
    a PhaseContext and returns a raw numeric value (or None if not derivable for this
    session) — compute_phases() wraps the call so a raising compute fn degrades to None
    rather than failing the whole response.
    """
    key: str
    phase: str
    label: str
    unit: str
    tier: str
    status: str = "planned"
    compute: Optional[Callable[["PhaseContext"], float | None]] = None
    # True when the metric reads ctx.cycles — i.e. it inherits stroke-cycle segmentation
    # quality. compute_phases turns this into the emitted `provisional` flag whenever the
    # cycles came from the auto segmenter rather than a coach's annotation (75-06 D8).
    needs_cycles: bool = False

    def __post_init__(self):
        if self.phase not in PHASES:
            raise ValueError(f"{self.key}: unknown phase {self.phase!r}")
        if self.tier not in TIERS:
            raise ValueError(f"{self.key}: unknown tier {self.tier!r}")
        if self.status not in STATUSES:
            raise ValueError(f"{self.key}: unknown status {self.status!r}")
        if (self.status == "planned") != (self.compute is None):
            raise ValueError(
                f"{self.key}: status={self.status!r} requires "
                f"{'compute=None' if self.status == 'planned' else 'a compute function'}"
            )


@dataclass
class PhaseContext:
    """The stored signal Step-2 compute functions read — the compute-fn seam (D15).
    t/vel/dist/accel are 1-D numpy arrays at the session's own sample rate fs, aligned
    index-for-index (same convention as metrics.py). accel may be an empty array for
    sessions recorded before Phase 64 — a compute fn must handle that itself.
    go_signal_s is the reserved GO-button timestamp (D13); None until that feature
    ships, at which point reaction_time's compute fn reads it from here.

    Phase 75-02 adds the three inputs resolve_boundaries() needs, all optional so every
    pre-existing construction site keeps working:
      annotation_phases — the saved coach annotation's `phases` doc, or None
      seed_phases       — annotations.build_seed(metrics_json, fs)["phases"], or None
      initial_phase     — the session's metrics_json.initial_phase dict (pulldown, P7)
    `bounds` is not an input: compute_phases() fills it in with resolve_boundaries()'s
    result before any compute fn runs, so a compute fn reads ctx.bounds rather than
    re-resolving.
    """
    t: np.ndarray
    vel: np.ndarray
    dist: np.ndarray
    accel: np.ndarray
    fs: float
    stroke_type: str | None
    go_signal_s: float | None = None
    annotation_phases: dict | None = None
    seed_phases: dict | None = None
    initial_phase: dict | None = None
    bounds: dict | None = None
    # Phase 75-06: the session's per-stroke cycles (metrics_json.cycles) and whether they
    # are trustworthy. This is where "annotations first, auto fallback" lands for per-cycle
    # metrics — and it needs NO precedence code here, because PUT /annotations has already
    # overwritten metrics_json.cycles with compute_session_metrics(manual=...) output before
    # _rebuild_phases reads it. segmentation_reliable mirrors that same provenance
    # (metrics.py sets it to bool(manual_bounds)), so False == "these are auto cycles".
    # Both default to the safe reading: no cycles, not reliable.
    cycles: list | None = None
    segmentation_reliable: bool = False


# ─── Boundary resolution ─────────────────────────────────────────
# Every phase metric is window arithmetic over the same four boundaries, so they are
# resolved ONCE per session and hung on the context (ctx.bounds) rather than re-derived
# per metric. Precedence (75-02 P2): the coach's own annotation always wins; only where
# there is no human mark does a detector get a vote.

_BOUNDARY_KEYS = ("dive_start_s", "underwater_start_s", "stroke_start_s", "finish_s")


def _num(v):
    """v as a finite float, else None. Same coercion as annotations._num (bool is not
    a number here — a JSON true must not become 1.0 seconds)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if np.isfinite(f) else None


def _phase_val(doc, key):
    """Read one phase time out of an annotation/seed `phases` dict, tolerating None."""
    if not isinstance(doc, dict):
        return None
    return _num(doc.get(key))


def resolve_boundaries(ctx) -> dict:
    """Resolve the four race-phase boundaries for this session, recording where each
    one came from. Never raises — a key that cannot be resolved is None/"none".

    sources[key] is one of:
      "manual"   — the coach's saved annotation
      "auto"     — annotations.build_seed's derivation, used only as the fallback when the
                   detector below returns nothing (or, for dive_start, when no ≥X surge crosses)
      "detected" — a live detector run on this session's trace: detect_dive_start (dive_start),
                   detect_underwater_start (underwater_start), or detect_swim_boundaries
                   (stroke_start + finish — the rhythm-window + Phase 76/77 breakout answer)
      "none"     — not resolvable
    """
    ann, seed = ctx.annotation_phases, ctx.seed_phases
    bounds = {k: None for k in _BOUNDARY_KEYS}
    sources = {k: "none" for k in _BOUNDARY_KEYS}

    for key in ("dive_start_s", "stroke_start_s", "finish_s"):
        v = _phase_val(ann, key)
        if v is not None:
            bounds[key], sources[key] = v, "manual"
            continue
        v = _phase_val(seed, key)
        if v is not None:
            bounds[key], sources[key] = v, "auto"

    # Phase 79: where the coach has NOT marked dive_start_s, prefer the foot-of-surge
    # detector over the baseline_end seed. It anchors the race Start at the low point just
    # before the first ≥X m/s launch surge, skipping the jump-and-sink block artifact that
    # baseline_end trips on. On no ≥X surge, detect_dive_start returns None and the seed's
    # baseline_end value stands as "auto" — never worse than the old rule. Resolved BEFORE
    # underwater_start below, which seeds its search off dive_start_s.
    if sources["dive_start_s"] != "manual":
        try:
            idx = metrics.detect_dive_start(ctx.t, ctx.vel)
        except Exception:
            idx = None
        if idx is not None and ctx.fs and ctx.fs > 0:
            bounds["dive_start_s"] = float(idx) / float(ctx.fs)
            sources["dive_start_s"] = "detected"

    manual_uw = _phase_val(ann, "underwater_start_s")
    if manual_uw is not None:
        bounds["underwater_start_s"], sources["underwater_start_s"] = manual_uw, "manual"
    else:
        # ⚠ The SEED's underwater_start_s is deliberately not consulted. It is the
        # legacy dive-peak derivation (baseline_end_s + dive_duration_s) that 75-02
        # replaces — null on 84 of 108 sessions and ~1.5 s early where it fires. This
        # is not an oversight; do not "fix" it by adding a seed fallback here.
        dive_s = bounds["dive_start_s"]
        start_idx = 0
        if dive_s is not None and ctx.fs and ctx.fs > 0:
            start_idx = max(0, int(round(dive_s * ctx.fs)))
        try:
            idx = metrics.detect_underwater_start(ctx.t, ctx.vel, start_idx)
        except Exception:
            idx = None
        if idx is not None and ctx.fs and ctx.fs > 0:
            bounds["underwater_start_s"] = float(idx) / float(ctx.fs)
            sources["underwater_start_s"] = "detected"

    # stroke_start_s + finish_s from the newest swim-window/breakout detectors. build_seed's
    # stroke_start is the STALE stored initial_phase_end_idx (only the raw-CSV compute_session_
    # metrics path rewrites it), so on the auto path — backfill / recompute / process — prefer a
    # live run over the trace. Mirrors the dive_start (79) / underwater_start (75-02) pattern;
    # detection failure leaves the seed's "auto" value standing, and a coach annotation (resolved
    # above as "manual") always wins. Both boundaries come from one detect_swim_boundaries call.
    if (sources["stroke_start_s"] != "manual" or sources["finish_s"] != "manual") \
            and ctx.fs and ctx.fs > 0:
        try:
            ss_idx, fin_idx = metrics.detect_swim_boundaries(ctx.t, ctx.vel, ctx.stroke_type)
        except Exception:
            ss_idx = fin_idx = None
        if sources["stroke_start_s"] != "manual" and ss_idx is not None:
            bounds["stroke_start_s"] = float(ss_idx) / float(ctx.fs)
            sources["stroke_start_s"] = "detected"
        if sources["finish_s"] != "manual" and fin_idx is not None:
            bounds["finish_s"] = float(fin_idx) / float(ctx.fs)
            sources["finish_s"] = "detected"

    bounds["sources"] = sources
    return bounds


# ─── Compute functions ───────────────────────────────────────────
# One module-level _compute_<key> per implemented spec. Each returns a raw number or
# None; compute_phases() wraps the call, so raising is tolerated but returning None for
# "not derivable on this session" is the contract.


def _bounds(ctx):
    return ctx.bounds if isinstance(ctx.bounds, dict) else resolve_boundaries(ctx)


def _idx(ctx, time_s):
    """Sample index for a session-clock time, or None when it falls OUTSIDE the trace.

    Deliberately not clamped, unlike annotations.annotation_to_overrides: a boundary
    past the end of the stored profile means the window is not measurable, and AC-3
    requires None rather than a silently truncated number.
    """
    n = len(ctx.vel)
    if n == 0 or not ctx.fs or ctx.fs <= 0 or time_s is None:
        return None
    i = int(round(float(time_s) * float(ctx.fs)))
    return i if 0 <= i < n else None


def _window(ctx, start_s, end_s):
    """(i0, i1, duration_s) for a usable window, else None."""
    if start_s is None or end_s is None:
        return None
    duration = float(end_s) - float(start_s)
    if not np.isfinite(duration) or duration < _MIN_UW_DURATION_S:
        return None
    i0, i1 = _idx(ctx, start_s), _idx(ctx, end_s)
    if i0 is None or i1 is None or i1 <= i0:
        return None
    return i0, i1, duration


def _uw_window(ctx):
    b = _bounds(ctx)
    return _window(ctx, b.get("underwater_start_s"), b.get("stroke_start_s"))


def _span_distance(ctx, i0, i1):
    """Distance covered between two samples, or None if either is not a real number."""
    if len(ctx.dist) <= max(i0, i1):
        return None
    d = float(ctx.dist[i1]) - float(ctx.dist[i0])
    return d if np.isfinite(d) else None


def _compute_uw_duration(ctx):
    w = _uw_window(ctx)
    return None if w is None else w[2]


def _compute_uw_distance(ctx):
    w = _uw_window(ctx)
    return None if w is None else _span_distance(ctx, w[0], w[1])


def _compute_uw_avg_speed(ctx):
    w = _uw_window(ctx)
    if w is None:
        return None
    d = _span_distance(ctx, w[0], w[1])
    return None if d is None else d / w[2]


def _compute_uw_surface_ratio(ctx):
    """Underwater average speed ÷ surface average speed. Both sides are the same
    window arithmetic (Δdist / Δt), so the ratio compares like with like."""
    uw = _compute_uw_avg_speed(ctx)
    if uw is None:
        return None
    b = _bounds(ctx)
    finish_s = b.get("finish_s")
    if finish_s is None and ctx.fs and ctx.fs > 0 and len(ctx.vel):
        finish_s = (len(ctx.vel) - 1) / float(ctx.fs)   # fall back to the end of the trace
    w = _window(ctx, b.get("stroke_start_s"), finish_s)
    if w is None:
        return None
    d = _span_distance(ctx, w[0], w[1])
    if d is None:
        return None
    surface = d / w[2]
    if not np.isfinite(surface) or surface <= 0:
        return None
    return uw / surface


def _pulldown(ctx, key):
    """Pulldown fields, breaststroke ONLY (75-02 P7). detect_initial_phase computes them
    for every stroke, but the underwater content of a freestyle/butterfly race is dolphin
    kicks — emitting them there would be a mislabeled number."""
    if ctx.stroke_type != "breaststroke" or not isinstance(ctx.initial_phase, dict):
        return None
    return _num(ctx.initial_phase.get(key))


def _compute_pulldown_peak_vel(ctx):
    return _pulldown(ctx, "pulldown_peak_vel_ms")


def _compute_pulldown_duration(ctx):
    return _pulldown(ctx, "pulldown_duration_s")


# ─── Underwater kick metrics (Phase 75-03) ───────────────────────────────────
# All seven ride on ONE detector: metrics.detect_underwater_kicks peak-counts the
# underwater window. _kick_analysis runs it once and returns the shared peak data; each
# metric is arithmetic on that, guarded by a per-metric count floor. Gated to the
# dolphin-kick strokes — breaststroke's underwater is the pulldown (see _pulldown).


def _kick_analysis(ctx):
    """Shared per-session kick data, or None when kicks do not apply to this session.

    None when: the stroke is breaststroke (its underwater is the pulldown), or the
    underwater window is unusable (_uw_window). Otherwise returns the detected downkick
    peaks (possibly an EMPTY array — a glide-only underwater), their velocities, the
    inter-kick intervals, the window bounds, and the window distance. Each _compute_kick_*
    applies its own count floor to this.
    """
    if ctx.stroke_type == "breaststroke":
        return None
    w = _uw_window(ctx)
    if w is None:
        return None
    i0, i1, _dur = w
    peaks = metrics.detect_underwater_kicks(ctx.t, ctx.vel, i0, i1)
    if peaks is None:
        peaks = np.array([], dtype=int)
    peak_vels = ctx.vel[peaks] if len(peaks) else np.array([])
    intervals = np.diff(ctx.t[peaks]) if len(peaks) >= 2 else np.array([])
    return {
        "peaks": peaks,
        "peak_vels": peak_vels,
        "intervals_s": intervals,
        "i0": i0,
        "i1": i1,
        "uw_dist": _span_distance(ctx, i0, i1),
    }


def _kick_bands(ctx):
    """Drawable per-downkick spans for the report card's Underwater inset (Phase 83-02).

    Session data, not a registry metric — it rides beside `boundaries` for the same reason
    that does: raw resolved segmentation, not a {value, unit, label, tier, status} envelope.

    It lives INSIDE `phases` rather than at the top of metrics_json (83-02 D5 reversed) so
    that all three write paths get it from one change: POST /process, `_rebuild_phases` and
    tools/backfill_phases.py each store compute_phases' return verbatim under the `phases`
    key alone. That also makes it impossible to go stale — PUT /annotations calls
    `_rebuild_phases` last, so the bands are re-derived against the coach's manual window
    instead of being carried forward against the one it replaced.

    [] for breaststroke (its underwater is the pulldown), for an unusable window, and for
    fewer than 2 detected kicks. Never raises.
    """
    try:
        a = _kick_analysis(ctx)
        if a is None:
            return []
        return metrics.segment_kick_bands(ctx.vel, a["peaks"], a["i0"], a["i1"], ctx.fs)
    except Exception:
        # compute_phases guards every SPEC, but this call sits in its header dict, outside
        # that loop — so the guard has to live here or the whole response could fail.
        return []


def _compute_kick_count(ctx):
    a = _kick_analysis(ctx)
    return None if a is None else int(len(a["peaks"]))


def _compute_kick_tempo(ctx):
    """Kicks per second, from the MEDIAN inter-kick interval — glide-independent (a pre-kick
    glide inside the window cannot dilute it the way count ÷ window-duration would)."""
    a = _kick_analysis(ctx)
    if a is None or len(a["intervals_s"]) < 1:
        return None
    med = float(np.median(a["intervals_s"]))
    return None if med <= 0 else 1.0 / med


def _compute_kick_consistency(ctx):
    """CV of the inter-kick intervals (std ÷ mean); lower = more even. Needs ≥2 intervals."""
    a = _kick_analysis(ctx)
    if a is None or len(a["intervals_s"]) < 2:
        return None
    iv = a["intervals_s"]
    mean = float(np.mean(iv))
    return None if mean <= 0 else float(np.std(iv) / mean)


def _compute_dist_per_kick(ctx):
    """Total underwater distance ÷ kick count (D-dpk: the whole window, not a glide-excluded
    sub-window — a long push-off glide inflates it; documented, not corrected)."""
    a = _kick_analysis(ctx)
    if a is None or len(a["peaks"]) < 1 or a["uw_dist"] is None:
        return None
    return float(a["uw_dist"]) / len(a["peaks"])


def _compute_per_kick_decay(ctx):
    """Signed % change in downkick-peak velocity, first kick → last. Negative = the kicks
    are dying across the underwater; positive = building. Needs ≥2 kicks."""
    a = _kick_analysis(ctx)
    if a is None or len(a["peak_vels"]) < 2:
        return None
    first, last = float(a["peak_vels"][0]), float(a["peak_vels"][-1])
    if not np.isfinite(first) or not np.isfinite(last) or first == 0:
        return None
    return (last - first) / first * 100.0


def _compute_first_kick_impulse(ctx):
    """Velocity gained across the first downkick: the first peak minus the lowest velocity
    between the window start and that peak (the trough it accelerated from). Unit m/s — a
    Δv, not an integral."""
    a = _kick_analysis(ctx)
    if a is None or len(a["peaks"]) < 1:
        return None
    p0 = int(a["peaks"][0])
    pre = ctx.vel[a["i0"]: p0 + 1]
    pre = pre[np.isfinite(pre)]
    v_peak = float(a["peak_vels"][0])
    if len(pre) == 0 or not np.isfinite(v_peak):
        return None
    return v_peak - float(np.min(pre))


def _compute_uw_ivv(ctx):
    """Intra-underwater velocity variation = std ÷ mean of velocity over the window
    (D-ivv). Detector-INDEPENDENT — needs only the window, so it computes even where the
    kick peaks are unreliable. Gated to non-breaststroke, like the rest of the kick group."""
    if ctx.stroke_type == "breaststroke":
        return None
    w = _uw_window(ctx)
    if w is None:
        return None
    i0, i1, _dur = w
    seg = ctx.vel[i0:i1]
    seg = seg[np.isfinite(seg)]
    if len(seg) < 2:
        return None
    mean = float(np.mean(seg))
    if not np.isfinite(mean) or mean == 0:
        return None
    return float(np.std(seg) / mean)


# ─── Start metrics (Phase 75-04) ──────────────────────────────────────────────
# The Start phase runs [dive_start_s, underwater_start_s]; both boundaries resolve on
# ctx.bounds (dive_start = Phase 79 foot-of-surge, underwater_start = 75-02 first dip).
# Physically the window is foot → propulsive surge → PEAK → passive glide → bottom (kicking
# begins), so every Start metric is a reduction over that window or its glide sub-slice
# [peak, underwater_start]. Same degrade-to-None-never-raise contract as the underwater group.
# 10 of 11 implemented here; streamline_drag (a nonlinear drag-decay fit, confounded by the
# tether) stays planned.


def _start_window(ctx):
    b = _bounds(ctx)
    return _window(ctx, b.get("dive_start_s"), b.get("underwater_start_s"))


def _start_peak(ctx):
    """(peak_idx, peak_vel) over the start window — the launch crest. None when the window is
    unusable or its slice is all-NaN. nan-safe: stored profiles can carry dropout nulls."""
    w = _start_window(ctx)
    if w is None:
        return None
    i0, i1, _dur = w
    seg = ctx.vel[i0:i1]
    if not np.any(np.isfinite(seg)):
        return None
    off = int(np.nanargmax(seg))
    return i0 + off, float(seg[off])


def _glide_window(ctx):
    """(peak_idx, uw_start_idx, dur) for the passive glide — velocity PEAK to underwater_start.
    Deliberately NO _MIN_UW_DURATION_S floor (unlike _window): a short glide (the swimmer kicks
    almost immediately) is real signal, not numerical noise. None unless underwater_start lands
    after the peak with a positive duration."""
    p = _start_peak(ctx)
    if p is None:
        return None
    peak_idx = p[0]
    uw_idx = _idx(ctx, _bounds(ctx).get("underwater_start_s"))
    if uw_idx is None or uw_idx <= peak_idx:
        return None
    dur = float(ctx.t[uw_idx]) - float(ctx.t[peak_idx])
    if not np.isfinite(dur) or dur <= 0:
        return None
    return peak_idx, uw_idx, dur


def _compute_peak_vel(ctx):
    p = _start_peak(ctx)
    return None if p is None else p[1]


def _compute_time_to_peak_vel(ctx):
    """Time from dive_start to the velocity peak — explosiveness. None if the peak precedes
    dive_start or the boundary is missing."""
    p = _start_peak(ctx)
    if p is None:
        return None
    ds = _bounds(ctx).get("dive_start_s")
    if ds is None:
        return None
    val = float(ctx.t[p[0]]) - float(ds)
    return val if np.isfinite(val) and val >= 0 else None


def _compute_max_accel(ctx):
    """Peak acceleration off block/wall over the start window. None when the window is unusable
    OR ctx.accel is empty (pre-Phase-64 sessions carry no acceleration_profile)."""
    if len(ctx.accel) == 0:
        return None
    w = _start_window(ctx)
    if w is None:
        return None
    i0, i1, _dur = w
    if len(ctx.accel) <= i0:
        return None
    seg = ctx.accel[i0:min(i1, len(ctx.accel))]
    seg = seg[np.isfinite(seg)]
    if len(seg) == 0:
        return None
    return float(np.max(seg))


def _compute_dive_duration(ctx):
    """Length of the Start phase (dive_start → underwater_start). Push-off or dive — the window
    is the same either way; start-type classification is out of scope."""
    w = _start_window(ctx)
    return None if w is None else w[2]


def _compute_glide_duration(ctx):
    w = _glide_window(ctx)
    return None if w is None else w[2]


def _compute_glide_distance(ctx):
    w = _glide_window(ctx)
    return None if w is None else _span_distance(ctx, w[0], w[1])


def _compute_glide_avg_speed(ctx):
    w = _glide_window(ctx)
    if w is None:
        return None
    d = _span_distance(ctx, w[0], w[1])
    return None if d is None else d / w[2]


def _compute_glide_decel(ctx):
    """Speed-loss RATE across the glide: (v_peak − v_at_underwater_start) / glide_duration, m/s².
    Positive = decelerating in streamline (the normal case). Linear — the nonlinear drag-model fit
    is streamline_drag (deferred)."""
    w = _glide_window(ctx)
    if w is None:
        return None
    i0, i1, dur = w
    v0, v1 = float(ctx.vel[i0]), float(ctx.vel[i1])
    if not (np.isfinite(v0) and np.isfinite(v1)):
        return None
    return (v0 - v1) / dur


def _compute_break_into_kick_vel(ctx):
    """Velocity at the instant underwater kicking begins (= underwater_start_s, the bottom of the
    glide). Glided too long → low; too short → high."""
    idx = _idx(ctx, _bounds(ctx).get("underwater_start_s"))
    if idx is None:
        return None
    v = float(ctx.vel[idx])
    return v if np.isfinite(v) else None


def _compute_reaction_time(ctx):
    """GO signal → first encoder movement. None until a GO time is supplied (ctx.go_signal_s, set
    via PUT /sessions/{id}/go-signal). First movement = motion onset from detect_phases (the jump
    off the block), NOT dive_start — Phase 79 deliberately skips the jump-and-sink, which would
    undercount reaction time. Both times are on the session clock. Negative (GO logged after the
    swimmer moved) → None: a bad input, not a measurement."""
    go = _num(ctx.go_signal_s)
    if go is None:
        return None
    try:
        onset = metrics.detect_phases(ctx.t, ctx.vel)["baseline_end"]
    except Exception:
        return None
    if onset is None or onset < 0 or onset >= len(ctx.t):
        return None
    rt = float(ctx.t[onset]) - go
    return rt if np.isfinite(rt) and rt >= 0 else None


# ─── Swim metrics (Phase 75-06) ───────────────────────────────────────────────
# The Swim phase runs [stroke_start_s, finish_s] — breakout to touch. Two reliability
# layers live here and must not be confused (75-06-DISCOVERY):
#   Layer A — window arithmetic over ctx.bounds. As trustworthy as the boundaries, which
#             75-03/76/77/79 measured. Most of this group.
#   Layer B — per-CYCLE reductions over ctx.cycles. These inherit stroke-cycle segmentation
#             quality, which is unmeasured on the auto path (Phase 80: freestyle hits the
#             exact cycle count on 6/21 sessions). They carry needs_cycles=True so
#             compute_phases can flag them provisional; the coach's annotated cycles arrive
#             on ctx.cycles automatically when one exists.
# ⚠ finish_s is the weakest boundary in the model (MAE 2.76 s, worst 6.43 s — Phase 78).
# Anything averaging to the end of the window trims its tail rather than trusting it.

# Velocity right at breakout is a single noisy sample, so it is averaged over a short span.
_BREAKOUT_WINDOW_S = 0.5
# How far past breakout to look for the speed trough the swimmer falls into before the
# stroke rhythm establishes — roughly one slow stroke cycle.
_BREAKOUT_LOSS_WINDOW_S = 2.0
# Fraction of the swim window dropped from the END before taking a "steady state" mean.
# This is the finish_s mitigation: an untrimmed tail drags the denominator toward whatever
# the weak finish detector included (a wall touch, a glide-out, dead trace).
_STEADY_TRIM_FRAC = 0.15
# Cumulative distances (m from dive_start) at which a split velocity is reported. Each split
# is the mean velocity of the PRECEDING 5 m segment.
_SPLIT_DISTANCES_M = (5, 10, 15, 20, 25)
# Correlating two 2-point series is meaningless; below this many cycles, coupling is None.
_MIN_COUPLING_CYCLES = 3


def _finish_s(ctx):
    """finish_s, falling back to the end of the stored trace when the boundary is missing.
    Mirrors the fallback _compute_uw_surface_ratio already uses: a session whose finish never
    resolved still has a measurable swim, and reporting nothing is worse than reporting to
    the end of what was recorded."""
    b = _bounds(ctx)
    fin = b.get("finish_s")
    if fin is not None:
        return fin
    if ctx.fs and ctx.fs > 0 and len(ctx.vel):
        return (len(ctx.vel) - 1) / float(ctx.fs)
    return None


def _swim_window(ctx):
    return _window(ctx, _bounds(ctx).get("stroke_start_s"), _finish_s(ctx))


def _finite_slice(arr, i0, i1):
    """arr[i0:i1] with non-finite samples dropped. Stored profiles carry dropout nulls, so
    every reduction in this module goes through here rather than trusting the raw slice."""
    if len(arr) <= i0:
        return np.array([])
    seg = np.asarray(arr[i0:min(i1, len(arr))], dtype=float)
    return seg[np.isfinite(seg)]


def _compute_ivv(ctx):
    """Intracyclic velocity variation across the swim = std ÷ mean of velocity over
    [stroke_start, finish]. Detector-independent: it reads the window, never the cycles, so
    it is Layer A even though "intracyclic" names a cycle. Structurally the same reduction as
    _compute_uw_ivv but WITHOUT its breaststroke gate — that gate exists because the kick
    group is meaningless for a pulldown, which has nothing to do with surface-swim variance."""
    w = _swim_window(ctx)
    if w is None:
        return None
    seg = _finite_slice(ctx.vel, w[0], w[1])
    if len(seg) < 2:
        return None
    mean = float(np.mean(seg))
    if not np.isfinite(mean) or mean == 0:
        return None
    return float(np.std(seg) / mean)


def _breakout_slice(ctx, span_s):
    """(i0, i1) covering span_s seconds from stroke_start, clipped to the swim window."""
    w = _swim_window(ctx)
    if w is None or not ctx.fs or ctx.fs <= 0:
        return None
    i0, i1, _dur = w
    end = min(i1, i0 + max(1, int(round(float(span_s) * float(ctx.fs)))))
    return (i0, end) if end > i0 else None


def _compute_breakout_vel(ctx):
    """Mean velocity over the first _BREAKOUT_WINDOW_S of the swim — how much speed survives
    the transition from underwater to surface swimming."""
    s = _breakout_slice(ctx, _BREAKOUT_WINDOW_S)
    if s is None:
        return None
    seg = _finite_slice(ctx.vel, s[0], s[1])
    return float(np.mean(seg)) if len(seg) else None


def _compute_breakout_vel_loss(ctx):
    """Underwater average speed − the speed trough shortly after breakout. Positive = the
    swimmer gave up speed surfacing (the normal case). The trough is the minimum over
    _BREAKOUT_LOSS_WINDOW_S rather than an instant, so one dropout sample cannot define it."""
    uw = _compute_uw_avg_speed(ctx)
    if uw is None:
        return None
    s = _breakout_slice(ctx, _BREAKOUT_LOSS_WINDOW_S)
    if s is None:
        return None
    seg = _finite_slice(ctx.vel, s[0], s[1])
    if len(seg) == 0:
        return None
    return float(uw) - float(np.min(seg))


def _compute_breakout_vs_steady(ctx):
    """Breakout-window mean ÷ steady-state mean. Above 1 = the breakout carried more speed
    than the swim settled at; below 1 = the swimmer was still building. "Steady" excludes BOTH
    ends: the breakout window itself at the front, and _STEADY_TRIM_FRAC of the window at the
    back (the finish_s mitigation)."""
    bo = _compute_breakout_vel(ctx)
    if bo is None:
        return None
    w = _swim_window(ctx)
    s = _breakout_slice(ctx, _BREAKOUT_WINDOW_S)
    if w is None or s is None:
        return None
    i0, i1, _dur = w
    start = s[1]
    end = i1 - int(round((i1 - i0) * _STEADY_TRIM_FRAC))
    if end <= start:
        return None
    seg = _finite_slice(ctx.vel, start, end)
    if len(seg) < 2:
        return None
    steady = float(np.mean(seg))
    if not np.isfinite(steady) or steady <= 0:
        return None
    return float(bo) / steady


def _dive_relative(ctx):
    """Shared anchor block for every dive-relative distance metric (the fixed splits and
    splits_remainder — 88-01 D5): resolve dive_start_s, its index, the 0 m origin (d0), and the
    finish-clamped array of distance-since-dive-start. Returns (i_start, rel, end), or None when
    dive_start_s or d0 can't be resolved. Extracted verbatim from _split_velocity so there is
    exactly one "where is 0 m" rule for these metrics (CONTEXT F5 is three of them on the page)."""
    b = _bounds(ctx)
    i_start = _idx(ctx, b.get("dive_start_s"))
    if i_start is None or len(ctx.dist) <= i_start:
        return None
    d0 = float(ctx.dist[i_start])
    if not np.isfinite(d0):
        return None
    fin_idx = _idx(ctx, _finish_s(ctx))
    end = len(ctx.dist) if fin_idx is None else min(len(ctx.dist), fin_idx + 1)
    rel = np.asarray(ctx.dist[i_start:end], dtype=float) - d0
    return i_start, rel, end


def _split_velocity(ctx, meters):
    """Mean velocity over the 5 m segment ENDING at `meters`, measured from dive_start as the
    0 m anchor. None when the swim never reached that distance — which is the normal case for
    the 20/25 m splits on a short trial, not an error."""
    anchor = _dive_relative(ctx)
    if anchor is None:
        return None
    i_start, rel, end = anchor

    def _first_at(target):
        hits = np.nonzero(np.isfinite(rel) & (rel >= target))[0]
        return int(hits[0]) + i_start if len(hits) else None

    i_a, i_b = _first_at(float(meters) - 5.0), _first_at(float(meters))
    if i_a is None or i_b is None or i_b <= i_a:
        return None
    dt = float(ctx.t[i_b]) - float(ctx.t[i_a])
    dd = float(ctx.dist[i_b]) - float(ctx.dist[i_a])
    if not (np.isfinite(dt) and np.isfinite(dd)) or dt <= 0:
        return None
    return dd / dt


def _remainder_velocity(ctx):
    """Mean velocity from the first sample at 20 m past dive_start to the finish sample —
    the closing stretch a 25-yard tether-limited lap actually has, in place of the unreachable
    20-25 m bin (CONTEXT F2). Same chord convention as the fixed bins (delta-distance over
    delta-time, D4), not a sample mean of ctx.vel — so a coach reading this row directly beneath
    four chord rows is reading the same kind of number, and 88-04's picker can reproduce it
    exactly. None when the swim never reaches 20 m, or when the tail past 20 m is under
    _MIN_REMAINDER_M (D3) — arithmetically fine but too short to mean anything."""
    anchor = _dive_relative(ctx)
    if anchor is None:
        return None
    i_start, rel, end = anchor

    def _first_at(target):
        hits = np.nonzero(np.isfinite(rel) & (rel >= target))[0]
        return int(hits[0]) + i_start if len(hits) else None

    i_a = _first_at(20.0)
    i_b = i_start + len(rel) - 1
    if i_a is None or i_b <= i_a:
        return None
    dt = float(ctx.t[i_b]) - float(ctx.t[i_a])
    dd = float(ctx.dist[i_b]) - float(ctx.dist[i_a])
    if not (np.isfinite(dt) and np.isfinite(dd)) or dt <= 0 or dd < _MIN_REMAINDER_M:
        return None
    return dd / dt


def _make_split(meters):
    def _fn(ctx):
        return _split_velocity(ctx, meters)
    _fn.__name__ = f"_compute_splits_{meters}m"
    return _fn


def _compute_accel_asymmetry(ctx):
    """Time spent accelerating ÷ time spent decelerating across the swim. 1.0 = balanced;
    below 1 = more of the swim is spent losing speed than making it. None when ctx.accel is
    empty (pre-Phase-64 sessions carry no acceleration_profile) or nothing is negative."""
    if len(ctx.accel) == 0:
        return None
    w = _swim_window(ctx)
    if w is None:
        return None
    seg = _finite_slice(ctx.accel, w[0], w[1])
    if len(seg) < 2:
        return None
    pos = int(np.count_nonzero(seg > 0))
    neg = int(np.count_nonzero(seg < 0))
    return float(pos) / float(neg) if neg else None


def _swim_cycles(ctx):
    """The stroke cycles that start inside the swim window, as (start_idx, end_idx, cycle).

    THE annotations-first seam for Layer-B metrics. No precedence logic lives here: ctx.cycles
    is whatever metrics_json.cycles holds, and PUT /annotations has already replaced that with
    compute_session_metrics(manual=...) output whenever a coach annotated the session. So the
    coach's cycles arrive here by construction, and the auto segmenter's arrive otherwise —
    the difference is reported through ctx.segmentation_reliable, not decided here."""
    if not isinstance(ctx.cycles, list) or not ctx.cycles:
        return []
    w = _swim_window(ctx)
    if w is None:
        return []
    i0, i1, _dur = w
    out = []
    for c in ctx.cycles:
        if not isinstance(c, dict):
            continue
        a, b = c.get("start_idx"), c.get("end_idx")
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            continue
        a, b = int(a), int(b)
        if a < i0 or a >= i1 or b <= a or b > len(ctx.vel):
            continue
        out.append((a, b, c))
    return out


def _compute_sr_dps_coupling(ctx):
    """Correlation between per-cycle stroke rate (60 ÷ duration) and distance per stroke.
    Strongly negative = the swimmer buys tempo by giving up distance; near zero = the two move
    independently. Pearson r over the swim window's cycles. None below _MIN_COUPLING_CYCLES
    cycles or when either series has no variance (r undefined, not zero)."""
    cyc = _swim_cycles(ctx)
    sr, dps = [], []
    for _a, _b, c in cyc:
        dur, dist = c.get("duration_s"), c.get("dist_m")
        if not isinstance(dur, (int, float)) or not isinstance(dist, (int, float)):
            continue
        dur, dist = float(dur), float(dist)
        if not (np.isfinite(dur) and np.isfinite(dist)) or dur <= 0:
            continue
        sr.append(60.0 / dur)
        dps.append(dist)
    if len(sr) < _MIN_COUPLING_CYCLES:
        return None
    a, b = np.asarray(sr), np.asarray(dps)
    if float(np.std(a)) == 0 or float(np.std(b)) == 0:
        return None
    r = float(np.corrcoef(a, b)[0, 1])
    return r if np.isfinite(r) else None


def _compute_dead_spot_timing(ctx):
    """Mean seconds from the start of a stroke cycle to that cycle's slowest instant — where
    in the stroke the swimmer loses the most speed (75-06 D9). Reported in absolute seconds,
    matching the registry unit; a normalized within-cycle fraction would hide the fact that a
    slower cycle has a later dead spot."""
    offsets = []
    if not ctx.fs or ctx.fs <= 0:
        return None
    for a, b, _c in _swim_cycles(ctx):
        seg = np.asarray(ctx.vel[a:b], dtype=float)
        if not np.any(np.isfinite(seg)):
            continue
        offsets.append(float(np.nanargmin(seg)) / float(ctx.fs))
    return float(np.mean(offsets)) if offsets else None


# ─── Whole-race metrics (Phase 75-06) ─────────────────────────────────────────
# Cross-phase reductions: they describe the race as a whole rather than one window, so they
# have no single window of their own (which is why the report card gives the Whole section a
# full-trace inset). All Layer A — boundary and profile arithmetic, no cycles.

# The three measurable race phases, each as the (start, end) boundary-key pair bounding it.
_PHASE_SPANS = {
    "start":      ("dive_start_s", "underwater_start_s"),
    "underwater": ("underwater_start_s", "stroke_start_s"),
    "swim":       ("stroke_start_s", "finish_s"),
}


def _phase_span(ctx, name):
    """(i0, i1, duration_s) for one named race phase, or None. The swim span resolves its end
    through _finish_s so a missing finish degrades to the end of the trace rather than
    deleting the phase."""
    b = _bounds(ctx)
    start_key, end_key = _PHASE_SPANS[name]
    end = _finish_s(ctx) if end_key == "finish_s" else b.get(end_key)
    return _window(ctx, b.get(start_key), end)


def _race_span(ctx):
    """(i0, i1, duration_s) for the whole race — dive_start to finish."""
    return _window(ctx, _bounds(ctx).get("dive_start_s"), _finish_s(ctx))


def _make_time_budget(name):
    def _fn(ctx):
        span, total = _phase_span(ctx, name), _race_span(ctx)
        if span is None or total is None or total[2] <= 0:
            return None
        return span[2] / total[2] * 100.0
    _fn.__name__ = f"_compute_phase_time_budget_{name}"
    return _fn


def _make_dist_budget(name):
    def _fn(ctx):
        span, total = _phase_span(ctx, name), _race_span(ctx)
        if span is None or total is None:
            return None
        d_span = _span_distance(ctx, span[0], span[1])
        d_total = _span_distance(ctx, total[0], total[1])
        if d_span is None or d_total is None or d_total <= 0:
            return None
        return d_span / d_total * 100.0
    _fn.__name__ = f"_compute_phase_dist_budget_{name}"
    return _fn


def _make_vel_envelope(name):
    """Peak velocity within one phase, or across the whole race for name='overall' (75-06 D6).
    Read across the four rows, these trace how the race's speed ceiling decays after the dive."""
    def _fn(ctx):
        span = _race_span(ctx) if name == "overall" else _phase_span(ctx, name)
        if span is None:
            return None
        seg = _finite_slice(ctx.vel, span[0], span[1])
        return float(np.max(seg)) if len(seg) else None
    _fn.__name__ = f"_compute_vel_envelope_{name}"
    return _fn


def _compute_jerk_smoothness(ctx):
    """Mean |Δacceleration| per second across the swim — how jerky the surface swim is.
    ⚠ Jerk is a SECOND derivative of an axial signal, so it is noise-amplified even though
    ctx.accel is already the Savitzky-Golay derivative (PIPELINE §1.7). Usable as a
    within-athlete relative proxy; do not read it as an absolute smoothness number.
    None when ctx.accel is empty (pre-Phase-64 sessions)."""
    if len(ctx.accel) == 0:
        return None
    w = _swim_window(ctx)
    if w is None or not ctx.fs or ctx.fs <= 0:
        return None
    seg = _finite_slice(ctx.accel, w[0], w[1])
    if len(seg) < 2:
        return None
    return float(np.mean(np.abs(np.diff(seg))) * float(ctx.fs))


# ─── Registry ────────────────────────────────────────────────────────────────
# One MetricSpec per metric in the Phase-75 CONTEXT taxonomy. As of 75-06 every spec is
# status="implemented" EXCEPT streamline_drag (a nonlinear drag-decay fit the tether
# confounds), which stays planned. Tiers follow the CONTEXT feasibility tags:
# already-derivable-from-existing-data (was tagged (cheap)) -> low/medium,
# needs-new-signal-processing (peak-picker / detector / model-fit) -> high.
# Do not add metrics beyond the taxonomy and do not flip any status here — that is
# Step 2's job, one metric at a time, at the user's explicit approval (D12).
REGISTRY: tuple[MetricSpec, ...] = (
    # Phase 1 — Start (dive | push-off) — 75-04: 10 of 11 implemented; streamline_drag deferred
    MetricSpec("peak_vel", "start", "Peak velocity", "m/s", "low",
               status="implemented", compute=_compute_peak_vel),
    MetricSpec("time_to_peak_vel", "start", "Time to peak velocity", "s", "low",
               status="implemented", compute=_compute_time_to_peak_vel),
    MetricSpec("max_accel", "start", "Max acceleration off block/wall", "m/s^2", "low",
               status="implemented", compute=_compute_max_accel),
    MetricSpec("dive_duration", "start", "Dive/push-off duration", "s", "medium",
               status="implemented", compute=_compute_dive_duration),
    MetricSpec("glide_duration", "start", "Glide duration", "s", "high",
               status="implemented", compute=_compute_glide_duration),
    MetricSpec("glide_distance", "start", "Glide distance", "m", "high",
               status="implemented", compute=_compute_glide_distance),
    MetricSpec("glide_avg_speed", "start", "Glide average speed", "m/s", "high",
               status="implemented", compute=_compute_glide_avg_speed),
    MetricSpec("glide_decel", "start", "Glide speed-loss rate", "m/s^2", "high",
               status="implemented", compute=_compute_glide_decel),
    MetricSpec("streamline_drag", "start", "Streamline drag coefficient", "", "high"),
    MetricSpec("break_into_kick_vel", "start", "Break-into-kick velocity", "m/s", "high",
               status="implemented", compute=_compute_break_into_kick_vel),
    MetricSpec("reaction_time", "start", "Reaction time (GO signal)", "s", "high",
               status="implemented", compute=_compute_reaction_time),

    # Phase 2 — Underwater (dolphin kicks | breaststroke pulldown)
    MetricSpec("uw_duration", "underwater", "Underwater duration", "s", "low",
               status="implemented", compute=_compute_uw_duration),
    MetricSpec("uw_distance", "underwater", "Underwater distance", "m", "low",
               status="implemented", compute=_compute_uw_distance),
    MetricSpec("uw_avg_speed", "underwater", "Underwater average speed", "m/s", "low",
               status="implemented", compute=_compute_uw_avg_speed),
    MetricSpec("uw_surface_ratio", "underwater", "Underwater ÷ surface speed ratio", "ratio", "medium",
               status="implemented", compute=_compute_uw_surface_ratio),
    MetricSpec("kick_count", "underwater", "Kick count", "count", "high",
               status="implemented", compute=_compute_kick_count),
    MetricSpec("dist_per_kick", "underwater", "Distance per kick", "m", "high",
               status="implemented", compute=_compute_dist_per_kick),
    MetricSpec("kick_tempo", "underwater", "Kick tempo", "kicks/s", "high",
               status="implemented", compute=_compute_kick_tempo),
    MetricSpec("kick_consistency", "underwater", "Kick consistency (CV)", "ratio", "high",
               status="implemented", compute=_compute_kick_consistency),
    MetricSpec("uw_ivv", "underwater", "Underwater intracyclic velocity variation", "ratio", "high",
               status="implemented", compute=_compute_uw_ivv),
    MetricSpec("per_kick_decay", "underwater", "Per-kick speed decay", "%", "high",
               status="implemented", compute=_compute_per_kick_decay),
    MetricSpec("first_kick_impulse", "underwater", "First-kick impulse", "m/s", "high",
               status="implemented", compute=_compute_first_kick_impulse),
    MetricSpec("pulldown_peak_vel", "underwater", "Pulldown peak velocity", "m/s", "low",
               status="implemented", compute=_compute_pulldown_peak_vel),
    MetricSpec("pulldown_duration", "underwater", "Pulldown duration", "s", "low",
               status="implemented", compute=_compute_pulldown_duration),

    # Phase 3 — Swim (strokes; breakout = special first stroke) — 75-06
    # `splits` is registered as one spec PER DISTANCE rather than a single list-valued spec
    # (75-06 D7). The report card builds an athlete's usual range by reading the SAME key out
    # of past sessions, so a list would force baseline lookup to index into an array whose
    # length varies per session (a 15 m trial has no 25 m split) and elements would silently
    # misalign across history. Scalar keys are independently None-able instead.
    # ⛔ REMOVED: `breathing_dip` (was: "Breathing-stroke velocity dip"). Not deferred —
    # unbuildable. It requires knowing WHICH cycles were breaths, and a 1-D axial encoder on a
    # tether does not observe head position. Do not re-add it without a second sensor.
    MetricSpec("ivv", "swim", "Intracyclic velocity variation", "ratio", "medium",
               status="implemented", compute=_compute_ivv),
    MetricSpec("breakout_vel", "swim", "Breakout velocity", "m/s", "low",
               status="implemented", compute=_compute_breakout_vel),
    MetricSpec("breakout_vel_loss", "swim", "Velocity loss at breakout", "m/s", "medium",
               status="implemented", compute=_compute_breakout_vel_loss),
    MetricSpec("breakout_vs_steady", "swim", "Breakout vs steady-state ratio", "ratio", "medium",
               status="implemented", compute=_compute_breakout_vs_steady),
    MetricSpec("splits_5m", "swim", "Split 0–5 m", "m/s", "low",
               status="implemented", compute=_make_split(5)),
    MetricSpec("splits_10m", "swim", "Split 5–10 m", "m/s", "low",
               status="implemented", compute=_make_split(10)),
    MetricSpec("splits_15m", "swim", "Split 10–15 m", "m/s", "low",
               status="implemented", compute=_make_split(15)),
    MetricSpec("splits_20m", "swim", "Split 15–20 m", "m/s", "low",
               status="implemented", compute=_make_split(20)),
    MetricSpec("splits_remainder", "swim", "Split 20 m to finish", "m/s", "low",
               status="implemented", compute=_remainder_velocity),
    MetricSpec("accel_asymmetry", "swim", "Acceleration asymmetry", "ratio", "medium",
               status="implemented", compute=_compute_accel_asymmetry),
    # The two Layer-B specs: they read ctx.cycles, so they inherit stroke-cycle segmentation
    # quality and are flagged provisional whenever those cycles are auto rather than a coach's.
    MetricSpec("sr_dps_coupling", "swim", "Stroke-rate ↔ DPS coupling", "ratio", "low",
               status="implemented", compute=_compute_sr_dps_coupling, needs_cycles=True),
    MetricSpec("dead_spot_timing", "swim", "Dead-spot timing within cycle", "s", "medium",
               status="implemented", compute=_compute_dead_spot_timing, needs_cycles=True),

    # Whole race (cross-phase) — 75-06. Same per-element expansion as splits, for the same
    # baseline-alignment reason: `phase_time_budget`, `phase_dist_budget` and `vel_envelope`
    # were each one vector-valued spec and are now one spec per phase.
    MetricSpec("phase_time_budget_start", "whole", "Start time share", "%", "medium",
               status="implemented", compute=_make_time_budget("start")),
    MetricSpec("phase_time_budget_underwater", "whole", "Underwater time share", "%", "medium",
               status="implemented", compute=_make_time_budget("underwater")),
    MetricSpec("phase_time_budget_swim", "whole", "Swim time share", "%", "medium",
               status="implemented", compute=_make_time_budget("swim")),
    MetricSpec("phase_dist_budget_start", "whole", "Start distance share", "%", "medium",
               status="implemented", compute=_make_dist_budget("start")),
    MetricSpec("phase_dist_budget_underwater", "whole", "Underwater distance share", "%", "medium",
               status="implemented", compute=_make_dist_budget("underwater")),
    MetricSpec("phase_dist_budget_swim", "whole", "Swim distance share", "%", "medium",
               status="implemented", compute=_make_dist_budget("swim")),
    MetricSpec("vel_envelope_start", "whole", "Start peak velocity", "m/s", "low",
               status="implemented", compute=_make_vel_envelope("start")),
    MetricSpec("vel_envelope_underwater", "whole", "Underwater peak velocity", "m/s", "low",
               status="implemented", compute=_make_vel_envelope("underwater")),
    MetricSpec("vel_envelope_swim", "whole", "Swim peak velocity", "m/s", "low",
               status="implemented", compute=_make_vel_envelope("swim")),
    MetricSpec("vel_envelope_overall", "whole", "Race peak velocity", "m/s", "low",
               status="implemented", compute=_make_vel_envelope("overall")),
    # Unit corrected from the 75-01 placeholder "ratio": mean |Δaccel|/Δt is a jerk, m/s³. The
    # report card overrides units for display, but the stored value is read by other consumers.
    MetricSpec("jerk_smoothness", "whole", "Whole-swim smoothness (jerk)", "m/s³", "medium",
               status="implemented", compute=_compute_jerk_smoothness),
)


def compute_phases(ctx: PhaseContext) -> dict:
    """Build the phases object api.py stores in metrics_json and returns in responses.

    Resolves the four race-phase boundaries ONCE (Phase 75-02) and hangs them on the
    context as ctx.bounds before any compute fn runs, so every window metric reads the
    same decomposition. They are also emitted as out["boundaries"], with per-key
    sources, so a reader can tell a coach's mark from a detector's guess.

    Partitions REGISTRY by phase. For each spec: status=="implemented" specs call
    spec.compute(ctx), with any exception swallowed to value=None (a metric must never
    fail the whole response); status=="planned" specs are value=None by construction.
    Never raises.
    """
    try:
        ctx.bounds = resolve_boundaries(ctx)
    except Exception:
        ctx.bounds = {k: None for k in _BOUNDARY_KEYS}
        ctx.bounds["sources"] = {k: "none" for k in _BOUNDARY_KEYS}
    out = {
        "schema_version": SCHEMA_VERSION,
        "go_signal_s": ctx.go_signal_s,
        "boundaries": ctx.bounds,
        # Non-registry session data, like `boundaries` above (Phase 83-02). Emitted here
        # because every write path stores this return verbatim under `phases`.
        "kick_bands": _kick_bands(ctx),
    }
    for phase in PHASES:
        out[phase] = {}
    for spec in REGISTRY:
        value = None
        if spec.status == "implemented" and spec.compute is not None:
            try:
                value = spec.compute(ctx)
            except Exception:
                value = None
        out[spec.phase][spec.key] = {
            "value": value,
            "unit": spec.unit,
            "label": spec.label,
            "tier": spec.tier,
            "status": spec.status,
            # SCHEMA_VERSION 3 (75-06). True = this number was derived from AUTO stroke
            # cycles, whose count is unmeasured on the auto path. The report card renders a
            # provisional metric without valence color so it never reads as confident.
            # Always False for window metrics, which do not touch the cycles at all.
            "provisional": bool(spec.needs_cycles and not ctx.segmentation_reliable),
        }
    return out
