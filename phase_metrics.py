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

PHASES = ("start", "underwater", "swim", "whole")
TIERS = ("low", "medium", "high")
STATUSES = ("planned", "implemented")

SCHEMA_VERSION = 1


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
    """
    t: np.ndarray
    vel: np.ndarray
    dist: np.ndarray
    accel: np.ndarray
    fs: float
    stroke_type: str | None
    go_signal_s: float | None = None


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
    MetricSpec("uw_duration", "underwater", "Underwater duration", "s", "low"),
    MetricSpec("uw_distance", "underwater", "Underwater distance", "m", "low"),
    MetricSpec("uw_avg_speed", "underwater", "Underwater average speed", "m/s", "low"),
    MetricSpec("uw_surface_ratio", "underwater", "Underwater ÷ surface speed ratio", "ratio", "medium"),
    MetricSpec("kick_count", "underwater", "Kick count", "count", "high"),
    MetricSpec("dist_per_kick", "underwater", "Distance per kick", "m", "high"),
    MetricSpec("kick_tempo", "underwater", "Kick tempo", "kicks/s", "high"),
    MetricSpec("kick_consistency", "underwater", "Kick consistency (CV)", "ratio", "high"),
    MetricSpec("uw_ivv", "underwater", "Underwater intracyclic velocity variation", "ratio", "high"),
    MetricSpec("per_kick_decay", "underwater", "Per-kick speed decay", "%", "high"),
    MetricSpec("first_kick_impulse", "underwater", "First-kick impulse", "m/s", "high"),
    MetricSpec("pulldown_peak_vel", "underwater", "Pulldown peak velocity", "m/s", "low"),
    MetricSpec("pulldown_duration", "underwater", "Pulldown duration", "s", "low"),

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

    Partitions REGISTRY by phase. For each spec: status=="implemented" specs call
    spec.compute(ctx), with any exception swallowed to value=None (a metric must never
    fail the whole response); status=="planned" specs are value=None by construction.
    With today's all-planned REGISTRY, every value is None — that is the intended
    skeleton output. Never raises.
    """
    out = {"schema_version": SCHEMA_VERSION, "go_signal_s": ctx.go_signal_s}
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
