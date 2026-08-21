"""Unit tests for phase_metrics.py — registry invariants + compute engine (Phase 75-01)."""
import numpy as np
import pytest

import phase_metrics as pm
from phase_metrics import (
    MetricSpec,
    SCHEMA_VERSION,
    resolve_boundaries,
    PhaseContext,
    PHASES,
    TIERS,
    REGISTRY,
    compute_phases,
)


def _make_ctx(**overrides):
    n = 50
    defaults = dict(
        t=np.arange(n) / 10.0,
        vel=np.full(n, 1.0),
        dist=np.arange(n) * 0.1,
        accel=np.zeros(n),
        fs=10.0,
        stroke_type="freestyle",
        go_signal_s=None,
    )
    defaults.update(overrides)
    return PhaseContext(**defaults)


class TestRegistryInvariants:
    """AC-1: REGISTRY is the single declarative source of truth, fully populated as planned."""

    def test_keys_unique(self):
        keys = [spec.key for spec in REGISTRY]
        assert len(keys) == len(set(keys)), "duplicate metric key in REGISTRY"

    def test_every_spec_has_valid_phase_and_tier(self):
        for spec in REGISTRY:
            assert spec.phase in PHASES, f"{spec.key}: bad phase {spec.phase!r}"
            assert spec.tier in ("low", "medium", "high"), f"{spec.key}: bad tier {spec.tier!r}"
            assert spec.tier in TIERS

    def test_status_and_compute_fn_agree(self):
        """The invariant that survives Step 2: a `planned` spec reserves a slot and has
        no compute fn; an `implemented` one must supply one. (75-01 asserted the stronger
        'everything is planned', which 75-02 retires by implementing the first metrics.)"""
        for spec in REGISTRY:
            if spec.status == "planned":
                assert spec.compute is None, f"{spec.key} is planned but has a compute fn"
            else:
                assert spec.compute is not None, f"{spec.key} is implemented with no compute fn"

    def test_reaction_time_reserved_under_start(self):
        keys_by_phase = {spec.key: spec.phase for spec in REGISTRY}
        assert "reaction_time" in keys_by_phase
        assert keys_by_phase["reaction_time"] == "start"

    def test_registry_nonempty_and_covers_all_phases(self):
        phases_present = {spec.phase for spec in REGISTRY}
        assert phases_present == set(PHASES)
        assert len(REGISTRY) >= 30  # the full taxonomy, not a token subset


class TestMetricSpecValidation:
    def test_unknown_phase_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "not_a_phase", "X", "s", "low")

    def test_unknown_tier_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "start", "X", "s", "not_a_tier")

    def test_planned_with_compute_fn_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "start", "X", "s", "low", status="planned", compute=lambda ctx: 1.0)

    def test_implemented_without_compute_fn_rejected(self):
        with pytest.raises(ValueError):
            MetricSpec("x", "start", "X", "s", "low", status="implemented", compute=None)

    def test_implemented_with_compute_fn_accepted(self):
        spec = MetricSpec("x", "start", "X", "s", "low", status="implemented", compute=lambda ctx: 1.0)
        assert spec.compute(_make_ctx()) == 1.0


class TestComputePhases:
    """AC-1/AC-2 engine behavior: the seam runs cleanly with an all-planned registry."""

    def test_returns_four_phase_buckets_plus_metadata(self):
        result = compute_phases(_make_ctx())
        assert result["schema_version"] == SCHEMA_VERSION
        assert "go_signal_s" in result
        assert "boundaries" in result
        for phase in PHASES:
            assert phase in result
            assert isinstance(result[phase], dict)

    def test_every_registry_key_reflected_with_its_spec_metadata(self):
        result = compute_phases(_make_ctx())
        for spec in REGISTRY:
            entry = result[spec.phase][spec.key]
            if spec.status == "planned":
                assert entry["value"] is None
            assert entry["status"] == spec.status
            assert entry["unit"] == spec.unit
            assert entry["label"] == spec.label
            assert entry["tier"] == spec.tier

    def test_reaction_time_entry_value_none_status_planned(self):
        result = compute_phases(_make_ctx())
        entry = result["start"]["reaction_time"]
        assert entry["value"] is None
        assert entry["status"] == "planned"

    def test_go_signal_passed_through(self):
        result = compute_phases(_make_ctx(go_signal_s=12.5))
        assert result["go_signal_s"] == 12.5

    def test_never_raises_on_empty_accel(self):
        ctx = _make_ctx(accel=np.array([]))
        result = compute_phases(ctx)  # must not raise
        assert result["schema_version"] == SCHEMA_VERSION


