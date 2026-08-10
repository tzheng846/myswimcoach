"""Unit tests for metrics.compute_session_metrics."""
import numpy as np
import pytest

import metrics as m

# ── Helpers ───────────────────────────────────────────────────────────────────

EXPECTED_SESSION_KEYS = [
    "lap_time_s",
    "total_dist_m",
    "stroke_count",
    "stroke_rate_spm",
    "mean_vel_ms",
    "max_vel_ms",
    "mean_dps_m",
    "fatigue_index_pct",
    "total_cycles_raw",
    "outlier_cycle_count",
    "implausible_cycle_count",
    "kick_metrics_reliable",
    "segmentation_reliable",
]

EXPECTED_TOP_KEYS = ["session", "cycles", "initial_phase"]


def _sine_wave_inputs(duration_s=30.0, fs_hz=100.0):
    """Return (t, vel, dist) with realistic breaststroke-like sinusoidal velocity."""
    n = int(duration_s * fs_hz)
    t = np.linspace(0.0, duration_s, n)
    vel = 0.8 + 0.4 * np.sin(2 * np.pi * 0.5 * t)
    vel = np.maximum(vel, 0.05)
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / fs_hz)])
    return t, vel, dist


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestComputeSessionMetricsShape:
    """Shape and key-presence tests — no crash, all expected keys returned."""

    def test_top_level_keys_present(self):
        t, vel, dist = _sine_wave_inputs()
        result = m.compute_session_metrics(t, vel, dist)
        for key in EXPECTED_TOP_KEYS:
            assert key in result, f"Missing top-level key: {key}"

    def test_session_standard_keys_present(self):
        t, vel, dist = _sine_wave_inputs()
        result = m.compute_session_metrics(t, vel, dist)
        session = result["session"]
        for key in EXPECTED_SESSION_KEYS:
            assert key in session, f"Missing session key: {key}"

    def test_cycles_is_list(self):
        t, vel, dist = _sine_wave_inputs()
        result = m.compute_session_metrics(t, vel, dist)
        assert isinstance(result["cycles"], list)

    def test_quality_key_types(self):
        t, vel, dist = _sine_wave_inputs()
        s = m.compute_session_metrics(t, vel, dist)["session"]
        assert isinstance(s["total_cycles_raw"], int)
        assert isinstance(s["outlier_cycle_count"], int)
        assert isinstance(s["implausible_cycle_count"], int)
        assert isinstance(s["kick_metrics_reliable"], bool)

    def test_kick_metrics_reliable_always_false(self):
        """LP filter limitation — must always be False regardless of input."""
        t, vel, dist = _sine_wave_inputs()
        s = m.compute_session_metrics(t, vel, dist)["session"]
        assert s["kick_metrics_reliable"] is False

    def test_segmentation_reliable_always_false(self):
        """Wavelet ridge shipped as placeholder (Phase 16-05) — always False
        until the rate-accuracy/boundary tuning pass; see 16-04-SUMMARY."""
        t, vel, dist = _sine_wave_inputs()
        s = m.compute_session_metrics(t, vel, dist)["session"]
        assert s["segmentation_reliable"] is False

    def test_quality_counts_non_negative(self):
        t, vel, dist = _sine_wave_inputs()
        s = m.compute_session_metrics(t, vel, dist)["session"]
        assert s["total_cycles_raw"] >= 0
        assert s["outlier_cycle_count"] >= 0
        assert s["implausible_cycle_count"] >= 0

    def test_outlier_count_leq_total(self):
        """Outliers can't exceed total cycle count."""
        t, vel, dist = _sine_wave_inputs()
        s = m.compute_session_metrics(t, vel, dist)["session"]
        assert s["outlier_cycle_count"] <= s["total_cycles_raw"]
        assert s["implausible_cycle_count"] <= s["total_cycles_raw"]


