"""Unit tests for roster_metrics — pure team aggregation (33-02)."""

import roster_metrics as rm


def _row(aid, name, date, **metrics):
    return {"athlete_id": aid, "athlete_name": name, "date": date, "session": metrics}


def test_latest_per_athlete_picks_newest():
    rows = [
        _row("a", "Maria", "2026-06-01", mean_dps_m=1.0),
        _row("a", "Maria", "2026-06-14", mean_dps_m=1.3),
        _row("b", "Sam", "2026-06-10", mean_dps_m=1.1),
    ]
    latest = {r["athlete_id"]: r for r in rm.latest_per_athlete(rows)}
    assert latest["a"]["date"] == "2026-06-14"
    assert latest["a"]["session"]["mean_dps_m"] == 1.3
    assert latest["b"]["date"] == "2026-06-10"


def test_rank_ascending_and_descending():
    rows = [
        _row("a", "Maria", "2026-06-14", mean_dps_m=1.4),
        _row("b", "Sam", "2026-06-14", mean_dps_m=1.0),
        _row("c", "Kai", "2026-06-14", mean_dps_m=1.2),
    ]
    asc = rm.rank_athletes(rows, "mean_dps_m", ascending=True)
    assert [r["athlete_name"] for r in asc] == ["Sam", "Kai", "Maria"]
    desc = rm.rank_athletes(rows, "mean_dps_m", ascending=False)
    assert [r["athlete_name"] for r in desc] == ["Maria", "Kai", "Sam"]


def test_rank_drops_missing_metric_and_respects_limit():
    rows = [
        _row("a", "Maria", "2026-06-14", mean_dps_m=1.4),
        _row("b", "Sam", "2026-06-14"),  # no mean_dps_m
        _row("c", "Kai", "2026-06-14", mean_dps_m=1.2),
    ]
    ranked = rm.rank_athletes(rows, "mean_dps_m", ascending=True, limit=1)
    assert [r["athlete_name"] for r in ranked] == ["Kai"]
    assert all("athlete_name" in r for r in ranked)


def test_progress_sign_and_values():
    rows = [
        _row("a", "Maria", "2026-06-01", mean_dps_m=1.0),
        _row("a", "Maria", "2026-06-14", mean_dps_m=1.3),
    ]
    out = rm.rank_progress(rows, "mean_dps_m", min_sessions=2)
    assert out["insufficient_data"] == []
    p = out["progressed"][0]
    assert p["athlete_name"] == "Maria"
    assert round(p["pct_change"], 1) == 30.0
    assert p["from"]["value"] == 1.0 and p["to"]["value"] == 1.3


def test_progress_excludes_thin_data():
    rows = [
        _row("a", "Maria", "2026-06-01", mean_dps_m=1.0),
        _row("a", "Maria", "2026-06-14", mean_dps_m=1.3),
        _row("b", "Sam", "2026-06-14", mean_dps_m=1.1),  # only one session
    ]
    out = rm.rank_progress(rows, "mean_dps_m", min_sessions=2)
    names = [p["athlete_name"] for p in out["progressed"]]
    assert names == ["Maria"]
    assert out["insufficient_data"] == [{"athlete_name": "Sam", "sessions_with_metric": 1}]


def test_progress_nonpositive_min_sessions_does_not_crash():
    # min_sessions<1 used to let an empty metric list reach vals[0] → IndexError.
    rows = [
        _row("a", "Maria", "2026-06-01"),   # no mean_dps_m at all
        _row("a", "Maria", "2026-06-14"),
    ]
    out = rm.rank_progress(rows, "mean_dps_m", min_sessions=0)
    assert out["progressed"] == []
    assert out["insufficient_data"] == [{"athlete_name": "Maria", "sessions_with_metric": 0}]


def test_rank_athletes_nonpositive_limit_returns_all():
    rows = [
        _row("a", "Maria", "2026-06-14", mean_dps_m=1.4),
        _row("b", "Sam", "2026-06-14", mean_dps_m=1.0),
    ]
    assert len(rm.rank_athletes(rows, "mean_dps_m", limit=0)) == 2
    assert len(rm.rank_athletes(rows, "mean_dps_m", limit=-1)) == 2


def test_team_summary_aggregates_latest():
    rows = [
        _row("a", "Maria", "2026-06-01", mean_dps_m=1.0),
        _row("a", "Maria", "2026-06-14", mean_dps_m=1.4),  # latest used
        _row("b", "Sam", "2026-06-14", mean_dps_m=1.0),
    ]
    s = rm.team_summary(rows, ["mean_dps_m"])
    assert s["athlete_count"] == 2
    m = s["metrics"]["mean_dps_m"]
    assert m["n"] == 2
    assert m["max"] == 1.4 and m["min"] == 1.0
    assert round(m["mean"], 2) == 1.2