class TestComputeSeamWiring:
    """Prove the engine actually calls compute() for implemented specs, and swallows
    exceptions to None — this is the seam Step 2 will rely on."""

    def _registry_with(self, extra_spec):
        return tuple(REGISTRY) + (extra_spec,)

    def test_implemented_spec_compute_is_called(self, monkeypatch):
        called = {}

        def fake_compute(ctx):
            called["yes"] = True
            return 42.0

        extra = MetricSpec("test_only_metric", "start", "Test", "s", "low",
                            status="implemented", compute=fake_compute)
        monkeypatch.setattr("phase_metrics.REGISTRY", self._registry_with(extra))

        result = compute_phases(_make_ctx())
        assert called.get("yes") is True
        assert result["start"]["test_only_metric"]["value"] == 42.0
        assert result["start"]["test_only_metric"]["status"] == "implemented"

    def test_raising_compute_fn_degrades_to_none(self, monkeypatch):
        def boom(ctx):
            raise RuntimeError("simulated failure")

        extra = MetricSpec("test_boom_metric", "start", "Test", "s", "low",
                            status="implemented", compute=boom)
        monkeypatch.setattr("phase_metrics.REGISTRY", self._registry_with(extra))

        result = compute_phases(_make_ctx())  # must not raise
        assert result["start"]["test_boom_metric"]["value"] is None


# ── Phase 75-02: boundary resolution + the underwater window metrics ──────────

def _uw_trace(fs=100.0, dur_s=20.0, dip_t=3.0, speed=1.0):
    """Synthetic trace: a start surge, a decaying glide, a prominent dip at dip_t, then
    steady stroking. dist is the exact integral of vel, so window arithmetic on it is
    checkable to floating-point precision."""
    n = int(dur_s * fs)
    t = np.arange(n) / fs
    vel = np.full(n, speed)
    surge = t < dip_t
    # rise to 3 m/s then decay to 0.4 m/s right at dip_t
    vel[surge] = 0.4 + 2.6 * np.exp(-3.0 * t[surge])
    vel[int(dip_t * fs)] = 0.15                     # the dip itself
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])
    return t, vel, dist


def _dive_surge_trace(fs=100.0, dur_s=14.0):
    """Phase 79: low onset, a sub-X jump-sink tug, then a dive surge crossing X≈2. The
    launch FOOT (sink trough) sits at 0.9 s; steady stroking (1.0 m/s) follows. Unlike
    _uw_trace this does NOT start above X, so detect_dive_start has a foot to anchor."""
    n = int(dur_s * fs)
    t = np.arange(n) / fs
    vel = np.full(n, 1.0)
    tug, sink, crest = 0.4, 0.9, 1.6
    vel = np.piecewise(
        t,
        [t < tug,
         (t >= tug) & (t < sink),
         (t >= sink) & (t < crest),
         (t >= crest) & (t < 3.0)],
        [lambda x: 0.9 * x / tug,
         lambda x: 0.9 - (0.9 - 0.15) * (x - tug) / (sink - tug),
         lambda x: 0.15 + (3.0 - 0.15) * (x - sink) / (crest - sink),
         lambda x: 3.0 - (3.0 - 1.0) * (x - crest) / (3.0 - crest),
         1.0],
    )
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])
    return t, vel, dist


def _ctx(fs=100.0, **kw):
    t, vel, dist = _uw_trace(fs=fs)
    defaults = dict(t=t, vel=vel, dist=dist, accel=np.gradient(vel, t), fs=fs,
                    stroke_type="freestyle")
    defaults.update(kw)
    return PhaseContext(**defaults)