class TestRealSession:
    """Tests using processed/breaststroke_sample.csv — real recorded swim data."""

    def test_no_crash(self, real_session):
        t, vel, dist = real_session
        result = m.compute_session_metrics(t, vel, dist)
        assert "session" in result

    def test_all_session_keys_present(self, real_session):
        t, vel, dist = real_session
        s = m.compute_session_metrics(t, vel, dist)["session"]
        for key in EXPECTED_SESSION_KEYS:
            assert key in s, f"Missing session key: {key}"

    def test_detects_strokes(self, real_session):
        """Real session should produce at least 1 detected stroke cycle."""
        t, vel, dist = real_session
        s = m.compute_session_metrics(t, vel, dist)["session"]
        assert s["stroke_count"] >= 1, "Expected at least 1 stroke in real session"
        assert s["total_cycles_raw"] >= 1

    def test_plausible_stroke_rate(self, real_session):
        """Breaststroke SPM should be in a human-possible range (10–60)."""
        t, vel, dist = real_session
        s = m.compute_session_metrics(t, vel, dist)["session"]
        if s["stroke_count"] >= 2:  # need ≥2 cycles for a meaningful rate
            assert 10 <= s["stroke_rate_spm"] <= 60, (
                f"stroke_rate_spm={s['stroke_rate_spm']:.1f} outside plausible range"
            )

    def test_kick_metrics_reliable_false(self, real_session):
        t, vel, dist = real_session
        s = m.compute_session_metrics(t, vel, dist)["session"]
        assert s["kick_metrics_reliable"] is False


class TestComputeSessionMetricsEdgeCases:
    """Edge cases — must not raise exceptions."""

    def test_flat_signal_no_crash(self):
        """Near-zero velocity (no strokes) — should return without error."""
        t = np.linspace(0.0, 10.0, 1000)
        vel = np.full_like(t, 0.01)
        dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / 100.0)])
        result = m.compute_session_metrics(t, vel, dist)
        s = result["session"]
        assert isinstance(s["total_cycles_raw"], int)
        assert s["outlier_cycle_count"] == 0
        assert s["kick_metrics_reliable"] is False

    def test_short_signal_no_crash(self):
        """Very short signal (5 seconds) — pipeline must not raise."""
        t = np.linspace(0.0, 5.0, 500)
        vel = 0.8 + 0.3 * np.sin(2 * np.pi * 0.5 * t)
        vel = np.maximum(vel, 0.05)
        dist = np.concatenate([[0.0], np.cumsum(vel[:-1] / 100.0)])
        result = m.compute_session_metrics(t, vel, dist)
        assert "session" in result

    def test_head_waist_offset_accepted(self):
        """head_waist_m kwarg should be accepted without error."""
        t, vel, dist = _sine_wave_inputs()
        result = m.compute_session_metrics(t, vel, dist, head_waist_m=0.35)
        assert "session" in result


# ── Phase 47: manual annotation overrides ─────────────────────────────────────

class TestManualOverrides:
    """compute_session_metrics(manual=...) — human-annotation boundary injection."""

    def test_no_manual_identical_to_default(self):
        """manual=None and omitted must produce identical results."""
        t, vel, dist = _sine_wave_inputs()
        base = m.compute_session_metrics(t, vel, dist)
        with_none = m.compute_session_metrics(t, vel, dist, manual=None)
        assert base["session"] == with_none["session"]
        assert len(base["cycles"]) == len(with_none["cycles"])

    def test_manual_cycle_bounds_used_verbatim(self):
        t, vel, dist = _sine_wave_inputs()
        bounds = [(500, 700), (700, 910), (910, 1100)]
        result = m.compute_session_metrics(t, vel, dist, manual={"cycle_bounds": bounds})
        got = [(c["start_idx"], c["end_idx"]) for c in result["cycles"]]
        assert got == bounds
        # Downstream per-cycle metrics computed on the injected cycles
        for c in result["cycles"]:
            assert np.isfinite(c["duration_s"]) and c["duration_s"] > 0
            assert np.isfinite(c["arm_peak_vel"])
        assert result["session"]["total_cycles_raw"] == 3

    def test_manual_bounds_flip_segmentation_reliable(self):
        t, vel, dist = _sine_wave_inputs()
        result = m.compute_session_metrics(
            t, vel, dist, manual={"cycle_bounds": [(500, 700), (700, 910)]})
        assert result["session"]["segmentation_reliable"] is True
        auto = m.compute_session_metrics(t, vel, dist)
        assert auto["session"]["segmentation_reliable"] is False

    def test_manual_window_overrides(self):
        t, vel, dist = _sine_wave_inputs()
        result = m.compute_session_metrics(
            t, vel, dist,
            manual={"baseline_end_idx": 120, "swim_end_idx": 2500,
                    "cycle_bounds": [(500, 700)]})
        assert result["session"]["baseline_end_s"] == pytest.approx(t[120], abs=0.02)

    def test_degenerate_bounds_skipped(self):
        t, vel, dist = _sine_wave_inputs()
        result = m.compute_session_metrics(
            t, vel, dist, manual={"cycle_bounds": [(500, 501), (600, 800)]})
        assert len(result["cycles"]) == 1
        assert result["cycles"][0]["start_idx"] == 600


