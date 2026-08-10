"""Tests for segmenter_eval.py — the Phase-59 ground-truth scoring harness.

Two layers:
  * Unit tests on hand-constructed inputs, where the expected precision/recall/F1 are
    computed by hand in the test name or docstring.
  * A regression (added in 59-01 Task 3) that scores real segmenters against a committed
    fixture and pins the result, so a future change that degrades segmentation fails here.
"""
import numpy as np
import pytest

import segmenter_eval as se


class TestMatchSeries:
    def test_perfect_match(self):
        truth = [1.0, 2.0, 3.0]
        s = se.score_series(truth, truth, tol_s=0.15)
        assert s["matched"] == 3
        assert s["precision"] == 1.0
        assert s["recall"] == 1.0
        assert s["f1"] == 1.0
        assert s["mae_s"] == 0.0
        assert s["bias_s"] == 0.0

    def test_all_miss_when_outside_tolerance(self):
        s = se.score_series([1.0, 2.0], [5.0, 6.0], tol_s=0.15)
        assert s["matched"] == 0
        assert s["precision"] == 0.0
        assert s["recall"] == 0.0
        assert s["f1"] == 0.0
        assert s["mae_s"] is None
        assert s["bias_s"] is None

    def test_duplicate_prediction_consumes_only_one_truth(self):
        """Two predictions on top of one truth: 1 match, precision 0.5, recall 1.0."""
        s = se.score_series([1.0, 1.0], [1.0], tol_s=0.1)
        assert s["n_pred"] == 2
        assert s["n_truth"] == 1
        assert s["matched"] == 1
        assert s["precision"] == 0.5
        assert s["recall"] == 1.0

    def test_optimal_beats_greedy(self):
        """THE reason this module does not use a greedy matcher.

        truth [0.00, 0.10], pred [0.09, 0.20], tol 0.12.
        Greedy nearest-first pairs 0.09 with 0.10 (error 0.01), then strands 0.20 because
        0.00 is 0.20 away — reporting ONE match. The optimal assignment pairs 0.09→0.00
        (0.09) and 0.20→0.10 (0.10) for a total cost of 0.19, matching BOTH.
        """
        s = se.score_series([0.09, 0.20], [0.00, 0.10], tol_s=0.12)
        assert s["matched"] == 2, "greedy matching would report 1 here"
        assert s["recall"] == 1.0
        assert s["mae_s"] == pytest.approx(0.095)

    def test_result_is_order_independent(self):
        pred = [0.20, 0.09]
        rev = [0.09, 0.20]
        a = se.score_series(pred, [0.00, 0.10], tol_s=0.12)
        b = se.score_series(rev, [0.00, 0.10], tol_s=0.12)
        assert a["matched"] == b["matched"] == 2
        assert a["f1"] == b["f1"]

    @pytest.mark.parametrize("pred,truth", [
        ([], [1.0, 2.0]),
        ([1.0, 2.0], []),
        ([], []),
    ])
    def test_empty_inputs_score_zero_not_nan(self, pred, truth):
        s = se.score_series(pred, truth, tol_s=0.15)
        assert s["matched"] == 0
        for key in ("precision", "recall", "f1"):
            assert s[key] == 0.0
            assert not np.isnan(s[key])

    def test_non_numeric_entries_are_dropped_not_raised(self):
        s = se.score_series([1.0, None, "x", float("nan")], [1.0], tol_s=0.1)
        assert s["n_pred"] == 1
        assert s["matched"] == 1

    def test_unmatched_lists_are_returned(self):
        pairs, un_p, un_t = se.match_series([1.0, 9.0], [1.0, 5.0], tol_s=0.1)
        assert len(pairs) == 1
        assert un_p == [9.0]
        assert un_t == [5.0]


class TestSweep:
    def test_sweep_returns_one_score_per_tolerance(self):
        rows = se.sweep([1.05], [1.0], [0.01, 0.10, 0.30])
        assert [r["tol_s"] for r in rows] == [0.01, 0.10, 0.30]
        assert [r["matched"] for r in rows] == [0, 1, 1]


class TestCoverage:
    def test_fully_labeled_window_is_about_one(self):
        marks = [float(i) for i in range(10)]        # 10 marks, 1.0 s apart
        c = se.coverage(marks, 0.0, 10.0)
        assert c["median_isi_s"] == pytest.approx(1.0)
        assert c["expected_marks"] == pytest.approx(10.0)
        assert c["ratio"] == pytest.approx(1.0)

    def test_half_labeled_window_is_about_one_half(self):
        marks = [float(i) for i in range(5)]         # only the first half labeled
        c = se.coverage(marks, 0.0, 10.0)
        assert c["ratio"] == pytest.approx(0.5)

    def test_too_few_marks_yields_no_ratio(self):
        """A 2-point ISI is not a tempo estimate, so no ratio is fabricated."""
        c = se.coverage([1.0, 2.0], 0.0, 10.0)
        assert c["median_isi_s"] is None
        assert c["ratio"] is None
        assert c["n_marks"] == 2

    def test_missing_window_bound_yields_no_ratio(self):
        c = se.coverage([1.0, 2.0, 3.0], 0.0, None)
        assert c["ratio"] is None
        assert c["median_isi_s"] == pytest.approx(1.0)


