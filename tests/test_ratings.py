"""Unit tests for ratings.py — pure pillar rating logic (no I/O)."""
import math
from datetime import date

import ratings


PILLAR_KEYS = {"speed", "stroke_length", "consistency", "endurance"}

# A solid breaststroke session (good across the board).
GOOD = {
    "mean_vel_ms": 1.30, "max_vel_ms": 2.8, "mean_trough_vel_ms": 0.3, "stroke_rate_spm": 50.0,
    "mean_dps_m": 1.60, "mean_impulse_m": 1.5, "mean_coast_fraction": 0.4,
    "cv_arm_peak_vel": 0.08, "cv_isi": 0.10, "fatigue_index_pct": 5.0,
    "segmentation_reliable": False,
}


def _pillar(result, key):
    return next(p for p in result["pillars"] if p["key"] == key)


class TestStructure:
    def test_four_pillars_present(self):
        r = ratings.rate_session(GOOD, None, "breaststroke")
        assert {p["key"] for p in r["pillars"]} == PILLAR_KEYS

    def test_rating_colors_exposed(self):
        r = ratings.rate_session(GOOD, None, "breaststroke")
        assert r["rating_colors"] == {"good": "#2d9e5f", "ok": "#d4860a", "needs_work": "#c0392b"}

    def test_kick_metrics_never_surface(self):
        m = {**GOOD, "pct_cycles_with_kick": 0.9, "mean_arm_kick_ratio": 1.2,
             "mean_arm_kick_delay_s": 0.3}
        r = ratings.rate_session(m, None, "breaststroke")
        leaked = []
        for p in r["pillars"]:
            keys = {p["primary"]["key"]} | {c["key"] for c in p["metrics"]}
            leaked += [k for k in keys if "kick" in k]
        assert leaked == []


class TestBands:
    def test_higher_is_better_bands(self):
        assert _pillar(ratings.rate_session({"mean_vel_ms": 1.30}, None, "breaststroke"), "speed")["band"] == "good"
        assert _pillar(ratings.rate_session({"mean_vel_ms": 0.90}, None, "breaststroke"), "speed")["band"] == "ok"
        assert _pillar(ratings.rate_session({"mean_vel_ms": 0.50}, None, "breaststroke"), "speed")["band"] == "needs_work"

    def test_lower_is_better_bands(self):
        # fatigue: good < 8, ok < 20
        assert _pillar(ratings.rate_session({"fatigue_index_pct": 4.0}, None, "breaststroke"), "endurance")["band"] == "good"
        assert _pillar(ratings.rate_session({"fatigue_index_pct": 15.0}, None, "breaststroke"), "endurance")["band"] == "ok"
        assert _pillar(ratings.rate_session({"fatigue_index_pct": 30.0}, None, "breaststroke"), "endurance")["band"] == "needs_work"

    def test_score_orders_with_band(self):
        good = _pillar(ratings.rate_session({"mean_vel_ms": 1.30}, None, "breaststroke"), "speed")["score"]
        ok = _pillar(ratings.rate_session({"mean_vel_ms": 0.90}, None, "breaststroke"), "speed")["score"]
        bad = _pillar(ratings.rate_session({"mean_vel_ms": 0.50}, None, "breaststroke"), "speed")["score"]
        assert 0 <= bad < ok < good <= 100

    def test_score_higher_for_better_even_when_lower_is_better(self):
        # endurance: lower fatigue must yield a HIGHER score
        better = _pillar(ratings.rate_session({"fatigue_index_pct": 2.0}, None, "breaststroke"), "endurance")["score"]
        worse = _pillar(ratings.rate_session({"fatigue_index_pct": 25.0}, None, "breaststroke"), "endurance")["score"]
        assert better > worse


class TestTrend:
    def test_first_session_when_no_baseline(self):
        r = ratings.rate_session(GOOD, None, "breaststroke")
        assert all(p["trend"] == "first_session" for p in r["pillars"])

    def test_improved_and_declined_direction_aware(self):
        cur = {"mean_vel_ms": 1.30, "fatigue_index_pct": 5.0}
        base = {"mean_vel_ms": 1.00, "fatigue_index_pct": 20.0}
        r = ratings.rate_session(cur, base, "breaststroke")
        # speed up = improved; fatigue down = improved
        assert _pillar(r, "speed")["trend"] == "improved"
        assert _pillar(r, "endurance")["trend"] == "improved"
        # now flip: speed down = declined; fatigue up = declined
        r2 = ratings.rate_session(base, cur, "breaststroke")
        assert _pillar(r2, "speed")["trend"] == "declined"
        assert _pillar(r2, "endurance")["trend"] == "declined"

    def test_steady_within_deadband(self):
        cur = {"mean_vel_ms": 1.20}
        base = {"mean_vel_ms": 1.21}  # ~0.8% < 5% deadband
        assert _pillar(ratings.rate_session(cur, base, "breaststroke"), "speed")["trend"] == "steady"

    def test_missing_baseline_metric_is_first_session(self):
        r = ratings.rate_session({"mean_vel_ms": 1.2}, {"mean_dps_m": 1.5}, "breaststroke")
        assert _pillar(r, "speed")["trend"] == "first_session"


