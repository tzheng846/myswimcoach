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
