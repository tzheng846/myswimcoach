"""Unit tests for phase_metrics.py — registry invariants + compute engine (Phase 75-01)."""
import numpy as np
import pytest

import metrics
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

    def test_reaction_time_implemented_but_none_without_go(self):
        result = compute_phases(_make_ctx())
        entry = result["start"]["reaction_time"]
        assert entry["value"] is None             # no GO signal supplied
        assert entry["status"] == "implemented"   # 75-04 flipped it from planned

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


# ── Phase 83-02: per-kick bands (peaks → trough-to-trough spans) ──────────────

class TestSegmentKickBands:
    """AC-1/AC-2: metrics.segment_kick_bands turns the detector's peaks into drawable spans."""

    @staticmethod
    def _bands(n_kicks=5, uw_start=3.0, uw_end=8.0, fs=100.0):
        t, vel, _ = _kick_trace(fs=fs, n_kicks=n_kicks, uw_start=uw_start, uw_end=uw_end)
        i0, i1 = int(uw_start * fs), int(uw_end * fs)
        peaks = metrics.detect_underwater_kicks(t, vel, i0, i1)
        return vel, peaks, i0, i1, metrics.segment_kick_bands(vel, peaks, i0, i1, fs)

    def test_one_band_per_kick_with_its_peak_inside(self):
        vel, peaks, _i0, _i1, bands = self._bands(n_kicks=5)
        assert len(peaks) == 5 and len(bands) == 5
        for b, p in zip(bands, peaks):
            assert b["peak_idx"] == p
            assert b["start_idx"] <= p < b["end_idx"]
        assert [b["kick_num"] for b in bands] == [0, 1, 2, 3, 4]

    def test_consecutive_bands_meet_at_the_velocity_minimum(self):
        vel, peaks, _i0, _i1, bands = self._bands(n_kicks=5)
        for k in range(len(bands) - 1):
            edge = bands[k]["end_idx"]
            assert edge == bands[k + 1]["start_idx"]          # they tile, no gap or overlap
            between = vel[peaks[k] + 1:peaks[k + 1]]
            assert vel[edge] == pytest.approx(float(np.min(between)))

    def test_outer_edges_clamp_to_the_window(self):
        _vel, _peaks, i0, i1, bands = self._bands(n_kicks=5)
        assert bands[0]["start_idx"] == i0
        assert bands[-1]["end_idx"] == i1

    def test_duration_is_the_band_span_in_seconds(self):
        _vel, _peaks, _i0, _i1, bands = self._bands(n_kicks=5, fs=100.0)
        for b in bands:
            assert b["duration_s"] == pytest.approx((b["end_idx"] - b["start_idx"]) / 100.0)

    def test_zero_or_one_peak_yields_no_bands(self):
        """R2: a glide-only or single-kick underwater must produce NOTHING, never one band
        spanning the whole window — that would assert a segmentation nothing measured."""
        for n in (0, 1):
            _vel, peaks, _i0, _i1, bands = self._bands(n_kicks=n)
            assert len(peaks) == n
            assert bands == []

    def test_degenerate_inputs_degrade_to_empty_rather_than_raise(self):
        vel, peaks, i0, i1, _bands = self._bands(n_kicks=5)
        assert metrics.segment_kick_bands(vel, peaks, i1, i0, 100.0) == []       # reversed window
        assert metrics.segment_kick_bands(vel, peaks, i0, i0, 100.0) == []       # empty window
        assert metrics.segment_kick_bands(vel, peaks, 0, 10, 100.0) == []        # peaks outside
        assert metrics.segment_kick_bands(vel, peaks[::-1], i0, i1, 100.0) == []  # unsorted
        assert metrics.segment_kick_bands(vel, peaks, i0, i1, 0.0) == []         # bad fs
        assert metrics.segment_kick_bands(vel, None, i0, i1, 100.0) == []
        nanned = vel.copy()
        nanned[(i0 + i1) // 2] = np.nan
        assert metrics.segment_kick_bands(nanned, peaks, i0, i1, 100.0) == []

    def test_every_value_is_a_plain_python_number(self):
        """_clean is applied by compute_phases' CALLERS, not inside it, so an np.int64 here
        would reach json.dumps and raise."""
        _vel, _peaks, _i0, _i1, bands = self._bands(n_kicks=5)
        for b in bands:
            for k in ("kick_num", "peak_idx", "start_idx", "end_idx"):
                assert type(b[k]) is int, f"{k} is {type(b[k])}"
            assert type(b["duration_s"]) is float


class TestKickBandsAreEmitted:
    """AC-3/AC-4: compute_phases emits kick_bands beside `boundaries`, so all three
    PhaseContext write sites persist it from one change."""

    def test_kicky_underwater_emits_bands_beside_boundaries(self):
        out = compute_phases(_kick_ctx(n_kicks=5))
        assert len(out["kick_bands"]) == 5
        assert out["kick_bands"][0]["kick_num"] == 0
        assert out["underwater"]["kick_count"]["value"] == len(out["kick_bands"])

    def test_breaststroke_emits_no_bands(self):
        """D9: breaststroke's underwater is the pulldown, so _kick_analysis gates it off
        and the inset must stay single-colour."""
        assert compute_phases(_kick_ctx(n_kicks=6, stroke_type="breaststroke"))["kick_bands"] == []

    def test_unresolvable_underwater_window_emits_no_bands(self, monkeypatch):
        monkeypatch.setattr("phase_metrics.metrics.detect_swim_boundaries",
                            lambda *a, **k: (None, None))
        ctx = _ctx(annotation_phases={"underwater_start_s": 3.0})
        assert compute_phases(ctx)["kick_bands"] == []

    def test_glide_only_underwater_emits_no_bands(self):
        assert compute_phases(_kick_ctx(n_kicks=0))["kick_bands"] == []

    def test_the_whole_phases_object_survives_a_json_round_trip(self):
        """The numpy guard end to end — _clean is applied by api.py AROUND compute_phases'
        return, so a np.int64 inside kick_bands would raise at json.dumps."""
        import json as _json
        out = compute_phases(_kick_ctx(n_kicks=5))
        assert _json.loads(_json.dumps(out["kick_bands"])) == out["kick_bands"]


# ── Phase 75-04: Start-phase metrics ──────────────────────────────────────────

def _start_ctx(fs=100.0, dive=0.5, uw=3.0, **kw):
    """Controlled Start trace: still → foot at `dive` → linear rise to a 3.0 m/s peak at the
    window midpoint → linear glide down to 0.8 at `uw` → steady 1.0. dist is the exact integral
    of vel, so window/glide arithmetic is checkable. Boundaries pinned via annotation (manual)
    unless overridden, so the start window is exact."""
    n = int(12.0 * fs)
    t = np.arange(n) / fs
    vel = np.full(n, 1.0)
    vel[t < dive] = 0.0
    peak_t = (dive + uw) / 2.0
    rise = (t >= dive) & (t < peak_t)
    glide = (t >= peak_t) & (t <= uw)
    vel[rise] = 0.2 + (3.0 - 0.2) * (t[rise] - dive) / (peak_t - dive)
    vel[glide] = 3.0 - (3.0 - 0.8) * (t[glide] - peak_t) / (uw - peak_t)
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])
    defaults = dict(
        t=t, vel=vel, dist=dist, accel=np.gradient(vel, t), fs=fs, stroke_type="freestyle",
        annotation_phases={"dive_start_s": dive, "underwater_start_s": uw,
                           "stroke_start_s": 8.0, "finish_s": 11.5},
    )
    defaults.update(kw)
    return PhaseContext(**defaults)