class TestAnnotationToOverrides:
    """annotations.annotation_to_overrides — times → indices mapping."""

    def test_full_annotation_maps(self):
        import annotations as a
        ann = {
            "phases": {"dive_start_s": 1.2, "stroke_start_s": 4.5, "finish_s": 11.0},
            "stroke_marks_s": [5.0, 7.0, 9.1],
        }
        out = a.annotation_to_overrides(ann, 3000)
        assert out["baseline_end_idx"] == 120
        assert out["ip_end_idx"] == 450
        assert out["swim_end_idx"] == 1101  # exclusive: finish idx + 1
        # marks + finish → 4 boundaries → 3 cycles
        assert out["cycle_bounds"] == [(500, 700), (700, 910), (910, 1100)]

    def test_fewer_than_two_boundaries_no_cycles(self):
        import annotations as a
        assert "cycle_bounds" not in a.annotation_to_overrides(
            {"stroke_marks_s": [5.0]}, 3000)
        assert "cycle_bounds" not in a.annotation_to_overrides(
            {"stroke_marks_s": []}, 3000)

    def test_clamping_and_malformed(self):
        import annotations as a
        out = a.annotation_to_overrides(
            {"phases": {"finish_s": 999.0}, "stroke_marks_s": [5.0, "junk", 7.0]}, 3000)
        assert out["swim_end_idx"] == 3000  # clamped to n_samples
        assert out["cycle_bounds"][0] == (500, 700)
        assert a.annotation_to_overrides(None, 3000) == {}
        assert a.annotation_to_overrides({}, 0) == {}


class TestSegmenterDispatch:
    """Per-stroke segmenter registry (Phase 59-02, populated 59-03, completed 59-05).

    ⚠ RE-BASELINED TWICE, BOTH TIMES DELIBERATELY. 59-02 shipped the registry EMPTY and
    these tests pinned that inertness; 59-03 registered free/back with a pairing wrapper;
    59-05 registered fly/breast with the LEARNED detector. Every assertion has been
    TIGHTENED to the new truth each time, never loosened to make the suite green.
    """

    def test_every_stroke_is_registered_and_unknowns_take_the_default(self):
        """All four strokes route somewhere specific as of 59-05.

        Only genuinely unknown values fall through to the bare wavelet — including the
        mobile picker's "im" and "udk", which are not strokes this pipeline models.
        """
        for stroke in ("im", "udk", "not-a-stroke", "", None):
            assert m.resolve_segmenter(stroke) is m.segment_cycles_wavelet, stroke
        for stroke in ("freestyle", "backstroke", "butterfly", "breaststroke"):
            assert m.resolve_segmenter(stroke) is not m.segment_cycles_wavelet, stroke

    def test_registry_holds_exactly_the_four_strokes(self):
        """A stroke appearing here by accident is the failure worth catching."""
        assert set(m.SEGMENTER_BY_STROKE) == {
            "freestyle", "backstroke", "butterfly", "breaststroke"}

    def test_alternating_strokes_pair_wavelet_boundaries(self, real_session):
        """Free/back keep the wavelet and halve its boundary count.

        59-04 measured both challengers WORSE than the wavelet on freestyle cycle
        regularity (L1 0.121, peakpick 0.246 vs 0.069), so freestyle deliberately did NOT
        move in 59-05.
        """
        t, vel, dist = real_session
        base_n = m.compute_session_metrics(t, vel, dist)["session"]["stroke_count"]
        for stroke in ("freestyle", "backstroke"):
            n = m.compute_session_metrics(
                t, vel, dist, stroke_type=stroke)["session"]["stroke_count"]
            assert n < base_n, f"{stroke} should yield fewer, longer cycles"
            assert abs(n - base_n / 2) <= 1, f"{stroke}: {n} vs base {base_n}"

    def test_fly_and_breast_use_the_learned_detector(self, real_session):
        """Butterfly/breaststroke moved OFF the wavelet in 59-05.

        ⚠ They are paired k=2 despite being physiologically ONE arm entry per cycle. That
        is not a bug: the detector emits ~2.02 events per cycle consistently, so every 2nd
        lands one boundary per cycle at a stable phase. `k` is a property of the DETECTOR.
        """
        t, vel, dist = real_session
        base = m.compute_session_metrics(t, vel, dist)
        for stroke in ("butterfly", "breaststroke"):
            out = m.compute_session_metrics(t, vel, dist, stroke_type=stroke)
            assert out["cycles"] != base["cycles"], f"{stroke} must not equal the wavelet"

    def test_learned_inference_needs_no_sklearn(self):
        """AC-3: a 5-parameter model must not drag a dependency onto the Railway path."""
        import inspect
        src = inspect.getsource(m)
        assert "sklearn" not in src.replace("NO sklearn", "").replace(
            "sklearn stays in tools/", "").replace("reproduce sklearn's", "")
        assert m._LEARNED_COEF.shape == (5,)

    def test_a_registered_override_is_actually_called(self, monkeypatch, real_session):
        """Proves the seam reaches the segmentation slice.

        Without this the registry could be wired to nothing and every other test here
        would still pass.
        """
        t, vel, dist = real_session
        seen = {}

        def sentinel(t_seg, vel_seg):
            seen["n"] = len(vel_seg)
            return [
                {"cycle_num": 0, "peak_idx": 10, "start_idx": 0, "end_idx": 200},
                {"cycle_num": 1, "peak_idx": 210, "start_idx": 200, "end_idx": 400},
            ]

        monkeypatch.setitem(m.SEGMENTER_BY_STROKE, "butterfly", sentinel)
        out = m.compute_session_metrics(t, vel, dist, stroke_type="butterfly")

        assert "n" in seen, "the registered segmenter was never called"
        assert 0 < seen["n"] <= len(vel), "it did not receive the segmentation slice"
        assert out["session"]["stroke_count"] <= 2
        # An UNREGISTERED value still takes the default. All four strokes are registered
        # as of 59-05, so this must use something outside the stroke set entirely.
        assert m.resolve_segmenter("im") is m.segment_cycles_wavelet