class TestBoundaryResolution:
    """AC-2: the coach's annotation wins; the detector only fills the gap."""

    def test_annotation_wins_for_every_key(self):
        ann = {"dive_start_s": 0.5, "underwater_start_s": 4.0,
               "stroke_start_s": 8.0, "finish_s": 18.0}
        seed = {"dive_start_s": 0.9, "underwater_start_s": 1.1,
                "stroke_start_s": 6.0, "finish_s": 17.0}
        b = resolve_boundaries(_ctx(annotation_phases=ann, seed_phases=seed))
        for k, v in ann.items():
            assert b[k] == v
            assert b["sources"][k] == "manual"

    def test_unannotated_underwater_start_comes_from_the_detector(self):
        seed = {"dive_start_s": 0.0, "stroke_start_s": 8.0, "finish_s": 18.0}
        ctx = _ctx(seed_phases=seed)
        b = resolve_boundaries(ctx)
        assert b["sources"]["underwater_start_s"] == "detected"
        assert abs(b["underwater_start_s"] - 3.0) < 0.15
        # stroke_start + finish now come from detect_swim_boundaries, overriding the stale seed;
        # dive_start has no ≥X surge to anchor here, so its baseline_end seed stands.
        assert b["sources"]["stroke_start_s"] == "detected"
        assert b["stroke_start_s"] != 8.0
        assert b["sources"]["finish_s"] == "detected"
        assert b["sources"]["dive_start_s"] == "auto"

    def test_detected_value_is_not_the_legacy_dive_peak(self):
        """The seed's own underwater_start_s (the dive-peak rule) must be ignored."""
        seed = {"dive_start_s": 0.0, "underwater_start_s": 0.75,
                "stroke_start_s": 8.0, "finish_s": 18.0}
        b = resolve_boundaries(_ctx(seed_phases=seed))
        assert b["sources"]["underwater_start_s"] == "detected"
        assert b["underwater_start_s"] != 0.75

    def test_no_qualifying_dip_yields_null_with_source_none(self):
        n = 1000
        t = np.arange(n) / 100.0
        vel = np.linspace(0.1, 2.0, n)            # monotone rise, never dips
        dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / 100.0)])
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.zeros(n), fs=100.0,
                           stroke_type="freestyle")
        b = resolve_boundaries(ctx)
        assert b["underwater_start_s"] is None
        assert b["sources"]["underwater_start_s"] == "none"

    def test_no_inputs_at_all_resolves_everything_to_none_without_raising(self):
        n = 20
        ctx = PhaseContext(t=np.arange(n) / 100.0, vel=np.zeros(n), dist=np.zeros(n),
                           accel=np.zeros(n), fs=100.0, stroke_type=None)
        b = resolve_boundaries(ctx)
        for k in ("dive_start_s", "underwater_start_s", "stroke_start_s", "finish_s"):
            assert b[k] is None
            assert b["sources"][k] == "none"

    def test_detector_exception_degrades_to_none(self, monkeypatch):
        monkeypatch.setattr("phase_metrics.metrics.detect_underwater_start",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        b = resolve_boundaries(_ctx(seed_phases={"dive_start_s": 0.0}))
        assert b["underwater_start_s"] is None
        assert b["sources"]["underwater_start_s"] == "none"

    def test_compute_phases_emits_boundaries_and_hangs_them_on_ctx(self):
        ann = {"underwater_start_s": 3.0, "stroke_start_s": 8.0, "finish_s": 18.0}
        ctx = _ctx(annotation_phases=ann)
        out = compute_phases(ctx)
        assert out["boundaries"]["underwater_start_s"] == 3.0
        assert ctx.bounds is out["boundaries"]

    # ── Phase 79: dive_start foot-of-surge detector + baseline_end fallback ────

    def test_unannotated_dive_start_comes_from_the_detector(self):
        t, vel, dist = _dive_surge_trace()
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.gradient(vel, t), fs=100.0,
                           stroke_type="freestyle",
                           seed_phases={"dive_start_s": 0.0})    # baseline_end seed
        b = resolve_boundaries(ctx)
        assert b["sources"]["dive_start_s"] == "detected"
        assert abs(b["dive_start_s"] - 0.9) < 0.05                # the launch foot
        assert b["dive_start_s"] != 0.0                           # overrode the seed

    def test_dive_start_falls_back_to_baseline_end_when_no_surge_reaches_x(self):
        n = 1400
        t = np.arange(n) / 100.0
        vel = np.full(n, 1.2)                                     # steady, never crosses X=2
        dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / 100.0)])
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.zeros(n), fs=100.0,
                           stroke_type="freestyle",
                           seed_phases={"dive_start_s": 0.5})     # baseline_end seed stands
        b = resolve_boundaries(ctx)
        assert b["dive_start_s"] == 0.5
        assert b["sources"]["dive_start_s"] == "auto"

    def test_manual_dive_start_wins_over_the_detector(self):
        t, vel, dist = _dive_surge_trace()                        # a real ≥X surge exists
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.gradient(vel, t), fs=100.0,
                           stroke_type="freestyle",
                           annotation_phases={"dive_start_s": 0.3},
                           seed_phases={"dive_start_s": 0.0})
        b = resolve_boundaries(ctx)
        assert b["dive_start_s"] == 0.3                           # coach's mark, untouched
        assert b["sources"]["dive_start_s"] == "manual"

    def test_dive_start_detector_exception_degrades_to_the_seed(self, monkeypatch):
        monkeypatch.setattr("phase_metrics.metrics.detect_dive_start",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        t, vel, dist = _dive_surge_trace()
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.gradient(vel, t), fs=100.0,
                           stroke_type="freestyle",
                           seed_phases={"dive_start_s": 0.5})
        b = resolve_boundaries(ctx)
        assert b["dive_start_s"] == 0.5                           # fell back, no raise
        assert b["sources"]["dive_start_s"] == "auto"