class TestStartMetrics:
    """AC-1: the ten Start metrics are window/glide arithmetic; AC-3: degrade to None."""

    def _start(self, ctx):
        out = compute_phases(ctx)["start"]
        return out, {k: out[k]["value"] for k in out}

    def test_values_are_window_and_glide_arithmetic(self):
        ctx = _start_ctx()
        _out, v = self._start(ctx)
        fs = ctx.fs
        di, ui = int(round(0.5 * fs)), int(round(3.0 * fs))
        pk = di + int(np.nanargmax(ctx.vel[di:ui]))
        assert v["peak_vel"] == pytest.approx(float(ctx.vel[pk]))
        assert v["time_to_peak_vel"] == pytest.approx(float(ctx.t[pk]) - 0.5)
        assert v["dive_duration"] == pytest.approx(2.5)
        assert v["glide_duration"] == pytest.approx(float(ctx.t[ui] - ctx.t[pk]))
        assert v["glide_distance"] == pytest.approx(float(ctx.dist[ui] - ctx.dist[pk]))
        assert v["glide_avg_speed"] == pytest.approx(
            float(ctx.dist[ui] - ctx.dist[pk]) / float(ctx.t[ui] - ctx.t[pk]))
        assert v["glide_decel"] == pytest.approx(
            (float(ctx.vel[pk]) - float(ctx.vel[ui])) / float(ctx.t[ui] - ctx.t[pk]))
        assert v["glide_decel"] >= 0                       # decelerating in streamline
        assert v["break_into_kick_vel"] == pytest.approx(float(ctx.vel[ui]))
        assert v["max_accel"] is not None and v["max_accel"] > 0

    def test_ten_specs_report_implemented_streamline_planned(self):
        out, _ = self._start(_start_ctx())
        for k in ("peak_vel", "time_to_peak_vel", "max_accel", "dive_duration",
                  "glide_duration", "glide_distance", "glide_avg_speed", "glide_decel",
                  "break_into_kick_vel", "reaction_time"):
            assert out[k]["status"] == "implemented", k
        assert out["streamline_drag"]["status"] == "planned"
        assert out["streamline_drag"]["value"] is None

    def test_missing_dive_start_blanks_window_metrics(self, monkeypatch):
        # No dive_start anywhere: annotation lacks it, no seed, detector returns None.
        monkeypatch.setattr("phase_metrics.metrics.detect_dive_start", lambda *a, **k: None)
        ctx = _start_ctx(annotation_phases={"underwater_start_s": 3.0})
        _out, v = self._start(ctx)
        for k in ("peak_vel", "time_to_peak_vel", "max_accel", "dive_duration",
                  "glide_duration", "glide_distance", "glide_avg_speed", "glide_decel"):
            assert v[k] is None, k
        # break_into_kick_vel needs only underwater_start, so it still resolves
        assert v["break_into_kick_vel"] is not None

    def test_empty_accel_blanks_only_max_accel(self):
        _out, v = self._start(_start_ctx(accel=np.array([])))
        assert v["max_accel"] is None
        assert v["peak_vel"] is not None

    def test_window_narrower_than_floor_blanks_window_metrics(self):
        _out, v = self._start(_start_ctx(
            annotation_phases={"dive_start_s": 3.0, "underwater_start_s": 3.2}))
        for k in ("peak_vel", "dive_duration", "glide_duration", "glide_avg_speed"):
            assert v[k] is None, k

    def test_boundary_past_the_trace_blanks_everything(self):
        _out, v = self._start(_start_ctx(
            annotation_phases={"dive_start_s": 0.5, "underwater_start_s": 999.0}))
        for k in ("peak_vel", "dive_duration", "glide_duration", "break_into_kick_vel"):
            assert v[k] is None, k

    def test_never_raises_on_degenerate_context(self):
        n = 5
        ctx = PhaseContext(t=np.arange(n) / 100.0, vel=np.zeros(n), dist=np.zeros(n),
                           accel=np.array([]), fs=100.0, stroke_type=None,
                           annotation_phases={"dive_start_s": 0.0, "underwater_start_s": 0.02})
        _out, v = self._start(ctx)   # must not raise
        assert v["glide_distance"] is None


