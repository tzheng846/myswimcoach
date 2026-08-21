"""
phase_metrics.py — race-phase metric registry + compute engine (Phase 75-01).

Pure module, no I/O (same convention as metrics.py / annotations.py / ratings.py).

Step 1 of the Phase-75 report-card revamp (CONTEXT.md D11/D15/D16): this module is the
"define + provide space" skeleton, NOT a metrics implementation. It declares one
MetricSpec per taxonomy metric so every metric has a registry slot, key, unit, and
effort tier — and every spec in REGISTRY today is status="planned" with compute=None.
Step 2 (a later plan, one metric at a time, gated on explicit user approval per D12)
flips a spec to status="implemented" and supplies its compute function. Nothing in this
file computes a real metric value.

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

SCHEMA_VERSION = 2  # 2 (Phase 75-02): added the resolved `boundaries` object

# Arithmetic-sanity floor for the underwater window: narrower than this and
# distance/duration ratios are numerical noise rather than a measurement. It is NOT a
# trust gate (75-02 P3) — a wide-but-wrong window is still computed and reported.
_MIN_UW_DURATION_S = 0.5


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


# ─── Registry ────────────────────────────────────────────────────────────────
# One MetricSpec per metric in the Phase-75 CONTEXT taxonomy. ALL status="planned",
# compute=None — see module docstring. Tiers follow the CONTEXT feasibility tags:
# already-derivable-from-existing-data (was tagged (cheap)) -> low/medium,
# needs-new-signal-processing (peak-picker / detector / model-fit) -> high.
# Do not add metrics beyond the taxonomy and do not flip any status here — that is
# Step 2's job, one metric at a time, at the user's explicit approval (D12).
REGISTRY: tuple[MetricSpec, ...] = (
    # Phase 1 — Start (dive | push-off)
    MetricSpec("peak_vel", "start", "Peak velocity", "m/s", "low"),
    MetricSpec("time_to_peak_vel", "start", "Time to peak velocity", "s", "low"),
    MetricSpec("max_accel", "start", "Max acceleration off block/wall", "m/s^2", "low"),
    MetricSpec("dive_duration", "start", "Dive/push-off duration", "s", "medium"),
    MetricSpec("glide_duration", "start", "Glide duration", "s", "high"),
    MetricSpec("glide_distance", "start", "Glide distance", "m", "high"),
    MetricSpec("glide_avg_speed", "start", "Glide average speed", "m/s", "high"),
    MetricSpec("glide_decel", "start", "Glide speed-loss rate", "m/s^2", "high"),
    MetricSpec("streamline_drag", "start", "Streamline drag coefficient", "", "high"),
    MetricSpec("break_into_kick_vel", "start", "Break-into-kick velocity", "m/s", "high"),
    MetricSpec("reaction_time", "start", "Reaction time (GO signal)", "s", "high"),

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

    # Phase 3 — Swim (strokes; breakout = special first stroke)
    MetricSpec("ivv", "swim", "Intracyclic velocity variation", "ratio", "medium"),
    MetricSpec("breakout_vel", "swim", "Breakout velocity", "m/s", "low"),
    MetricSpec("breakout_vel_loss", "swim", "Velocity loss at breakout", "m/s", "medium"),
    MetricSpec("breakout_vs_steady", "swim", "Breakout vs steady-state ratio", "ratio", "medium"),
    MetricSpec("splits", "swim", "Split velocities", "m/s", "low"),
    MetricSpec("sr_dps_coupling", "swim", "Stroke-rate ↔ DPS coupling", "ratio", "low"),
    MetricSpec("dead_spot_timing", "swim", "Dead-spot timing within cycle", "s", "medium"),
    MetricSpec("accel_asymmetry", "swim", "Acceleration asymmetry", "ratio", "medium"),
    MetricSpec("breathing_dip", "swim", "Breathing-stroke velocity dip", "m/s", "high"),

    # Whole race (cross-phase)
    MetricSpec("phase_time_budget", "whole", "Phase time budget", "%", "medium"),
    MetricSpec("phase_dist_budget", "whole", "Phase distance budget", "%", "medium"),
    MetricSpec("vel_envelope", "whole", "Velocity envelope", "m/s", "low"),
    MetricSpec("jerk_smoothness", "whole", "Whole-swim smoothness (jerk)", "ratio", "medium"),
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
        }
    return out
