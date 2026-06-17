"""roster_metrics.py — pure team-level aggregation over session rows. No I/O.

A "row" is a plain dict:
    {"athlete_id": str, "athlete_name": str, "date": "YYYY-MM-DD", "session": {metric: value}}

These functions are metric-agnostic and stroke-agnostic; api.py's /coach/chat team tools load
the coach's roster and call them. Kept pure (like metrics.py) so they're unit-testable.
"""


def latest_per_athlete(rows):
    """
    Select the most recent row for each athlete based on ISO date string ordering.
    
    Returns:
        list: Rows with the latest date for each unique athlete_id.
    """
    latest = {}
    for r in rows:
        aid = r.get("athlete_id")
        if aid is None:
            continue
        cur = latest.get(aid)
        if cur is None or (r.get("date") or "") > (cur.get("date") or ""):
            latest[aid] = r
    return list(latest.values())


def rank_athletes(rows, metric, ascending=True, limit=None):
    """
    Sort athletes by a specified session metric value.
    
    Rows without the metric are excluded. If ascending is True, results are ordered
    from lowest to highest; otherwise highest to lowest. If limit is provided, only
    the top limit entries are returned.
    
    Returns:
        list: Dicts with keys athlete_name, value (the metric value), and date.
    """
    scored = []
    for r in rows:
        val = (r.get("session") or {}).get(metric)
        if val is None:
            continue
        scored.append({"athlete_name": r.get("athlete_name"), "value": val, "date": r.get("date")})
    scored.sort(key=lambda x: x["value"], reverse=not ascending)
    if limit is not None and limit > 0:   # 0/negative → treat as no limit, never a weird slice
        scored = scored[:limit]
    return scored


def rank_progress(rows, metric, min_sessions=2):
    """
    Compute percent change in a metric from each athlete's earliest to latest session.
    
    Requires each athlete to have at least min_sessions sessions containing the metric.
    Athletes below this threshold are returned separately without progress computation.
    Percent change is set to None if the starting value is zero.
    
    Parameters:
        rows (list): List of row dicts with athlete_id, athlete_name, date, and session.
        metric (str): The metric name to track within each row's session dict.
        min_sessions (int): Minimum number of sessions with the metric required for progress computation. Defaults to 2.
    
    Returns:
        dict: Contains two keys:
            - "progressed": List of dicts (sorted by improvement, best first) with athlete_name,
              pct_change (float or None), from (dict with date and value), and to (dict with
              date and value).
            - "insufficient_data": List of dicts with athlete_name and sessions_with_metric count.
    """

    """Percent change in `metric` from each athlete's earliest to latest session with that metric.
    Athletes below min_sessions are returned separately — never given a fabricated trend."""
    min_sessions = max(min_sessions, 1)   # guard: <1 lets empty vals reach vals[0] (IndexError)
    by_ath = {}
    for r in rows:
        aid = r.get("athlete_id")
        if aid is None:
            continue
        by_ath.setdefault(aid, []).append(r)

    progressed, insufficient = [], []
    for arows in by_ath.values():
        name = arows[0].get("athlete_name")
        ordered = sorted(arows, key=lambda x: x.get("date") or "")
        vals = [(x.get("date"), (x.get("session") or {}).get(metric)) for x in ordered]
        vals = [(d, v) for d, v in vals if v is not None]
        if len(vals) < min_sessions:
            insufficient.append({"athlete_name": name, "sessions_with_metric": len(vals)})
            continue
        first_v, last_v = vals[0][1], vals[-1][1]
        pct = None if first_v == 0 else (last_v - first_v) / abs(first_v) * 100.0
        progressed.append({
            "athlete_name": name,
            "pct_change": pct,
            "from": {"date": vals[0][0], "value": first_v},
            "to": {"date": vals[-1][0], "value": last_v},
        })
    # Best improvement first; undefined (None) percentages sort last.
    progressed.sort(key=lambda x: (x["pct_change"] is None, -(x["pct_change"] or 0.0)))
    return {"progressed": progressed, "insufficient_data": insufficient}


def team_summary(rows, metrics):
    """
    Compute team-level statistics for specified metrics across each athlete's latest session.
    
    Parameters:
        rows: List of session row dicts containing athlete_id, athlete_name, date, and session metric values.
        metrics: Metric names to aggregate.
    
    Returns:
        dict: Dictionary with "athlete_count" and a "metrics" dict mapping each metric to mean, min, max, and count of non-None values.
    """
    latest = latest_per_athlete(rows)
    out = {"athlete_count": len(latest), "metrics": {}}
    for metric in metrics:
        vals = [(r.get("session") or {}).get(metric) for r in latest]
        vals = [v for v in vals if v is not None]
        if vals:
            out["metrics"][metric] = {
                "mean": sum(vals) / len(vals),
                "min": min(vals),
                "max": max(vals),
                "n": len(vals),
            }
    return out