class TestReactionTime:
    """AC-2: reaction_time derives only from a stored GO time, on the session clock; the
    first movement is motion onset (the jump), not dive_start."""

    def _rt(self, ctx):
        return compute_phases(ctx)["start"]["reaction_time"]["value"]

    def test_none_without_go_signal(self):
        assert self._rt(_start_ctx()) is None

    def test_derived_from_go_signal(self):
        ctx = _start_ctx()
        onset = pm.metrics.detect_phases(ctx.t, ctx.vel)["baseline_end"]
        ctx.go_signal_s = float(ctx.t[onset]) - 0.4
        assert self._rt(ctx) == pytest.approx(0.4, abs=1e-6)

    def test_go_after_first_movement_is_none(self):
        ctx = _start_ctx()
        onset = pm.metrics.detect_phases(ctx.t, ctx.vel)["baseline_end"]
        ctx.go_signal_s = float(ctx.t[onset]) + 1.0
        assert self._rt(ctx) is None


# ── Phase 75-06: Swim + Whole-race metrics ────────────────────────────────────

def _race_ctx(fs=100.0, dive=0.5, uw=2.0, brk=5.0, fin=15.0, dur=17.0, **kw):
    """A full four-boundary race trace with pinned (manual) boundaries.

    still → launch surge peaking at 3.0 → glide to 1.6 → underwater 1.8 with kick ripple →
    surface swim at 1.2 mean with a clean 1 Hz, 0.3 amplitude stroke oscillation → stopped.
    dist is the exact integral of vel, so window and split arithmetic is checkable by hand.
    Distances land at roughly 2.6 m / 5.4 m / 12 m per phase (~20 m total), which is
    deliberately short of 25 m so the un-reached-split branch is exercised too.
    """
    n = int(dur * fs)
    t = np.arange(n) / fs
    vel = np.zeros(n)
    peak_t = (dive + uw) / 2.0
    rise = (t >= dive) & (t < peak_t)
    glide = (t >= peak_t) & (t < uw)
    vel[rise] = 0.2 + (3.0 - 0.2) * (t[rise] - dive) / (peak_t - dive)
    vel[glide] = 3.0 - (3.0 - 1.6) * (t[glide] - peak_t) / (uw - peak_t)
    under = (t >= uw) & (t < brk)
    vel[under] = 1.8 + 0.15 * np.sin(2 * np.pi * 2.0 * (t[under] - uw))
    swim = (t >= brk) & (t <= fin)
    vel[swim] = 1.2 + 0.3 * np.sin(2 * np.pi * 1.0 * (t[swim] - brk))
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])
    defaults = dict(
        t=t, vel=vel, dist=dist, accel=np.gradient(vel, t), fs=fs, stroke_type="freestyle",
        annotation_phases={"dive_start_s": dive, "underwater_start_s": uw,
                           "stroke_start_s": brk, "finish_s": fin},
    )
    defaults.update(kw)
    return PhaseContext(**defaults)