class TestGatingAndSafety:
    def test_non_breaststroke_unknown_but_trend_computed(self):
        cur = {"mean_vel_ms": 1.30}
        base = {"mean_vel_ms": 1.0}
        r = ratings.rate_session(cur, base, "freestyle")
        sp = _pillar(r, "speed")
        assert sp["band"] == "unknown" and sp["score"] is None and sp["provisional"] is True
        assert sp["trend"] == "improved"  # trend-only still works

    def test_missing_primary_is_unknown_not_crash(self):
        r = ratings.rate_session({"segmentation_reliable": True}, None, "breaststroke")
        sp = _pillar(r, "speed")
        assert sp["band"] == "unknown" and sp["score"] is None

    def test_nan_primary_is_unknown(self):
        r = ratings.rate_session({"mean_vel_ms": float("nan")}, None, "breaststroke")
        assert _pillar(r, "speed")["band"] == "unknown"

    def test_provisional_follows_segmentation_flag(self):
        prov = ratings.rate_session({"mean_vel_ms": 1.3, "segmentation_reliable": False}, None, "breaststroke")
        trusted = ratings.rate_session({"mean_vel_ms": 1.3, "segmentation_reliable": True}, None, "breaststroke")
        assert _pillar(prov, "speed")["provisional"] is True
        assert _pillar(trusted, "speed")["provisional"] is False


class TestSelectBaseline:
    def test_previous_is_newest_prior(self):
        prior = [{"mean_vel_ms": 1.2}, {"mean_vel_ms": 1.0}]  # newest-first
        assert ratings.select_baseline(prior, "previous") == {"mean_vel_ms": 1.2}

    def test_first_is_earliest(self):
        prior = [{"mean_vel_ms": 1.2}, {"mean_vel_ms": 1.0}]
        assert ratings.select_baseline(prior, "first") == {"mean_vel_ms": 1.0}

    def test_recent_avg(self):
        prior = [{"mean_vel_ms": 1.2}, {"mean_vel_ms": 1.0}]
        assert ratings.select_baseline(prior, "recent_avg")["mean_vel_ms"] == 1.1

    def test_empty_is_none(self):
        assert ratings.select_baseline([], "previous") is None

    def test_unknown_mode_raises(self):
        import pytest
        with pytest.raises(ValueError):
            ratings.select_baseline([{"x": 1}], "bogus")


class TestSummarizeTeam:
    TODAY = date(2026, 6, 18)

    def _ath(self, aid, name, pillars, last_tested):
        return {"athlete_id": aid, "name": name, "stroke_type": "breaststroke",
                "last_session_id": f"s-{aid}", "last_tested": last_tested, "pillars": pillars}

    @staticmethod
    def _pl(band="good", trend="steady", provisional=False, key="speed", label="Speed"):
        return {"key": key, "label": label, "band": band, "trend": trend,
                "score": 50, "provisional": provisional}

    def test_distribution_counts_only_athletes_with_pillars(self):
        a1 = self._ath("1", "A", [self._pl(band="good")], "2026-06-17")
        a2 = self._ath("2", "B", [self._pl(band="needs_work")], "2026-06-17")
        a3 = self._ath("3", "C", [], None)  # no sessions → contributes nothing
        out = ratings.summarize_team([a1, a2, a3], self.TODAY)
        assert len(out["pillars"]) == 4   # all PILLARS present, in order
        speed = next(p for p in out["pillars"] if p["key"] == "speed")
        assert (speed["good"], speed["needs_work"], speed["ok"], speed["unknown"]) == (1, 1, 0, 0)

    def test_needs_work_and_declined_reasons(self):
        pillars = [self._pl(band="good", trend="declined", key="speed", label="Speed"),
                   self._pl(band="needs_work", trend="steady", key="consistency", label="Consistency")]
        out = ratings.summarize_team([self._ath("1", "A", pillars, "2026-06-17")], self.TODAY)
        types = {(r["type"], r.get("pillar")) for r in out["needs_attention"][0]["reasons"]}
        assert ("needs_work", "Consistency") in types
        assert ("declined", "Speed") in types

    def test_provisional_pillar_raises_no_alarm(self):
        pillars = [self._pl(band="needs_work", trend="declined", provisional=True)]
        out = ratings.summarize_team([self._ath("1", "A", pillars, "2026-06-17")], self.TODAY)
        assert out["needs_attention"] == []   # untrusted band/trend → no reason; recent → not stale

    def test_stale_reason(self):
        out = ratings.summarize_team(
            [self._ath("1", "A", [self._pl(band="good")], "2026-05-01")], self.TODAY)  # ~48d ago
        stale = [r for r in out["needs_attention"][0]["reasons"] if r["type"] == "stale"]
        assert stale and stale[0]["days"] > ratings.STALE_DAYS

    def test_never_tested(self):
        out = ratings.summarize_team([self._ath("1", "A", [], None)], self.TODAY)
        assert out["needs_attention"][0]["reasons"] == [{"type": "never_tested"}]

    def test_clean_athlete_omitted_and_sorted_by_reason_count(self):
        clean = self._ath("1", "Clean", [self._pl(band="good")], "2026-06-17")
        two = self._ath("2", "Two", [self._pl(band="needs_work", trend="declined")], "2026-06-17")
        one = self._ath("3", "One", [self._pl(band="needs_work", trend="steady")], "2026-06-17")
        out = ratings.summarize_team([clean, one, two], self.TODAY)
        names = [n["name"] for n in out["needs_attention"]]
        assert "Clean" not in names            # no reasons → omitted
        assert names == ["Two", "One"]         # 2 reasons before 1, ties broken by name
