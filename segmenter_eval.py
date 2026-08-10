"""
segmenter_eval.py — scoring a segmenter against human ground truth (Phase 59).

Pure functions, no I/O (same convention as metrics.py / ratings.py / annotations.py).
The CLI that feeds this module lives in tools/score_segmenter.py.

WHY THIS EXISTS
---------------
`metrics.py` sets ``segmentation_reliable = False`` as a hardcoded constant. It has never
been a measurement: Phase 16-05 shipped the wavelet segmenter to production for all four
strokes at self-declared "placeholder quality" and nothing since could quantify that.
This module is the missing instrument — given predicted event times and human-annotated
event times, it says how well they agree.

WHAT IT SCORES
--------------
A *series* is any named sequence of event times in seconds: cycle boundaries, arm entries,
a single phase marker. Nothing here knows what the events mean, which is deliberate —
underwater-kick segmentation is coming (Phase 59 CONTEXT D11) and must be a caller change,
not a rewrite of this file.

MATCHING IS OPTIMAL, NOT GREEDY
-------------------------------
`match_series` solves a minimum-cost assignment (``scipy.optimize.linear_sum_assignment``)
rather than walking the predictions and taking the nearest free truth. A greedy matcher is
order-dependent and *undercounts*: with truth [0.00, 0.10] and predictions [0.09, 0.20] at
tol 0.12, greedy pairs 0.09 with 0.10 (its nearest) and then strands 0.20, reporting one
match where two legitimately exist. Phase 59's preliminary numbers were produced greedily
and must not be reproduced that way. See ``test_optimal_beats_greedy``.

A NOTE ON WHAT A SCORE MEANS HERE
---------------------------------
The Phase-59 corpus is ONE swimmer, one pool, one device. These numbers describe how well a
segmenter tracks that person. They are a change-detector, not a definition of correctness.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment

# Cost assigned to a pred/truth pairing that exceeds the tolerance. Must be finite —
# linear_sum_assignment raises on an infeasible (inf-containing) matrix rather than
# solving around it. Pairs landing on this sentinel are filtered out after solving.
_INFEASIBLE = 1e9


def _clean(times):
    """Sorted list of finite floats. Never raises; drops anything non-numeric."""
    out = []
    for v in times if times is not None else []:
        if isinstance(v, bool):
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if np.isfinite(f):
            out.append(f)
    out.sort()
    return out


def match_series(pred_s, truth_s, tol_s):
    """Optimally match predicted event times to truth times within tol_s.

    Returns (pairs, unmatched_pred, unmatched_truth) where pairs is a list of
    (pred_time, truth_time, abs_error) sorted by truth time. Each prediction matches at
    most one truth and vice versa, so a duplicated prediction consumes only one truth.
    """
    pred = _clean(pred_s)
    truth = _clean(truth_s)
    if not pred or not truth or tol_s is None or tol_s <= 0:
        return [], list(pred), list(truth)

    p = np.asarray(pred, dtype=float)[:, None]
    t = np.asarray(truth, dtype=float)[None, :]
    cost = np.abs(p - t)
    cost = np.where(cost <= float(tol_s), cost, _INFEASIBLE)

    rows, cols = linear_sum_assignment(cost)

    pairs = []
    used_p, used_t = set(), set()
    for i, j in zip(rows, cols):
        if cost[i, j] >= _INFEASIBLE:
            continue  # assignment filled a slot with an out-of-tolerance pairing
        pairs.append((pred[i], truth[j], float(cost[i, j])))
        used_p.add(i)
        used_t.add(j)

    pairs.sort(key=lambda x: x[1])
    unmatched_pred = [v for i, v in enumerate(pred) if i not in used_p]
    unmatched_truth = [v for j, v in enumerate(truth) if j not in used_t]
    return pairs, unmatched_pred, unmatched_truth


def score_series(pred_s, truth_s, tol_s):
    """Precision / recall / F1 / timing error for one series against its truth.

    An empty prediction or truth list yields zeros, never NaN and never a division error —
    a segmenter that returns None for a session must score as "found nothing", not crash
    the run. ``mae_s`` and ``bias_s`` are None when nothing matched, because the mean of an
    empty set is not zero.
    """
    pred = _clean(pred_s)
    truth = _clean(truth_s)
    pairs, _, _ = match_series(pred, truth, tol_s)

    n_pred, n_truth, matched = len(pred), len(truth), len(pairs)
    precision = matched / n_pred if n_pred else 0.0
    recall = matched / n_truth if n_truth else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    errs = [abs_err for _, _, abs_err in pairs]
    signed = [p - t for p, t, _ in pairs]
    return {
        "n_pred": n_pred,
        "n_truth": n_truth,
        "matched": matched,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mae_s": float(np.mean(errs)) if errs else None,
        "bias_s": float(np.mean(signed)) if signed else None,
        "tol_s": float(tol_s),
    }


def sweep(pred_s, truth_s, tolerances):
    """score_series at each tolerance. The shape of the curve says whether a segmenter is
    finding the right events slightly late (scores climb with tolerance) or finding the
    wrong events entirely (scores stay flat)."""
    return [score_series(pred_s, truth_s, tol) for tol in tolerances]


def coverage(marks_s, window_start_s, window_end_s):
    """How much of the swim window a set of marks actually covers (Phase 59 CONTEXT D4).

    ratio = n_marks / (window_span / median_ISI) — i.e. observed marks over the number a
    uniformly-labeled window would hold at the labeller's own observed tempo. ~1.0 means
    complete; 0.5 means half the swim was left unlabeled.

    This exists because a PARTIALLY labeled session makes a CORRECT detection look like a
    false positive, so precision is meaningless on it. The statistic is a heuristic: it
    detects under-labeling that leaves a gap, and would NOT catch evenly-spaced skipping
    (which inflates the median ISI along with the window estimate). Always report it
    alongside the exclusion it justified rather than applying it silently.

    Fewer than 3 marks → ratio None. A 2-point ISI is not a tempo estimate.
    """
    marks = _clean(marks_s)
    out = {
        "n_marks": len(marks),
        "median_isi_s": None,
        "window_s": None,
        "expected_marks": None,
        "ratio": None,
    }
    if len(marks) >= 3:
        out["median_isi_s"] = float(np.median(np.diff(marks)))
    if window_start_s is not None and window_end_s is not None:
        span = float(window_end_s) - float(window_start_s)
        if span > 0:
            out["window_s"] = span
    if out["median_isi_s"] and out["median_isi_s"] > 0 and out["window_s"]:
        expected = out["window_s"] / out["median_isi_s"]
        out["expected_marks"] = float(expected)
        if expected > 0:
            out["ratio"] = len(marks) / expected
    return out


def aggregate(rows, exclude_ids=(), group_key="stroke_type"):
    """Roll per-session scores up by group (stroke by default).

    Each row is {"session_id": str, group_key: str, "score": <score_series result>}.

    Excluded sessions (CONTEXT D4 — partially labeled) contribute to ``recall_all`` ONLY.
    ``precision`` / ``recall`` / ``f1`` are computed over the INCLUDED subset alone, because
    a precision drawn from one population and a recall drawn from another do not combine
    into a meaningful F1. Both are reported so the effect of the exclusion is visible
    rather than silent.
    """
    excluded = set(exclude_ids or ())
    groups = {}
    for row in rows:
        g = row.get(group_key) or "unknown"
        s = row.get("score") or {}
        acc = groups.setdefault(g, {
            "n_sessions": 0, "n_excluded": 0,
            "inc_pred": 0, "inc_truth": 0, "inc_matched": 0,
            "all_truth": 0, "all_matched": 0,
            "_errs": [], "excluded_ids": [],
        })
        acc["n_sessions"] += 1
        acc["all_truth"] += s.get("n_truth", 0)
        acc["all_matched"] += s.get("matched", 0)
        if row.get("session_id") in excluded:
            acc["n_excluded"] += 1
            acc["excluded_ids"].append(row.get("session_id"))
            continue
        acc["inc_pred"] += s.get("n_pred", 0)
        acc["inc_truth"] += s.get("n_truth", 0)
        acc["inc_matched"] += s.get("matched", 0)
        if s.get("mae_s") is not None and s.get("matched"):
            acc["_errs"].append((s["mae_s"], s["matched"]))

    out = {}
    for g, a in groups.items():
        precision = a["inc_matched"] / a["inc_pred"] if a["inc_pred"] else 0.0
        recall = a["inc_matched"] / a["inc_truth"] if a["inc_truth"] else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        wsum = sum(n for _, n in a["_errs"])
        out[g] = {
            "n_sessions": a["n_sessions"],
            "n_excluded": a["n_excluded"],
            "excluded_ids": a["excluded_ids"],
            "n_pred": a["inc_pred"],
            "n_truth": a["inc_truth"],
            "matched": a["inc_matched"],
            "precision": precision,
            "recall": recall,
            "f1": f1,
            # Weighted by matched count so a 17-mark session outweighs a 5-mark one.
            "mae_s": (sum(m * n for m, n in a["_errs"]) / wsum) if wsum else None,
            "recall_all": (a["all_matched"] / a["all_truth"]) if a["all_truth"] else 0.0,
            "n_truth_all": a["all_truth"],
        }
    return out