def _even_cycles(fs=100.0, brk=5.0, n_cycles=10, period_s=1.0, dps=1.2):
    """Uniform cycles tiling the swim window — the degenerate case for coupling (no variance
    in either series), and the clean case for dead-spot timing."""
    return [
        {"cycle_num": i,
         "start_idx": int((brk + i * period_s) * fs),
         "end_idx": int((brk + (i + 1) * period_s) * fs),
         "duration_s": period_s,
         "dist_m": dps}
        for i in range(n_cycles)
    ]


class TestSwimWindowMetrics:
    """AC-1: the Layer-A swim metrics are window arithmetic over [stroke_start, finish]."""

    def _swim(self, ctx):
        out = compute_phases(ctx)["swim"]
        return {k: out[k]["value"] for k in out}

    def test_ivv_is_std_over_mean_of_the_swim_window(self):
        v = self._swim(_race_ctx())
        # A 0.3-amplitude sinusoid about 1.2 has std = 0.3/sqrt(2).
        assert v["ivv"] == pytest.approx((0.3 / np.sqrt(2)) / 1.2, rel=0.05)

    def test_breakout_vel_averages_the_first_half_second(self):
        v = self._swim(_race_ctx())
        # sin is positive across the whole first half-period, so the mean sits above 1.2.
        assert 1.2 < v["breakout_vel"] < 1.5

    def test_breakout_vel_loss_is_underwater_speed_minus_the_post_breakout_trough(self):
        v = self._swim(_race_ctx())
        assert v["breakout_vel_loss"] == pytest.approx(1.8 - 0.9, abs=0.05)

    def test_breakout_vs_steady_above_one_when_breakout_outruns_the_swim(self):
        v = self._swim(_race_ctx())
        assert v["breakout_vs_steady"] > 1.0

    def test_accel_asymmetry_balanced_on_a_symmetric_oscillation(self):
        v = self._swim(_race_ctx())
        assert v["accel_asymmetry"] == pytest.approx(1.0, rel=0.1)

    def test_accel_metrics_are_none_without_an_acceleration_profile(self):
        """Pre-Phase-64 sessions carry no acceleration_profile — an empty array, not a crash."""
        ctx = _race_ctx(accel=np.array([]))
        assert self._swim(ctx)["accel_asymmetry"] is None
        assert compute_phases(ctx)["whole"]["jerk_smoothness"]["value"] is None

    def test_unresolvable_swim_window_degrades_to_none(self):
        n = 200
        ctx = PhaseContext(t=np.arange(n) / 100.0, vel=np.zeros(n), dist=np.zeros(n),
                           accel=np.zeros(n), fs=100.0, stroke_type=None,
                           annotation_phases={"stroke_start_s": None, "finish_s": None})
        v = self._swim(ctx)
        for key in ("ivv", "breakout_vel", "breakout_vs_steady"):
            assert v[key] is None