class TestUnderwaterWindowMetrics:
    """AC-3: window arithmetic when the window is usable, null when it is not."""

    def _values(self, ctx):
        out = compute_phases(ctx)["underwater"]
        return {k: out[k]["value"] for k in out}

    def test_the_four_values_are_the_window_arithmetic(self):
        ann = {"underwater_start_s": 3.0, "stroke_start_s": 8.0, "finish_s": 18.0}
        ctx = _ctx(annotation_phases=ann)
        v = self._values(ctx)

        i0, i1 = int(3.0 * ctx.fs), int(8.0 * ctx.fs)
        exp_dur = 5.0
        exp_dist = float(ctx.dist[i1] - ctx.dist[i0])
        assert v["uw_duration"] == pytest.approx(exp_dur)
        assert v["uw_distance"] == pytest.approx(exp_dist)
        assert v["uw_avg_speed"] == pytest.approx(exp_dist / exp_dur)

        j0, j1 = int(8.0 * ctx.fs), int(18.0 * ctx.fs)
        surface = float(ctx.dist[j1] - ctx.dist[j0]) / 10.0
        assert v["uw_surface_ratio"] == pytest.approx((exp_dist / exp_dur) / surface)

    def test_the_four_specs_report_implemented(self):
        out = compute_phases(_ctx(annotation_phases={"underwater_start_s": 3.0,
                                                     "stroke_start_s": 8.0}))["underwater"]
        for key in ("uw_duration", "uw_distance", "uw_avg_speed", "uw_surface_ratio"):
            assert out[key]["status"] == "implemented"

    def test_null_stroke_start_blanks_all_four(self, monkeypatch):
        # No stroke_start anywhere: not annotated, not seeded, and the detector finds none.
        monkeypatch.setattr("phase_metrics.metrics.detect_swim_boundaries",
                            lambda *a, **k: (None, None))
        v = self._values(_ctx(annotation_phases={"underwater_start_s": 3.0}))
        for key in ("uw_duration", "uw_distance", "uw_avg_speed", "uw_surface_ratio"):
            assert v[key] is None

    def test_window_narrower_than_the_floor_blanks_all_four(self):
        ann = {"underwater_start_s": 3.0, "stroke_start_s": 3.2, "finish_s": 18.0}
        v = self._values(_ctx(annotation_phases=ann))
        for key in ("uw_duration", "uw_distance", "uw_avg_speed", "uw_surface_ratio"):
            assert v[key] is None

    def test_boundary_past_the_end_of_the_trace_blanks_all_four(self):
        ann = {"underwater_start_s": 3.0, "stroke_start_s": 999.0}
        v = self._values(_ctx(annotation_phases=ann))
        for key in ("uw_duration", "uw_distance", "uw_avg_speed", "uw_surface_ratio"):
            assert v[key] is None

    def test_surface_ratio_falls_back_to_the_end_of_the_trace(self):
        """finish_s null is not fatal — the tail of the trace is the surface window."""
        ann = {"underwater_start_s": 3.0, "stroke_start_s": 8.0}
        v = self._values(_ctx(annotation_phases=ann))
        assert v["uw_surface_ratio"] is not None
        assert v["uw_duration"] == pytest.approx(5.0)

    def test_surface_window_too_short_blanks_only_the_ratio(self):
        t, vel, dist = _uw_trace(dur_s=8.3)
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.zeros(len(t)), fs=100.0,
                           stroke_type="freestyle",
                           annotation_phases={"underwater_start_s": 3.0,
                                              "stroke_start_s": 8.0})
        v = self._values(ctx)
        assert v["uw_duration"] == pytest.approx(5.0)
        assert v["uw_surface_ratio"] is None

    def test_compute_phases_never_raises_on_a_degenerate_context(self):
        n = 5
        ctx = PhaseContext(t=np.arange(n) / 100.0, vel=np.zeros(n), dist=np.zeros(n),
                           accel=np.array([]), fs=100.0, stroke_type=None,
                           annotation_phases={"underwater_start_s": 1.0,
                                              "stroke_start_s": 2.0})
        v = self._values(ctx)   # must not raise
        assert v["uw_distance"] is None