class TestCycleRegularityGate:
    """Cycles must be REGULAR, not merely well-placed (Phase 59-05).

    ⚠ THIS EXISTS BECAUSE F1 ALONE PASSED A WRONG CANDIDATE. In 59-04 `peakpick` scored
    butterfly F1 0.524 against the wavelet's 0.317 and would have shipped on that basis.
    Its cycles alternated long/short (alternation 0.276 vs a human 0.056) because it emits
    an UNSTABLE ~2.5 events per cycle, so pairing drifted through phases.

    A segmenter can place boundaries well and still emit meaningless cycles. That poisons
    cv_isi, mean_dps_m and mean_coast_fraction while leaving stroke_rate_spm looking fine,
    because taking every k-th event preserves the MEAN interval even when every individual
    cycle is wrong. Rate is blind to this class of error; these statistics are not.
    """

    @staticmethod
    def _interval_stats(cycles, fs):
        b = [c["start_idx"] for c in cycles] + [cycles[-1]["end_idx"]]
        iv = np.diff(b) / fs
        iv = iv[iv > 0.15]
        if len(iv) < 3:
            return None
        cv = float(np.std(iv) / np.mean(iv))
        alt = float(np.mean([abs(iv[i + 1] / iv[i] - 1) for i in range(len(iv) - 1)]))
        return cv, alt

    @pytest.mark.parametrize("stroke", ["freestyle", "butterfly", "breaststroke"])
    def test_registered_cycles_are_no_less_regular_than_the_wavelet(
            self, real_session, stroke):
        t, vel, dist = real_session
        fs = m._compute_fs(t)
        seg = m.resolve_segmenter(stroke)(t, vel)
        base = m.segment_cycles_wavelet(t, vel)
        assert seg and base, "both should segment the fixture"
        got, inc = self._interval_stats(seg, fs), self._interval_stats(base, fs)
        assert got and inc
        # Generous margin: this is a guard against phase-drifting cycles, not a tuning knob.
        assert got[1] <= inc[1] + 0.15, (
            f"{stroke}: alternation {got[1]:.3f} vs incumbent {inc[1]:.3f} — "
            "cycles are drifting through phases, which is the peakpick failure mode")