def _split_by_hand(ctx, meters):
    """Independent reimplementation of one split: mean velocity over the 5 m segment ending at
    `meters`, anchored at dive_start. Checks the compute fn against arithmetic, not itself."""
    i_start = int(round(ctx.annotation_phases["dive_start_s"] * ctx.fs))
    # Search from dive_start, not from t=0. The trace is motionless before the dive, so a
    # 0 m target would otherwise match at index 0 and stretch the first segment backwards
    # across the still water.
    rel = np.asarray(ctx.dist[i_start:], dtype=float) - float(ctx.dist[i_start])
    i_a = int(np.nonzero(rel >= meters - 5.0)[0][0]) + i_start
    i_b = int(np.nonzero(rel >= meters)[0][0]) + i_start
    return (ctx.dist[i_b] - ctx.dist[i_a]) / (ctx.t[i_b] - ctx.t[i_a])


def _remainder_by_hand(ctx):
    """Independent reimplementation of splits_remainder: mean velocity from the first sample at
    20 m past dive_start to the LAST sample of the finish-clamped window. Same by-hand style as
    _split_by_hand, checking the compute fn against arithmetic, not itself."""
    i_start = int(round(ctx.annotation_phases["dive_start_s"] * ctx.fs))
    fin_idx = int(round(ctx.annotation_phases["finish_s"] * ctx.fs))
    i_b = min(len(ctx.dist) - 1, fin_idx)
    rel = np.asarray(ctx.dist[i_start:i_b + 1], dtype=float) - float(ctx.dist[i_start])
    i_a = int(np.nonzero(rel >= 20.0)[0][0]) + i_start
    return (ctx.dist[i_b] - ctx.dist[i_a]) / (ctx.t[i_b] - ctx.t[i_a])


class TestSplits:
    """AC-1: one scalar spec per 5 m segment (75-06 D7), None past the distance swum."""

    def _splits(self, ctx):
        out = compute_phases(ctx)["swim"]
        return {k: out[k]["value"] for k in out if k.startswith("splits_")}

    def test_reached_splits_are_segment_mean_velocities(self):
        s = self._splits(_race_ctx())
        for key in ("splits_5m", "splits_10m", "splits_15m"):
            assert s[key] is not None and 0.5 < s[key] < 4.0

    def test_split_tracks_the_segment_it_covers(self):
        """This FIXTURE has a 3.0 m/s launch inside the first 5 m, so its opening split is the
        fastest. That ordering is a property of the fixture, not a law: on real tethered trials
        the first 5 m includes the acceleration from a standstill and often reads SLOWER than
        the later splits. Only the per-segment arithmetic is asserted here."""
        ctx = _race_ctx()
        s = self._splits(ctx)
        assert s["splits_5m"] == pytest.approx(_split_by_hand(ctx, 5), rel=0.02)
        assert s["splits_15m"] == pytest.approx(_split_by_hand(ctx, 15), rel=0.02)

    def test_retired_split_key_is_gone(self):
        """splits_25m left the registry (88-01 D2/D3) — structurally unfillable on a 25-yard
        tether-limited lap, replaced by splits_remainder."""
        assert "splits_25m" not in self._splits(_race_ctx())

    def test_remainder_covers_twenty_metres_to_the_finish(self):
        """Extend the default fixture's swim phase well past 20 m (~32 m total, CONTEXT-probed
        above) and check the chord matches hand arithmetic at the same two indices."""
        ctx = _race_ctx(fin=25.0, dur=27.0)
        s = self._splits(ctx)
        assert s["splits_remainder"] is not None and 0.5 < s["splits_remainder"] < 4.0
        assert s["splits_remainder"] == pytest.approx(_remainder_by_hand(ctx), rel=1e-9)

    def test_remainder_is_none_when_the_tail_is_shorter_than_the_floor(self):
        """Crosses 20 m and stops 0.4 m later — arithmetically fine, under _MIN_REMAINDER_M."""
        fs = 100.0
        n = 1021
        t = np.arange(n) / fs
        vel = np.full(n, 2.0)
        dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])  # dist[-1] == 20.4
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.zeros(n), fs=fs,
                            stroke_type="freestyle",
                            annotation_phases={"dive_start_s": 0.0, "finish_s": float(t[-1])})
        assert dist[-1] - 20.0 < pm._MIN_REMAINDER_M
        assert self._splits(ctx)["splits_remainder"] is None

    def test_remainder_is_none_when_twenty_metres_is_never_reached(self):
        fs = 100.0
        n = 751
        t = np.arange(n) / fs
        vel = np.full(n, 2.0)
        dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs)])  # dist[-1] == 15.0
        ctx = PhaseContext(t=t, vel=vel, dist=dist, accel=np.zeros(n), fs=fs,
                            stroke_type="freestyle",
                            annotation_phases={"dive_start_s": 0.0, "finish_s": float(t[-1])})
        assert dist[-1] < 20.0
        assert self._splits(ctx)["splits_remainder"] is None

    def test_every_split_is_none_when_dive_start_is_unresolvable(self):
        n = 300
        ctx = PhaseContext(t=np.arange(n) / 100.0, vel=np.zeros(n), dist=np.zeros(n),
                           accel=np.zeros(n), fs=100.0, stroke_type=None,
                           annotation_phases={"dive_start_s": None})
        assert all(v is None for v in self._splits(ctx).values())