class TestPulldownPassthrough:
    """P7: pulldown is the BREASTSTROKE content of the underwater slot."""

    _IP = {"pulldown_peak_vel_ms": 1.85, "pulldown_duration_s": 0.62}

    def test_breaststroke_emits_both(self):
        out = compute_phases(_ctx(stroke_type="breaststroke", initial_phase=self._IP))["underwater"]
        assert out["pulldown_peak_vel"]["value"] == pytest.approx(1.85)
        assert out["pulldown_duration"]["value"] == pytest.approx(0.62)

    def test_freestyle_emits_neither(self):
        out = compute_phases(_ctx(stroke_type="freestyle", initial_phase=self._IP))["underwater"]
        assert out["pulldown_peak_vel"]["value"] is None
        assert out["pulldown_duration"]["value"] is None

    def test_missing_initial_phase_is_not_an_error(self):
        out = compute_phases(_ctx(stroke_type="breaststroke"))["underwater"]
        assert out["pulldown_peak_vel"]["value"] is None


# ── Phase 75-03: the underwater kick detector + seven kick metrics ────────────

def _kick_trace(fs=100.0, n_kicks=6, uw_start=3.0, uw_end=8.0, base=1.0, amp=0.6,
                dur_s=20.0, amps=None):
    """_uw_trace plus n_kicks evenly-spaced propulsive bumps strictly inside
    (uw_start, uw_end). dist is the exact integral of vel. amps overrides per-bump height."""
    t, vel, _ = _uw_trace(fs=fs, dur_s=dur_s, dip_t=uw_start, speed=base)
    centers = np.linspace(uw_start, uw_end, n_kicks + 2)[1:-1]
    if amps is None:
        amps = [amp] * len(centers)
    for c, a in zip(centers, amps):
        vel = vel + a * np.exp(-0.5 * ((t - c) / 0.06) ** 2)
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])
    return t, vel, dist


def _kick_ctx(fs=100.0, uw_start=3.0, uw_end=8.0, stroke_type="freestyle",
              n_kicks=6, amps=None, **kw):
    t, vel, dist = _kick_trace(fs=fs, n_kicks=n_kicks, uw_start=uw_start, uw_end=uw_end,
                               amps=amps)
    defaults = dict(
        t=t, vel=vel, dist=dist, accel=np.gradient(vel, t), fs=fs,
        stroke_type=stroke_type,
        annotation_phases={"underwater_start_s": uw_start, "stroke_start_s": uw_end,
                           "finish_s": 18.0},
    )
    defaults.update(kw)
    return PhaseContext(**defaults)


