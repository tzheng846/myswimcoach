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


# ── Acceleration extraction (Phase 64-02 → Savitzky-Golay, Phase 66) ────────────

def test_acceleration_from_velocity_savgol():
    """Phase 66: acceleration is a Savitzky-Golay first derivative at the full sample rate. It
    differentiates a line EXACTLY (constant acceleration) and tracks a known sinusoid's analytic
    acceleration far more accurately than the old decimate->gradient->linear-interp reconstruction —
    whose ~5 Hz bandwidth blunted peaks (~30%) and whose linear interp left visible facets. This
    guards the DISPLAY signal only; no metric consumes acceleration."""
    import numpy as np
    import vel_acc_extraction as vae

    fs = 89.5
    n = int(fs * 20)
    t = np.arange(n) / fs

    # AC-2 — SG (polyorder >= 1) differentiates a linear velocity EXACTLY: constant acceleration.
    ramp = 0.75 * t  # dv/dt == 0.75 everywhere
    accel_ramp = vae.acceleration_from_velocity(ramp, fs)
    assert accel_ramp.shape == (n,)
    assert np.all(np.isfinite(accel_ramp))
    assert np.allclose(accel_ramp, 0.75, atol=1e-6)

    # AC-1 — accuracy: a clean stroke-like sinusoid has a known analytic acceleration. SG tracks it;
    # the old reconstruction does not (over-smoothed + faceted). Compare interior RMS error.
    A, f = 0.6, 1.1
    vel = 1.0 + A * np.sin(2 * np.pi * f * t)
    true = A * 2 * np.pi * f * np.cos(2 * np.pi * f * t)

    sg = vae.acceleration_from_velocity(vel, fs)
    vd, td, fsd = vae.decimate_signal(vel, fs, 5.0)  # the old 5 Hz reconstruction, for contrast
    old = np.interp(t, td, np.gradient(vd, 1.0 / fsd))

    core = slice(100, -100)  # ignore edge transients
    rms = lambda x: float(np.sqrt(np.mean((x[core] - true[core]) ** 2)))
    assert rms(sg) < rms(old)  # SG is markedly closer to the analytic truth
    assert rms(sg) < 0.05 * rms(old)  # ...by well over an order of magnitude

    # Peak amplitude — the "definition too low" the old 5 Hz path caused by crushing peaks ~30%.
    assert np.max(sg[core]) > 0.95 * float(np.max(true[core]))


def test_acceleration_window_is_stroke_dependent():
    """Phase 66: free/back use a WIDER Savitzky-Golay window than fly/breast (their alternating arms
    + flutter kick put more high-frequency energy in velocity), so on the SAME noisy velocity the
    freestyle acceleration is smoother — lower total variation — than the butterfly one. An unknown
    stroke falls back to the sharp default (identical to butterfly here)."""
    import numpy as np
    import vel_acc_extraction as vae

    rng = np.random.default_rng(1)
    fs = 89.5
    n = int(fs * 20)
    t = np.arange(n) / fs
    # stroke oscillation + a faster kick ripple + a little noise — the free-vs-fly contrast in miniature
    vel = (1.2 + 0.5 * np.sin(2 * np.pi * 1.0 * t)
           + 0.1 * np.sin(2 * np.pi * 6.0 * t) + 0.02 * rng.standard_normal(n))

    free = vae.acceleration_from_velocity(vel, fs, "freestyle")
    fly = vae.acceleration_from_velocity(vel, fs, "butterfly")
    unknown = vae.acceleration_from_velocity(vel, fs, None)

    tv = lambda x: float(np.abs(np.diff(x)).sum())
    assert vae._ACCEL_WINDOW_S["freestyle"] > vae._ACCEL_WINDOW_S["butterfly"]
    assert tv(free) < tv(fly)  # wider window -> smoother on the same signal
    np.testing.assert_array_equal(unknown, fly)  # unknown == default window == butterfly's here


# ── Swim-window low-rail guard (Phase 65-02) ────────────────────────────────────