class TestAggregate:
    def _row(self, sid, stroke, n_pred, n_truth, matched, mae=0.05):
        return {
            "session_id": sid,
            "stroke_type": stroke,
            "score": {
                "n_pred": n_pred, "n_truth": n_truth, "matched": matched,
                "mae_s": mae,
            },
        }

    def test_groups_by_stroke(self):
        out = se.aggregate([
            self._row("a", "freestyle", 10, 10, 8),
            self._row("b", "freestyle", 10, 10, 6),
            self._row("c", "butterfly", 5, 5, 5),
        ])
        assert set(out) == {"freestyle", "butterfly"}
        assert out["freestyle"]["matched"] == 14
        assert out["freestyle"]["precision"] == pytest.approx(0.7)
        assert out["butterfly"]["f1"] == 1.0

    def test_excluded_session_drops_from_precision_but_stays_in_recall_all(self):
        rows = [
            self._row("keep", "freestyle", 10, 10, 8),
            self._row("drop", "freestyle", 20, 5, 5),   # partial labels: 20 preds, 5 marks
        ]
        out = se.aggregate(rows, exclude_ids=["drop"])["freestyle"]
        assert out["n_excluded"] == 1
        assert out["excluded_ids"] == ["drop"]
        # Precision sees only the kept session — 8/10, not 13/30.
        assert out["precision"] == pytest.approx(0.8)
        assert out["recall"] == pytest.approx(0.8)
        # recall_all still counts the excluded session's truth marks.
        assert out["n_truth_all"] == 15
        assert out["recall_all"] == pytest.approx(13 / 15)

    def test_mae_is_weighted_by_matched_count(self):
        rows = [
            self._row("a", "freestyle", 10, 10, 9, mae=0.10),
            self._row("b", "freestyle", 10, 10, 1, mae=0.50),
        ]
        out = se.aggregate(rows)["freestyle"]
        assert out["mae_s"] == pytest.approx((9 * 0.10 + 1 * 0.50) / 10)


# ── Regression against the committed fixture ─────────────────────────────────
#
# Pins what the three candidate segmenters and the phase seeder ACTUALLY produce on four
# real sessions, to 1e-6. Exact values, not a floor: plan 59-02 is a pure dispatch
# refactor whose acceptance is byte-identical output, and a `>=` floor cannot prove that.
#
# ⚠ THESE NUMBERS ARE NOT A DEFINITION OF CORRECTNESS. The fixture is ONE swimmer, one
# pool, one device. It is a change-detector: if a number here moves, something in
# metrics.py changed and you must know why. A LOW score is expected today — that is the
# measurement Phase 59 exists to take, not a bug in this test.
#
# Runs fully offline: no Supabase, no .env, no network.
import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = _ROOT / "tests" / "fixtures" / "segmenter_truth.json"