class TestKickMetrics:
    """AC-2/AC-3: seven metrics off metrics.detect_underwater_kicks."""

    _KEYS = ("kick_count", "kick_tempo", "kick_consistency", "dist_per_kick",
             "per_kick_decay", "first_kick_impulse", "uw_ivv")

    def _uw(self, ctx):
        out = compute_phases(ctx)["underwater"]
        return {k: out[k]["value"] for k in out}

    def test_kick_count_matches_the_known_bumps(self):
        assert self._uw(_kick_ctx(n_kicks=6))["kick_count"] == 6

    def test_tempo_and_consistency_from_intervals(self):
        v = self._uw(_kick_ctx(n_kicks=6))
        assert v["kick_tempo"] is not None and 0.5 < v["kick_tempo"] < 3.0
        assert v["kick_consistency"] is not None and v["kick_consistency"] < 0.15  # even spacing

    def test_dist_per_kick_is_total_uw_distance_over_count(self):
        ctx = _kick_ctx(n_kicks=5)
        i0, i1 = int(3.0 * ctx.fs), int(8.0 * ctx.fs)
        exp = float(ctx.dist[i1] - ctx.dist[i0]) / 5
        assert self._uw(ctx)["dist_per_kick"] == pytest.approx(exp, rel=1e-6)

    def test_first_kick_impulse_positive(self):
        assert self._uw(_kick_ctx(n_kicks=6))["first_kick_impulse"] > 0

    def test_per_kick_decay_sign_tracks_fading_kicks(self):
        fading = self._uw(_kick_ctx(n_kicks=5, amps=[1.0, 0.9, 0.8, 0.7, 0.6]))
        assert fading["per_kick_decay"] is not None and fading["per_kick_decay"] < 0
        building = self._uw(_kick_ctx(n_kicks=5, amps=[0.6, 0.7, 0.8, 0.9, 1.0]))
        assert building["per_kick_decay"] > 0

    def test_uw_ivv_is_detector_independent(self):
        """A window with no clean kicks still yields uw_ivv (std/mean); the count is 0 and
        the interval-based metrics blank."""
        v = self._uw(_kick_ctx(n_kicks=0))
        assert v["uw_ivv"] is not None
        assert v["kick_count"] == 0
        assert v["kick_tempo"] is None
        assert v["kick_consistency"] is None

    def test_single_kick_yields_partial_metrics(self):
        v = self._uw(_kick_ctx(n_kicks=1))
        assert v["kick_count"] == 1
        assert v["dist_per_kick"] is not None
        assert v["first_kick_impulse"] is not None
        assert v["kick_tempo"] is None
        assert v["kick_consistency"] is None
        assert v["per_kick_decay"] is None

    def test_breaststroke_blanks_all_seven(self):
        v = self._uw(_kick_ctx(n_kicks=6, stroke_type="breaststroke"))
        for k in self._KEYS:
            assert v[k] is None, f"{k} should be None for breaststroke"

    def test_no_underwater_window_blanks_all_seven(self, monkeypatch):
        # No stroke_start resolvable → the underwater window can't form.
        monkeypatch.setattr("phase_metrics.metrics.detect_swim_boundaries",
                            lambda *a, **k: (None, None))
        ctx = _ctx(annotation_phases={"underwater_start_s": 3.0})
        v = self._uw(ctx)
        for k in self._KEYS:
            assert v[k] is None, f"{k} should be None without a window"

    def test_all_seven_report_implemented(self):
        out = compute_phases(_kick_ctx())["underwater"]
        for k in self._KEYS:
            assert out[k]["status"] == "implemented"


# ── stroke_start / finish detector: drift guard against the real pipeline ──────
# detect_swim_boundaries deliberately duplicates the boundary block in
# compute_session_metrics (kept there so the hot metric path is untouched). This pins the
# two together on the ground-truth fixtures: if the pipeline's stroke_start ever diverges
# from the standalone detector resolve_boundaries now uses, this test fails loudly.

import json                                                    # noqa: E402
from pathlib import Path                                       # noqa: E402
import metrics as _metrics                                     # noqa: E402

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "segmenter_truth.json"


@pytest.mark.parametrize("row", json.loads(_FIXTURE.read_text())["sessions"],
                         ids=lambda r: f"{r['stroke_type']}-{r['session_id'][:8]}")
def test_detect_swim_boundaries_matches_pipeline(row):
    fs = float(row["sample_rate_hz"])
    vel = np.array([np.nan if v is None else float(v)
                    for v in row["velocity_profile"]], dtype=float)
    t = np.arange(vel.size) / fs
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])
    stroke = row["stroke_type"]

    ss_idx, _ = _metrics.detect_swim_boundaries(t, vel, stroke)
    pipeline_ip_end = _metrics.compute_session_metrics(
        t, vel, dist, stroke_type=stroke)["initial_phase"]["initial_phase_end_idx"]

    assert ss_idx == pipeline_ip_end