class TestSwimWindowLowRail:
    """detect_swim_window's de-bias guard for the "indigo ray" bug.

    On some free/back/fly sessions the production CWT ridge rails to the low-frequency floor
    (_track_ridge's low-band bias tips a weak stroke fundamental down), so f_ref reads ~0.33 Hz,
    the settle test trivially passes at the start, and ip_end collapses onto b_end — the dive +
    underwater kicks then segment as cycles. The guard recomputes the ridge with the bias removed
    when f_ref rails below _WINDOW_FMIN_HZ. End-to-end correction on the real railed session is a
    human-verify via tools/underwater_probe.py; these tests pin the mechanism and the invariants.
    """

    def test_default_bias_ridge_is_byte_identical(self, real_session):
        """AC-3: the low_band_bias parameter defaults to production, so segment_cycles_wavelet's
        bare _cwt_ridge call — and every fixture score computed from it — is unchanged."""
        t, vel, _ = real_session
        fs = m._compute_fs(t)
        f_default, p_default = m._cwt_ridge(vel, fs)
        f_explicit, p_explicit = m._cwt_ridge(vel, fs, low_band_bias=m._RIDGE_LOW_BAND_BIAS)
        np.testing.assert_array_equal(f_default, f_explicit)
        np.testing.assert_array_equal(p_default, p_explicit)

    def test_removing_low_band_bias_raises_the_ridge(self, real_session):
        """The lever: MORE low-band bias cannot RAISE the ridge, so removing it (bias=0) lifts the
        ridge off the low floor. This is why the guard recomputes de-biased instead of guessing."""
        t, vel, _ = real_session
        fs = m._compute_fs(t)
        med = lambda b: float(np.median(m._cwt_ridge(vel, fs, low_band_bias=b)[0]))
        m0, m_prod, m_hi = med(0.0), med(m._RIDGE_LOW_BAND_BIAS), med(2.0)
        assert m0 >= m_prod >= m_hi          # monotonic: bias pulls the ridge down
        assert m0 > m_hi                     # strictly, across the range

    def test_guard_is_noop_on_a_plausible_session(self, real_session):
        """AC-2 + D2: when f_ref is already a plausible stroke rate the guard never fires, so the
        window is identical regardless of stroke_type — including breaststroke (exempt) and the
        two-argument call that predates the parameter."""
        t, vel, _ = real_session
        base = m.detect_swim_window(t, vel)                 # 2-arg call still works
        assert base is not None
        assert m.detect_swim_window(t, vel, "breaststroke") == base
        assert m.detect_swim_window(t, vel, "butterfly") == base
        assert m.detect_swim_window(t, vel, "freestyle") == base

    def test_low_rail_guard_recomputes_debiased_and_exempts_breaststroke(self, monkeypatch):
        """AC-1 + D2 control flow, deterministic. Stub _cwt_ridge so the production (biased) ridge
        rails to 0.30 Hz across the whole trace — collapsing ip_end to the window start — while the
        de-biased ridge settles at 1.0 Hz a third of the way in. A dolphin-kick stroke must take the
        de-biased window (ip_end moves off the collapse); breaststroke must keep the railed one."""
        fs = 90.0
        n = int(20 * fs)
        t = np.arange(n) / fs
        vel = np.zeros(n)                                   # content irrelevant; the ridge is stubbed
        power = np.ones(n)
        railed = np.full(n, 0.30)                           # f_ref rails to 0.30 Hz (< _WINDOW_FMIN_HZ)
        good = np.where(np.arange(n) < n // 3, 0.30, 1.0)   # de-biased: settles at 1.0 Hz after n/3

        def fake_cwt(v, f, low_band_bias=m._RIDGE_LOW_BAND_BIAS):
            return (good, power) if low_band_bias == 0.0 else (railed, power)
        monkeypatch.setattr(m, "_cwt_ridge", fake_cwt)

        railed_win = m.detect_swim_window(t, vel, "breaststroke")   # exempt -> keeps the railed window
        fixed_win = m.detect_swim_window(t, vel, "butterfly")       # guard fires -> de-biased window

        assert railed_win == (0, n)                         # collapsed onto the window start
        assert fixed_win is not None and fixed_win[0] > 0    # ip_end lifted off the collapse
        assert fixed_win != railed_win
        assert fixed_win[1] == n                             # swim_end unchanged; only ip_end moved


# ── Underwater start (Phase 75-02) ────────────────────────────────────────────

def _dive_glide_kick_trace(fs=90.0, surge_peak=3.0, dip_vel=0.6, kick_mean=1.6,
                           kick_amp=0.30, dip_t=2.0, duration_s=12.0):
    """A realistic start → glide → underwater-kick velocity trace.

    Rises to `surge_peak` (the dive/push-off), decays in streamline to `dip_vel` at
    `dip_t` (the glide), then oscillates about `kick_mean` (dolphin kicking). The dip
    at `dip_t` is the boundary detect_underwater_start must find.
    """
    t = np.arange(0.0, duration_s, 1.0 / fs)
    rise_t = 0.5
    vel = np.piecewise(
        t,
        [t < rise_t, (t >= rise_t) & (t < dip_t), t >= dip_t],
        [lambda x: surge_peak * x / rise_t,
         lambda x: surge_peak - (surge_peak - dip_vel) * (x - rise_t) / (dip_t - rise_t),
         lambda x: kick_mean + kick_amp * np.sin(2 * np.pi * 2.0 * (x - dip_t))],
    )
    return t, vel


class TestDetectUnderwaterStart:
    """Phase 75-02: the coach's 'underwater begins at the first big velocity dip' rule."""

    def test_finds_the_glide_end_dip(self):
        fs, dip_t = 90.0, 2.0
        t, vel = _dive_glide_kick_trace(fs=fs, dip_t=dip_t)
        idx = m.detect_underwater_start(t, vel, 0)
        assert idx is not None
        # within one sample of the modelled dip
        assert abs(idx / fs - dip_t) <= 1.5 / fs

    def test_returns_none_when_no_qualifying_dip(self):
        fs = 90.0
        t = np.arange(0.0, 10.0, 1.0 / fs)
        vel = np.linspace(0.0, 2.0, len(t))       # monotone rise, never dips
        assert m.detect_underwater_start(t, vel, 0) is None

    def test_tolerates_nans_in_a_stored_profile(self):
        """The recompute path feeds a stored velocity_profile, which can contain nulls."""
        fs, dip_t = 90.0, 2.0
        t, vel = _dive_glide_kick_trace(fs=fs, dip_t=dip_t)
        vel = vel.copy()
        vel[::97] = np.nan                        # scattered dropouts, none at the dip
        idx = m.detect_underwater_start(t, vel, 0)
        assert idx is not None
        assert abs(idx / fs - dip_t) <= 1.5 / fs

    def test_returns_none_on_a_trace_under_one_second(self):
        fs = 90.0
        t, vel = _dive_glide_kick_trace(fs=fs)
        assert m.detect_underwater_start(t[:40], vel[:40], 0) is None

    def test_ignores_a_shallow_dip_and_takes_the_next_prominent_one(self):
        """A ripple during the glide must not be mistaken for the glide end."""
        fs, dip_t = 90.0, 2.5
        t, vel = _dive_glide_kick_trace(fs=fs, dip_t=dip_t)
        vel = vel.copy()
        v95 = float(np.percentile(np.abs(vel), 95))
        ripple = int(1.2 * fs)                    # a small notch mid-glide
        vel[ripple] -= 0.10 * v95                 # prominence well under the 0.40 threshold
        idx = m.detect_underwater_start(t, vel, 0)
        assert idx is not None
        assert idx != ripple
        assert abs(idx / fs - dip_t) <= 1.5 / fs

    def test_honors_baseline_end_idx_offset(self):
        """Searching from a later baseline_end must still return a FULL-TRACE index."""
        fs, dip_t = 90.0, 2.0
        t, vel = _dive_glide_kick_trace(fs=fs, dip_t=dip_t)
        pad = int(3.0 * fs)
        t_pad = np.arange(0.0, (len(vel) + pad) / fs, 1.0 / fs)[: len(vel) + pad]
        vel_pad = np.concatenate([np.zeros(pad), vel])
        idx = m.detect_underwater_start(t_pad, vel_pad, pad)
        assert idx is not None
        assert abs((idx - pad) / fs - dip_t) <= 1.5 / fs

    def test_never_raises_on_degenerate_input(self):
        t = np.arange(0.0, 5.0, 1.0 / 90.0)
        assert m.detect_underwater_start(t, np.zeros(len(t)), 0) is None
        assert m.detect_underwater_start(t, np.full(len(t), np.nan), 0) is None
        assert m.detect_underwater_start(t, np.zeros(len(t)), 10_000) is None


def _uw_kick_segment(fs=90.0, n_kicks=6, base=1.0, amp=0.6, win_s=5.0, pad_s=1.0):
    """Low glide, then n_kicks evenly-spaced propulsive bumps over win_s, then glide.
    Returns t, vel and the (i0, i1) window bounds bracketing the kicks."""
    total = 2 * pad_s + win_s
    n = int(total * fs)
    t = np.arange(n) / fs
    vel = np.full(n, base)
    i0, i1 = int(pad_s * fs), int((pad_s + win_s) * fs)
    for c in np.linspace(pad_s, pad_s + win_s, n_kicks + 2)[1:-1]:
        vel += amp * np.exp(-0.5 * ((t - c) / 0.06) ** 2)
    return t, vel, i0, i1


class TestDetectUnderwaterKicks:
    """Phase 75-03: a propulsive downkick = one prominent velocity peak in the window."""

    def test_counts_the_known_bumps(self):
        t, vel, i0, i1 = _uw_kick_segment(n_kicks=6)
        peaks = m.detect_underwater_kicks(t, vel, i0, i1)
        assert peaks is not None
        assert len(peaks) == 6
        assert np.all((peaks >= i0) & (peaks < i1))    # full-trace, in-window
        assert np.all(np.diff(peaks) > 0)              # strictly increasing

    def test_min_distance_collapses_kicks_closer_than_the_ceiling(self):
        fs = 90.0
        n = int(3.0 * fs)
        t = np.arange(n) / fs
        vel = np.full(n, 1.0)
        for c in (1.0, 1.10):                          # 0.10 s apart, under fs/4 = 0.25 s
            vel += 0.6 * np.exp(-0.5 * ((t - c) / 0.03) ** 2)
        peaks = m.detect_underwater_kicks(t, vel, 0, n)
        assert peaks is not None
        assert len(peaks) == 1

    def test_empty_array_when_window_is_flat(self):
        fs = 90.0
        n = int(4.0 * fs)
        t = np.arange(n) / fs
        peaks = m.detect_underwater_kicks(t, np.full(n, 1.0), 0, n)
        assert peaks is not None
        assert len(peaks) == 0                         # valid window, just no kicks

    def test_tolerates_nans_in_the_window(self):
        t, vel, i0, i1 = _uw_kick_segment(n_kicks=5)
        vel = vel.copy()
        vel[i0 + 3 :: 37] = np.nan                     # scattered dropouts
        peaks = m.detect_underwater_kicks(t, vel, i0, i1)
        assert peaks is not None
        assert len(peaks) >= 4                          # a NaN may shave at most one edge peak

    def test_none_on_degenerate_window(self):
        t, vel, i0, i1 = _uw_kick_segment()
        assert m.detect_underwater_kicks(t, vel, i1, i0) is None            # reversed
        assert m.detect_underwater_kicks(t, vel, 5, 6) is None              # < 3 samples
        assert m.detect_underwater_kicks(t, np.full(len(t), np.nan), i0, i1) is None


def _kicks_then_strokes(fs=90.0, kick_hz=2.2, kick_s=3.0, stroke_hz=1.0,
                        stroke_s=5.0, tail_s=2.0, amp=0.6, base=1.4):
    """~2 Hz dolphin kicks (IN the 1.8-3.2 Hz band) → ~1 Hz arm strokes (BELOW it) → dead
    tail. The kick→stroke transition is the breakout detect_breakout_kickband must mark:
    the kick band is loud during the kicks and goes quiet once stroking takes over.
    Returns t, vel, uw_start(0), breakout_idx, swim_end_idx."""
    def seg(dur, f):
        n = int(dur * fs)
        return base + amp * np.sin(2 * np.pi * f * (np.arange(n) / fs))
    kicks, strokes = seg(kick_s, kick_hz), seg(stroke_s, stroke_hz)
    vel = np.concatenate([kicks, strokes, np.full(int(tail_s * fs), 0.02)])
    t = np.arange(len(vel)) / fs
    return t, vel, 0, len(kicks), len(kicks) + len(strokes)


class TestBreakoutKickband:
    """Phase 76: Underwater→Swim breakout via kick-band disappearance (free/back)."""

    def test_marks_the_kick_to_stroke_transition(self):
        fs = 90.0
        t, vel, uw, breakout, swim_end = _kicks_then_strokes(fs=fs)
        bk = m.detect_breakout_kickband(t, vel, uw, swim_end)
        assert bk is not None
        assert uw < bk < swim_end                        # strictly inside the window
        assert abs(bk - breakout) / fs <= 1.0            # near the modelled transition

    def test_none_when_no_kick_phase(self):
        """Pure ~1 Hz stroking: the kick band is never loud → nothing disappears → None."""
        fs = 90.0
        t, vel, uw, _, swim_end = _kicks_then_strokes(fs=fs, kick_s=0.0)
        assert m.detect_breakout_kickband(t, vel, uw, swim_end) is None

    def test_none_when_kick_run_too_short(self, monkeypatch):
        """A kick run shorter than _KICK_MIN_RUN_S is weak/short underwater → refuse (D2).

        The gate is exercised by RAISING the floor above a known-good 3 s kick run rather
        than by shrinking the run under the shipped floor: _KICK_SMOOTH_S is 0.4 s, so a
        burst short enough to beat a 0.5 s floor is smeared past it by the smoothing and
        the pairing stops being meaningful. This tests the mechanism, so it stays valid
        whatever the measured floor is. (It was 1.0 s; corrected to 0.5 s on 2026-08-20
        when the probe was first pointed at the shipped detector and the gate turned out
        to be vetoing 4 of 16 real freestyle sessions it had already placed correctly.)
        """
        fs = 90.0
        t, vel, uw, _, swim_end = _kicks_then_strokes(fs=fs, kick_s=3.0)
        assert m.detect_breakout_kickband(t, vel, uw, swim_end) is not None   # baseline
        monkeypatch.setattr(m, "_KICK_MIN_RUN_S", 10.0)                       # floor > run
        assert m.detect_breakout_kickband(t, vel, uw, swim_end) is None

    def test_none_when_band_never_quiets_in_window(self):
        """The 'kept dolphin-kicking' case: kicks fill the whole window, the only quiet is
        the dead tail AFTER swim_end → bounding to swim_end refuses rather than mismarks."""
        fs = 90.0
        t, vel, uw, breakout, _ = _kicks_then_strokes(fs=fs, kick_s=4.0, stroke_s=0.0)
        # swim_end at the end of the kicks: no in-window quiet exists
        assert m.detect_breakout_kickband(t, vel, uw, swim_end_idx=breakout) is None

    def test_tolerates_nans_in_a_stored_profile(self):
        fs = 90.0
        t, vel, uw, breakout, swim_end = _kicks_then_strokes(fs=fs)
        vel = vel.copy()
        vel[::101] = np.nan                              # scattered dropouts
        bk = m.detect_breakout_kickband(t, vel, uw, swim_end)
        assert bk is not None
        assert abs(bk - breakout) / fs <= 1.0

    def test_never_raises_on_degenerate_input(self):
        t = np.arange(0.0, 5.0, 1.0 / 90.0)
        assert m.detect_breakout_kickband(t, np.zeros(len(t)), 0) is None
        assert m.detect_breakout_kickband(t, np.full(len(t), np.nan), 0) is None
        assert m.detect_breakout_kickband(t, np.zeros(len(t)), 10_000) is None
        # window under two seconds → None
        assert m.detect_breakout_kickband(t[:40], np.ones(40), 0, 40) is None


def _full_free_trace(fs=90.0):
    """baseline → dive surge → glide dip → ~2 Hz underwater kicks → ~1 Hz surface strokes →
    dead tail. A freestyle-shaped trace exercising the whole front end of
    compute_session_metrics. Returns t, vel, dist, breakout_idx (kick→stroke transition)."""
    def const(dur, v):
        return np.full(int(dur * fs), v)

    def sine(dur, f, b, a):
        return b + a * np.sin(2 * np.pi * f * (np.arange(int(dur * fs)) / fs))

    baseline = const(1.0, 0.0)
    rise     = np.linspace(0.0, 3.0, int(0.4 * fs))
    glide    = np.linspace(3.0, 0.5, int(1.3 * fs))     # decays to the dip
    kicks    = sine(3.0, 2.2, 1.5, 0.6)                 # underwater dolphin kicks
    strokes  = sine(6.0, 1.0, 1.4, 0.5)                 # surface arm strokes
    tail     = const(2.0, 0.02)
    vel = np.concatenate([baseline, rise, glide, kicks, strokes, tail])
    t = np.arange(len(vel)) / fs
    dist = np.concatenate([[0.0], np.cumsum(np.abs(vel[:-1]) / fs)])
    breakout_idx = len(baseline) + len(rise) + len(glide) + len(kicks)
    return t, vel, dist, breakout_idx


class TestBreakoutIntegration:
    """Phase 76: the per-stroke ip_end override in compute_session_metrics."""

    def test_freestyle_moves_ip_end_to_the_breakout(self):
        fs = 90.0
        t, vel, dist, breakout = _full_free_trace(fs=fs)
        r = m.compute_session_metrics(t, vel, dist, stroke_type="freestyle")
        ip_end = r["initial_phase"]["initial_phase_end_idx"]
        assert abs(ip_end - breakout) / fs <= 1.0        # detector placed it at the breakout

    def test_freestyle_and_backstroke_use_the_same_detector(self):
        """D1: the two flutter strokes share ONE begin-stroke detector. Same trace → same
        ip_end, because both route through detect_breakout_kickband identically (backstroke
        is physically analogous to freestyle: surface = arm strokes + flutter, not
        undulation). Ships flagged unvalidated for back (n=0 ground truth), 59-05 stance."""
        t, vel, dist, _ = _full_free_trace()
        free = m.compute_session_metrics(t, vel, dist, stroke_type="freestyle")
        back = m.compute_session_metrics(t, vel, dist, stroke_type="backstroke")
        assert (free["initial_phase"]["initial_phase_end_idx"]
                == back["initial_phase"]["initial_phase_end_idx"])

    def test_backstroke_enters_the_branch(self, monkeypatch):
        called = []
        real = m.detect_breakout_kickband
        monkeypatch.setattr(m, "detect_breakout_kickband",
                            lambda *a, **k: called.append(1) or real(*a, **k))
        t, vel, dist, _ = _full_free_trace()
        m.compute_session_metrics(t, vel, dist, stroke_type="backstroke")
        assert called                                    # back shares the free detector

    def test_detector_not_called_for_butterfly(self, monkeypatch):
        """AC-3: fly never enters the branch → ip_end + every metric byte-identical."""
        called = []
        monkeypatch.setattr(m, "detect_breakout_kickband",
                            lambda *a, **k: called.append(1))
        t, vel, dist, _ = _full_free_trace()
        m.compute_session_metrics(t, vel, dist, stroke_type="butterfly")
        assert called == []

    def test_detector_called_for_freestyle(self, monkeypatch):
        called = []
        real = m.detect_breakout_kickband
        monkeypatch.setattr(m, "detect_breakout_kickband",
                            lambda *a, **k: called.append(1) or real(*a, **k))
        t, vel, dist, _ = _full_free_trace()
        m.compute_session_metrics(t, vel, dist, stroke_type="freestyle")
        assert called                                    # free/back do enter the branch

    def test_refusal_falls_back_to_the_swim_window_value(self, monkeypatch):
        """When the detector refuses, ip_end is exactly the pre-branch (detect_swim_window)
        value — identical to the None-stroke path, which never enters the branch."""
        monkeypatch.setattr(m, "detect_breakout_kickband", lambda *a, **k: None)
        t, vel, dist, _ = _full_free_trace()
        r_free = m.compute_session_metrics(t, vel, dist, stroke_type="freestyle")
        r_none = m.compute_session_metrics(t, vel, dist, stroke_type=None)
        assert (r_free["initial_phase"]["initial_phase_end_idx"]
                == r_none["initial_phase"]["initial_phase_end_idx"])

    def test_manual_ip_end_wins_over_the_detector(self, monkeypatch):
        """AC-3: a manual ip_end_idx overrides the detector — the analysis is identical
        no matter what the detector returns."""
        t, vel, dist, breakout = _full_free_trace()
        man = {"ip_end_idx": breakout + int(1.5 * 90.0)}
        monkeypatch.setattr(m, "detect_breakout_kickband",
                            lambda *a, **k: breakout)     # detector says one thing
        r_a = m.compute_session_metrics(t, vel, dist, stroke_type="freestyle", manual=man)
        monkeypatch.setattr(m, "detect_breakout_kickband",
                            lambda *a, **k: None)          # detector says another
        r_b = m.compute_session_metrics(t, vel, dist, stroke_type="freestyle", manual=man)
        assert r_a["cycles"] == r_b["cycles"]              # manual governs, detector ignored
        assert r_a["session"] == r_b["session"]


def _fly_kicks_then_strokes(fs=90.0, kick_s=4.0, stroke_s=6.0):
    """A butterfly-shaped segment: a pure ~1.2 Hz underwater kick fundamental, then the
    surface stroke — a ~0.9 Hz arm cycle summed with its ~1.8 Hz two-beat kick harmonic.

    That sum is the whole point of Phase 77: the ~2 Hz kick band NEVER disappears on fly
    (it is the two dolphin kicks per arm cycle), so only the ARM band appearing separates
    the phases. Measured ratio on this fixture: 0.36 underwater, 5.7 on the surface.

    ⚠ Deliberately NO constant lead-in and NO dead tail. Both are step discontinuities,
    and the CWT smears a step across ~1 s at these frequencies, which manufactures a ratio
    rise that has nothing to do with an arm cycle. An earlier version of this fixture had
    both and made the refusal cases below fire on their own edges.

    Returns t, vel, uw_start_idx, breakout_idx, swim_end_idx.
    """
    def sine(dur, f, b, a):
        n = int(dur * fs)
        return b + a * np.sin(2 * np.pi * f * (np.arange(n) / fs))

    kicks = sine(kick_s, 1.2, 1.5, 0.6) if kick_s > 0 else np.empty(0)
    arms  = (sine(stroke_s, 0.9, 1.4, 0.6) + sine(stroke_s, 1.8, 0.0, 0.5)
             if stroke_s > 0 else np.empty(0))
    vel = np.concatenate([kicks, arms])
    t = np.arange(len(vel)) / fs
    return t, vel, 0, len(kicks), len(vel)


class TestBreakoutFly:
    """Phase 77: Underwater→Swim breakout via arm-cycle appearance (butterfly)."""

    def test_marks_the_arm_cycle_appearance(self):
        fs = 90.0
        t, vel, uw, breakout, swim_end = _fly_kicks_then_strokes(fs=fs)
        bk = m.detect_breakout_fly(t, vel, uw, swim_end)
        assert bk is not None
        assert uw < bk < swim_end                        # strictly inside the window
        # 1.5 s, not 1.0: the CWT smears this fixture's HARD step over ~1 s at these
        # frequencies, so ~1.1 s of lag is the wavelet, not the detector. The accuracy
        # claim that matters is the DB score (AC-2, 0.35 s median), not this fixture.
        assert abs(bk - breakout) / fs <= 1.5            # near the modelled transition

    def test_none_when_the_arm_cycle_never_appears(self):
        """A pure ~1.2 Hz kick for the whole window: the ratio never steps up → None.

        This is the case that separates Phase 77 from Phase 76 — nothing DISAPPEARS here
        either, so a disappearance detector would have nothing to say about it.

        Refused by the contrast gate (measured contrast 1.35 vs a 1.5 floor).
        """
        fs = 90.0
        t, vel, uw, _, swim_end = _fly_kicks_then_strokes(fs=fs, kick_s=10.0, stroke_s=0.0)
        assert m.detect_breakout_fly(t, vel, uw, swim_end) is None

    def test_stationary_stroking_is_refused_by_contrast_not_by_the_low_run(self, monkeypatch):
        """Arms from the first sample — a surface-fly trace with no underwater phase at all.

        ⚠ This test is asserted with the floor RAISED, and the reason is a real finding
        rather than test convenience: the sustained-low-run requirement does NOT refuse
        this case on its own. The arm cycle's own amplitude modulation dips the ratio for
        long enough to satisfy min_low, so the low-run gate is happy and only the contrast
        gate stops it. At the shipped 1.5 floor it does refuse, but by 0.7% (measured
        contrast 1.49) — a margin thin enough that asserting on it would be testing numpy's
        rounding, not the detector. So: assert the mechanism at a floor that unambiguously
        separates stationary (1.35-1.49) from a real reorganization (16.5 on this fixture),
        and record the thin real-world margin here rather than hiding it.
        """
        fs = 90.0
        t, vel, uw, _, swim_end = _fly_kicks_then_strokes(fs=fs, kick_s=0.0, stroke_s=10.0)
        monkeypatch.setattr(m, "_FLY_MIN_CONTRAST", 3.0)
        assert m.detect_breakout_fly(t, vel, uw, swim_end) is None

    def test_none_when_the_rise_is_outside_the_swim_window(self):
        """Short-underwater class: bounding the search to swim_end turns the confident
        late miss into a refusal, exactly as detect_breakout_kickband does."""
        fs = 90.0
        t, vel, uw, breakout, _ = _fly_kicks_then_strokes(fs=fs)
        assert m.detect_breakout_fly(t, vel, uw, swim_end_idx=breakout) is None

    def test_tolerates_nans_in_a_stored_profile(self):
        fs = 90.0
        t, vel, uw, breakout, swim_end = _fly_kicks_then_strokes(fs=fs)
        vel = vel.copy()
        vel[::101] = np.nan                              # scattered magnet dropouts
        bk = m.detect_breakout_fly(t, vel, uw, swim_end)
        assert bk is not None
        assert abs(bk - breakout) / fs <= 1.5

    def test_never_raises_on_degenerate_input(self):
        t = np.arange(0.0, 5.0, 1.0 / 90.0)
        assert m.detect_breakout_fly(t, np.zeros(len(t)), 0) is None
        assert m.detect_breakout_fly(t, np.full(len(t), np.nan), 0) is None
        assert m.detect_breakout_fly(t, np.zeros(len(t)), 10_000) is None
        # window under two seconds → None
        assert m.detect_breakout_fly(t[:40], np.ones(40), 0, 40) is None

    def test_contrast_gate_refuses_a_ratio_that_only_ripples(self, monkeypatch):
        """The gate is exercised by RAISING the floor above a known-good step rather than
        by shrinking the step, so the test stays valid whatever the measured floor is
        (same construction as the Phase-76 min-run test)."""
        fs = 90.0
        t, vel, uw, _, swim_end = _fly_kicks_then_strokes(fs=fs)
        assert m.detect_breakout_fly(t, vel, uw, swim_end) is not None    # baseline
        monkeypatch.setattr(m, "_FLY_MIN_CONTRAST", 1e6)                 # floor > any step
        assert m.detect_breakout_fly(t, vel, uw, swim_end) is None

    def test_band_refinement_falls_back_to_the_fixed_bands(self, monkeypatch):
        """D5: the per-session f0 refinement is unsupervised hardening with a fixed-band
        fallback — it must never make the detector raise or lose the transition."""
        fs = 90.0
        t, vel, uw, breakout, swim_end = _fly_kicks_then_strokes(fs=fs)
        monkeypatch.setattr(m, "_FLY_REFINE_BANDS", True)
        bk = m.detect_breakout_fly(t, vel, uw, swim_end)
        assert bk is not None
        assert abs(bk - breakout) / fs <= 1.5


class TestBreakoutCollapseGuard:
    """Phase 76 fix (2026-08-20): a breakout override must leave a swim behind it.

    The detectors answer a LOCAL question and cannot see that a late wrong answer leaves
    the segmenter two seconds to work with. Before the guard, the committed breaststroke
    fixture driven as freestyle shipped stroke_count = 0 — a confidently EMPTY session.
    """

    def test_guard_rejects_a_window_with_no_room_to_stroke(self):
        t, vel, dist, breakout = _full_free_trace(fs=90.0)
        swim_end = len(vel) - 1
        assert m._breakout_leaves_swim(t, vel, swim_end - 20, swim_end) is False

    def test_guard_accepts_a_real_swim(self):
        t, vel, dist, breakout = _full_free_trace(fs=90.0)
        assert m._breakout_leaves_swim(t, vel, breakout, len(vel) - 1) is True

    def test_guard_never_raises_on_degenerate_input(self):
        t, vel, dist, _ = _full_free_trace(fs=90.0)
        for bk, end in ((0, 0), (10, 5), (-5, 3), (len(vel), len(vel))):
            assert m._breakout_leaves_swim(t, vel, bk, end) in (True, False)
        flat = np.zeros_like(vel)
        assert m._breakout_leaves_swim(t, flat, 10, len(flat) - 1) in (True, False)

    def test_collapsed_breakout_is_vetoed_and_the_incumbent_stands(self, monkeypatch):
        """A detector that answers just before swim_end is disbelieved, so ip_end is the
        pre-branch detect_swim_window value — identical to the None-stroke path."""
        t, vel, dist, _ = _full_free_trace(fs=90.0)
        r_none = m.compute_session_metrics(t, vel, dist, stroke_type=None)
        monkeypatch.setattr(m, "detect_breakout_kickband",
                            lambda tt, vv, uw, se=None: int(se) - 20)
        r_free = m.compute_session_metrics(t, vel, dist, stroke_type="freestyle")
        assert (r_free["initial_phase"]["initial_phase_end_idx"]
                == r_none["initial_phase"]["initial_phase_end_idx"])

    def test_real_session_as_freestyle_still_segments(self, real_session):
        """The regression itself. processed/breaststroke_sample.csv carries no dolphin-kick
        band, so detect_breakout_kickband answers late (t=25.54 s of a 31.1 s trace) and
        used to collapse stroke_count 11 -> 0. The guard vetoes it."""
        t, vel, dist = real_session
        base = m.compute_session_metrics(t, vel, dist)["session"]["stroke_count"]
        for stroke in ("freestyle", "backstroke"):
            n = m.compute_session_metrics(
                t, vel, dist, stroke_type=stroke)["session"]["stroke_count"]
            assert n > 0, f"{stroke}: breakout override collapsed the swim window"
            assert abs(n - base / 2) <= 1, f"{stroke}: {n} vs base {base}"


def _full_fly_trace(fs=90.0):
    """baseline → dive surge → glide dip → ~1.2 Hz underwater dolphin kicks → surface fly
    (~0.9 Hz arm cycle + its ~1.8 Hz two-beat harmonic) → dead tail.

    The butterfly counterpart of _full_free_trace, and the one structural difference is the
    whole reason Phase 77 exists: the surface segment KEEPS a ~2 Hz component, so a
    kick-band-disappearance rule has nothing to find here. Returns t, vel, dist,
    breakout_idx (the kick→stroke transition).
    """
    def const(dur, v):
        return np.full(int(dur * fs), v)

    def sine(dur, f, b, a):
        return b + a * np.sin(2 * np.pi * f * (np.arange(int(dur * fs)) / fs))

    baseline = const(1.0, 0.0)
    rise     = np.linspace(0.0, 3.0, int(0.4 * fs))
    glide    = np.linspace(3.0, 0.5, int(1.3 * fs))       # decays to the dip
    kicks    = sine(4.0, 1.2, 1.5, 0.6)                   # underwater dolphin kicks
    fly      = (sine(7.0, 0.9, 1.4, 0.6)                  # surface arm cycle...
                + sine(7.0, 1.8, 0.0, 0.5))               # ...plus its two kick beats
    tail     = const(2.0, 0.02)
    vel = np.concatenate([baseline, rise, glide, kicks, fly, tail])
    t = np.arange(len(vel)) / fs
    dist = np.concatenate([[0.0], np.cumsum(np.abs(vel[:-1]) / fs)])
    breakout_idx = len(baseline) + len(rise) + len(glide) + len(kicks)
    return t, vel, dist, breakout_idx


class TestBreakoutFlyIntegration:
    """Phase 77: the butterfly ip_end override in compute_session_metrics."""

    def test_butterfly_moves_ip_end_to_the_breakout(self):
        fs = 90.0
        t, vel, dist, breakout = _full_fly_trace(fs=fs)
        r = m.compute_session_metrics(t, vel, dist, stroke_type="butterfly")
        ip_end = r["initial_phase"]["initial_phase_end_idx"]
        assert abs(ip_end - breakout) / fs <= 1.5        # see TestBreakoutFly on the 1.5 s

    def test_detector_called_for_butterfly_only(self, monkeypatch):
        """AC-3: free/back/breast/None never enter the branch, so nothing about them can
        move. The complement of Phase 76's test_detector_not_called_for_butterfly."""
        t, vel, dist, _ = _full_fly_trace()
        for stroke in ("freestyle", "backstroke", "breaststroke", None):
            called = []
            monkeypatch.setattr(m, "detect_breakout_fly", lambda *a, **k: called.append(1))
            m.compute_session_metrics(t, vel, dist, stroke_type=stroke)
            assert called == [], stroke
        called = []
        real = m.detect_breakout_fly
        monkeypatch.setattr(m, "detect_breakout_fly",
                            lambda *a, **k: called.append(1) or real(*a, **k))
        m.compute_session_metrics(t, vel, dist, stroke_type="butterfly")
        assert called

    def test_free_back_and_breast_are_unchanged_by_this_plan(self, real_session):
        """AC-3/AC-5 regression guard, on the committed real fixture rather than a
        synthetic one. These are the values the pre-Phase-77 module produces — verified by
        rebuilding it with both Phase-77 hunks stripped and diffing every returned key, so
        the numbers below are a snapshot of the old behaviour, not of the new.
        """
        t, vel, dist = real_session
        expected = {"freestyle": (1428, 5), "backstroke": (1428, 5),
                    "breaststroke": (1428, 9), None: (1428, 11)}
        for stroke, (ip_end, n_cycles) in expected.items():
            r = m.compute_session_metrics(t, vel, dist, stroke_type=stroke)
            assert r["initial_phase"]["initial_phase_end_idx"] == ip_end, stroke
            assert r["session"]["stroke_count"] == n_cycles, stroke

    def test_manual_ip_end_wins_over_the_detector(self, monkeypatch):
        """AC-3: Phase 47 precedence — a human boundary governs whatever the detector says.

        Held against the SAME stroke_type both times, because stroke_type also selects the
        segmenter (SEGMENTER_BY_STROKE): butterfly and None legitimately produce different
        cycles from identical boundaries, so comparing across strokes would test that
        instead of the override.
        """
        t, vel, dist, breakout = _full_fly_trace()
        man = {"ip_end_idx": breakout + int(1.5 * 90.0)}
        monkeypatch.setattr(m, "detect_breakout_fly",
                            lambda *a, **k: breakout)      # detector says one thing
        r_a = m.compute_session_metrics(t, vel, dist, stroke_type="butterfly", manual=man)
        monkeypatch.setattr(m, "detect_breakout_fly",
                            lambda *a, **k: None)          # detector says another
        r_b = m.compute_session_metrics(t, vel, dist, stroke_type="butterfly", manual=man)
        assert r_a["cycles"] == r_b["cycles"]              # manual governs, detector ignored
        assert r_a["session"] == r_b["session"]
        # ⚠ Not asserted: initial_phase["initial_phase_end_idx"] == the manual value. The
        # manual block sets the LOCAL ip_end that segmentation uses but does not write back
        # into the initial_phase dict, so that key keeps the detector's answer. Pre-existing
        # and shared with the 76 branch and 59-03's window block — noted, not changed here.

    def test_refusal_falls_back_to_the_swim_window_value(self, monkeypatch):
        """When the detector refuses, ip_end is exactly the pre-branch
        (detect_swim_window) value — identical to the None-stroke path."""
        monkeypatch.setattr(m, "detect_breakout_fly", lambda *a, **k: None)
        t, vel, dist, _ = _full_fly_trace()
        r_fly  = m.compute_session_metrics(t, vel, dist, stroke_type="butterfly")
        r_none = m.compute_session_metrics(t, vel, dist, stroke_type=None)
        assert (r_fly["initial_phase"]["initial_phase_end_idx"]
                == r_none["initial_phase"]["initial_phase_end_idx"])

    def test_collapsed_breakout_is_vetoed_and_the_incumbent_stands(self, monkeypatch):
        """The shared collapse guard applies to the fly branch too: a detector answering
        just before swim_end is disbelieved rather than shipping stroke_count = 0.
        Measured motivation — the 76 kick-band rule produces exactly this on 7 of the 16
        real fly sessions (+6.5 to +11.1 s)."""
        t, vel, dist, _ = _full_fly_trace(fs=90.0)
        r_none = m.compute_session_metrics(t, vel, dist, stroke_type=None)
        monkeypatch.setattr(m, "detect_breakout_fly",
                            lambda tt, vv, uw, se=None: int(se) - 20)
        r_fly = m.compute_session_metrics(t, vel, dist, stroke_type="butterfly")
        assert (r_fly["initial_phase"]["initial_phase_end_idx"]
                == r_none["initial_phase"]["initial_phase_end_idx"])
        assert r_fly["session"]["stroke_count"] > 0

    def test_real_session_as_butterfly_still_segments(self, real_session):
        """The Phase-76 collapse regression, re-run through the new branch: the committed
        breaststroke fixture driven as butterfly must never ship an empty swim."""
        t, vel, dist = real_session
        n = m.compute_session_metrics(
            t, vel, dist, stroke_type="butterfly")["session"]["stroke_count"]
        assert n > 0