class TestPerCycleSwimMetrics:
    """AC-2: the two Layer-B metrics read ctx.cycles and report their provenance."""

    def test_dead_spot_timing_finds_the_slowest_instant_in_the_cycle(self):
        ctx = _race_ctx(cycles=_even_cycles())
        out = compute_phases(ctx)["swim"]
        # vel = 1.2 + 0.3*sin(2*pi*(t-brk)) bottoms three-quarters through each cycle.
        assert out["dead_spot_timing"]["value"] == pytest.approx(0.75, abs=0.02)

    def test_coupling_is_none_without_variance_in_both_series(self):
        """Identical cycles make Pearson r undefined — that is None, never 0.0."""
        ctx = _race_ctx(cycles=_even_cycles())
        assert compute_phases(ctx)["swim"]["sr_dps_coupling"]["value"] is None

    def test_coupling_is_negative_when_tempo_is_bought_with_distance(self):
        cycles = _even_cycles()
        for i, c in enumerate(cycles):
            c["duration_s"] = 0.8 + 0.05 * i     # slowing tempo
            c["dist_m"] = 1.0 + 0.08 * i         # longer strokes
        ctx = _race_ctx(cycles=cycles)
        assert compute_phases(ctx)["swim"]["sr_dps_coupling"]["value"] < -0.9

    def test_too_few_cycles_gives_none(self):
        ctx = _race_ctx(cycles=_even_cycles(n_cycles=2))
        assert compute_phases(ctx)["swim"]["sr_dps_coupling"]["value"] is None

    def test_cycles_outside_the_swim_window_are_ignored(self):
        """An underwater-era cycle must not leak into a swim-phase metric."""
        cycles = _even_cycles() + [
            {"cycle_num": 99, "start_idx": 250, "end_idx": 350,
             "duration_s": 1.0, "dist_m": 1.8},
        ]
        assert pm._swim_cycles(_race_ctx(cycles=cycles)) == pm._swim_cycles(
            _race_ctx(cycles=_even_cycles()))

    def test_missing_cycles_degrade_to_none(self):
        out = compute_phases(_race_ctx(cycles=None))["swim"]
        assert out["dead_spot_timing"]["value"] is None
        assert out["sr_dps_coupling"]["value"] is None


class TestProvisionalFlag:
    """AC-2: provisional says whether the cycles were the coach's or the segmenter's."""

    def test_auto_cycles_are_flagged_provisional(self):
        out = compute_phases(_race_ctx(cycles=_even_cycles(),
                                       segmentation_reliable=False))["swim"]
        assert out["dead_spot_timing"]["provisional"] is True
        assert out["sr_dps_coupling"]["provisional"] is True

    def test_annotated_cycles_are_not_provisional(self):
        out = compute_phases(_race_ctx(cycles=_even_cycles(),
                                       segmentation_reliable=True))["swim"]
        assert out["dead_spot_timing"]["provisional"] is False

    def test_window_metrics_are_never_provisional(self):
        """Only needs_cycles specs can be provisional — a window metric never touches cycles."""
        phases = compute_phases(_race_ctx(segmentation_reliable=False))
        for phase in PHASES:
            for key, entry in phases[phase].items():
                if key not in ("dead_spot_timing", "sr_dps_coupling"):
                    assert entry["provisional"] is False, key

    def test_every_emitted_metric_carries_the_flag(self):
        phases = compute_phases(_race_ctx())
        for phase in PHASES:
            for key, entry in phases[phase].items():
                assert "provisional" in entry, key