def _load_cli():
    """Import tools/score_segmenter.py by path so the regression pins the REAL tool.

    Re-implementing the candidate invocation here would let the test and the tool drift
    apart silently, which is precisely the failure this suite exists to prevent.
    """
    spec = importlib.util.spec_from_file_location(
        "score_segmenter", str(_ROOT / "tools" / "score_segmenter.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _record(row):
    return {
        "annotation": row["annotation"],
        "session": {
            "id": row["session_id"],
            "stroke_type": row["stroke_type"],
            "sample_rate_hz": row["sample_rate_hz"],
            "velocity_profile": row["velocity_profile"],
            "metrics_json_auto": row["metrics_json_auto"],
            "metrics_json": None,
        },
    }


PINNED = {
    "3409e502": {
        ("annotated", "wavelet", "cycles"): (16, 6, 0.5217391304347825),
        ("annotated", "wavelet", "entries"): (16, 10, 0.6666666666666666),
        ("annotated", "trough", "cycles"): (0, 0, 0.0),
        ("annotated", "peakpick", "entries"): (22, 11, 0.6111111111111112),
        ("production", "wavelet", "entries"): (15, 0, 0.0),
        ("production", "peakpick", "cycles"): (18, 5, 0.4),
        ("phase", "dive_start_s"): 0.12235999999996694,
        ("phase", "stroke_start_s"): -1.4596880000000727,
        ("phase", "finish_s"): 4.299535999999591,
    },
    "4219daea": {
        ("annotated", "wavelet", "cycles"): (20, 6, 0.41379310344827586),
        ("annotated", "wavelet", "entries"): (20, 10, 0.5405405405405405),
        ("annotated", "trough", "cycles"): (0, 0, 0.0),
        ("annotated", "peakpick", "entries"): (28, 6, 0.26666666666666666),
        # Same session, window start moved 0.58 s: F1 0.54 -> 0.11 under the OLD window.
        # RE-BASELINED in 59-04 when the production column was un-staled to use
        # detect_swim_window; the sensitivity observation stands, the number moved.
        ("production", "wavelet", "entries"): (16, 9, 0.5454545454545455),
        ("production", "peakpick", "cycles"): (21, 3, 0.2),
        ("phase", "dive_start_s"): 0.30296799999982227,
        ("phase", "stroke_start_s"): -0.5757280000002183,
        ("phase", "finish_s"): 0.012391999999444181,
    },
    "69f33669": {
        ("annotated", "wavelet", "cycles"): (19, 4, 0.2857142857142857),
        ("annotated", "wavelet", "entries"): (19, 3, 0.22222222222222218),
        ("annotated", "trough", "cycles"): (11, 1, 0.09999999999999999),
        ("annotated", "peakpick", "entries"): (18, 8, 0.6153846153846153),
        ("production", "wavelet", "entries"): (19, 0, 0.0),
        ("production", "peakpick", "cycles"): (18, 9, 0.6666666666666666),
        ("phase", "dive_start_s"): -0.39207200000003595,
        ("phase", "stroke_start_s"): -6.482040000000042,
        ("phase", "finish_s"): 3.7221519999995003,
    },
    "c0cdfc25": {
        ("annotated", "wavelet", "cycles"): (22, 8, 0.4705882352941177),
        ("annotated", "wavelet", "entries"): (22, 7, 0.4242424242424242),
        ("annotated", "trough", "cycles"): (3, 1, 0.13333333333333333),
        ("annotated", "peakpick", "entries"): (31, 11, 0.5238095238095238),
        ("production", "wavelet", "entries"): (18, 3, 0.20689655172413793),
        ("production", "peakpick", "cycles"): (26, 11, 0.5789473684210527),
        ("phase", "dive_start_s"): -0.2998960000000248,
        ("phase", "stroke_start_s"): -3.5554240000000306,
        ("phase", "finish_s"): 4.392919999999581,
    },
}


class TestFixtureRegression:
    @pytest.fixture(scope="class")
    def scored(self):
        doc = json.load(open(FIXTURE, encoding="utf-8"))
        cli = _load_cli()
        return {r["session_id"][:8]: cli.score_session(_record(r), 0.15, (0.15,))
                for r in doc["sessions"]}

    def test_fixture_shape(self, scored):
        assert set(scored) == set(PINNED)
        assert len(scored) == 4

    def test_no_network_credentials_needed(self, monkeypatch, scored):
        """The guardrail must run in CI with no .env and no Supabase reachable."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        assert all(s["n_samples"] > 0 for s in scored.values())

    @pytest.mark.parametrize("sid", sorted(PINNED))
    def test_scores_are_unchanged(self, scored, sid):
        got = scored[sid]
        for key, expected in PINNED[sid].items():
            if key[0] == "phase":
                actual = got["phases"][key[1]]["error_s"]
                assert actual == pytest.approx(expected, abs=1e-6), f"{sid} {key}"
                continue
            window, cand, framing = key
            s = got["cycles"][window][cand][framing]
            n_pred, matched, f1 = expected
            assert s["n_pred"] == n_pred, f"{sid} {key} n_pred"
            assert s["matched"] == matched, f"{sid} {key} matched"
            assert s["f1"] == pytest.approx(f1, abs=1e-6), f"{sid} {key} f1"

    def test_circularity_guard_prefers_the_auto_backup(self, scored):
        """Phase predictions must never be seeded from the recomputed metrics_json."""
        cli = _load_cli()
        contaminated = {
            "metrics_json_auto": None,
            "metrics_json": {"session": {}, "data_quality": {"recomputed_from_annotation": True}},
        }
        src, reason = cli._auto_metrics(contaminated)
        assert src is None
        assert "recomputed" in reason
        # And with a backup present, that backup is what gets used.
        src, reason = cli._auto_metrics({"metrics_json_auto": {"session": {"x": 1}},
                                         "metrics_json": {"session": {"x": 2}}})
        assert src["session"]["x"] == 1 and reason is None
