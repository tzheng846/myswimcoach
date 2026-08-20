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
        # the other three fall back to the seed
        assert b["stroke_start_s"] == 8.0
        assert b["sources"]["stroke_start_s"] == "auto"
        assert b["sources"]["finish_s"] == "auto"

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

    def test_null_stroke_start_blanks_all_four(self):
        v = self._values(_ctx(annotation_phases={"underwater_start_s": 3.0},
                              seed_phases={"finish_s": 18.0}))
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