class TestWholeRaceMetrics:
    """AC-1: cross-phase reductions over the four boundaries."""

    def _whole(self, ctx):
        out = compute_phases(ctx)["whole"]
        return {k: out[k]["value"] for k in out}

    def test_time_budget_shares_sum_to_one_hundred_percent(self):
        v = self._whole(_race_ctx())
        total = sum(v[f"phase_time_budget_{p}"] for p in ("start", "underwater", "swim"))
        assert total == pytest.approx(100.0, abs=0.5)

    def test_time_budget_matches_the_pinned_boundaries(self):
        v = self._whole(_race_ctx())
        # start 1.5 s, underwater 3.0 s, swim 10.0 s of a 14.5 s race.
        assert v["phase_time_budget_start"] == pytest.approx(1.5 / 14.5 * 100, abs=0.5)
        assert v["phase_time_budget_swim"] == pytest.approx(10.0 / 14.5 * 100, abs=0.5)

    def test_distance_budget_shares_sum_to_one_hundred_percent(self):
        v = self._whole(_race_ctx())
        total = sum(v[f"phase_dist_budget_{p}"] for p in ("start", "underwater", "swim"))
        assert total == pytest.approx(100.0, abs=0.5)

    def test_velocity_envelope_decays_across_the_race(self):
        v = self._whole(_race_ctx())
        assert v["vel_envelope_start"] == pytest.approx(3.0, abs=0.05)
        assert v["vel_envelope_start"] > v["vel_envelope_underwater"] > v["vel_envelope_swim"]
        assert v["vel_envelope_overall"] == pytest.approx(v["vel_envelope_start"], abs=0.05)

    def test_jerk_smoothness_is_a_positive_rate(self):
        v = self._whole(_race_ctx())
        assert v["jerk_smoothness"] is not None and v["jerk_smoothness"] > 0

    def test_whole_metrics_degrade_to_none_without_boundaries(self):
        n = 200
        ctx = PhaseContext(t=np.arange(n) / 100.0, vel=np.zeros(n), dist=np.zeros(n),
                           accel=np.zeros(n), fs=100.0, stroke_type=None,
                           annotation_phases={"dive_start_s": None, "finish_s": None})
        v = self._whole(ctx)
        assert v["phase_time_budget_start"] is None
        assert v["vel_envelope_overall"] is None


class TestSeventyFiveSixRegistry:
    """AC-1: the registry restructure — vectors expanded, breathing_dip gone, all implemented."""

    KEYS = {spec.key for spec in REGISTRY}

    def test_replaced_vector_keys_are_gone(self):
        """These were single list-valued specs; D7 replaced them with per-element scalars so
        the report card's per-key baseline lookup stays aligned across a session's history."""
        for key in ("splits", "phase_time_budget", "phase_dist_budget", "vel_envelope"):
            assert key not in self.KEYS

    def test_breathing_dip_is_removed_not_reserved(self):
        """Unbuildable, not deferred: a 1-D axial encoder cannot see which strokes were breaths."""
        assert "breathing_dip" not in self.KEYS

    def test_per_element_keys_are_registered(self):
        expected = (
            {f"splits_{d}m" for d in (5, 10, 15, 20)} | {"splits_remainder"}
            | {f"phase_time_budget_{p}" for p in ("start", "underwater", "swim")}
            | {f"phase_dist_budget_{p}" for p in ("start", "underwater", "swim")}
            | {f"vel_envelope_{p}" for p in ("start", "underwater", "swim", "overall")}
        )
        assert expected <= self.KEYS

    def test_every_swim_and_whole_spec_is_implemented(self):
        for spec in REGISTRY:
            if spec.phase in ("swim", "whole"):
                assert spec.status == "implemented", spec.key
                assert spec.compute is not None, spec.key

    def test_only_the_two_layer_b_specs_need_cycles(self):
        needs = {spec.key for spec in REGISTRY if spec.needs_cycles}
        assert needs == {"sr_dps_coupling", "dead_spot_timing"}

    def test_streamline_drag_is_the_only_remaining_planned_spec(self):
        planned = {spec.key for spec in REGISTRY if spec.status == "planned"}
        assert planned == {"streamline_drag"}

    def test_schema_version_bumped_for_the_kick_bands_field(self):
        assert SCHEMA_VERSION == 4
        assert compute_phases(_race_ctx())["schema_version"] == 4


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
