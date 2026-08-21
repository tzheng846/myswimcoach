"""annotated_roster.py — read-only swimmer census + annotation-coverage gap (Phase 78).

Every segmentation number the project quotes (Phase 59 cycle F1s, 75-02 underwater 0.13 s,
76/77 breakout) is stamped "ONE SWIMMER." STATE.md item 2 flagged that the labeled data
should span more people. This probe answers the prerequisite question before trusting any
detector on real teams: how many DISTINCT swimmers does the scored corpus actually cover,
and how many swimmers' sessions exist in the DB but were never annotated (so no scorer ever
sees them)?

Two halves:
  A. ANNOTATED CENSUS  — the corpus every scorer fetches (session_annotations ⋈ sessions ⋈
     athletes): totals, per-stroke swimmer counts, and each annotated session by athlete.
  B. FULL-ROSTER COVERAGE — ALL sessions vs the annotated subset, per athlete, so the
     unannotated swimmers are impossible to miss. Includes the AlexGroup expansion: that
     athlete row is a STAND-IN whose per-session NAMES are individual testers.

The three scorers deliberately print NO athlete PII (id prefix + stroke only). Identity
lives ONLY here. Read-only Supabase (service-role key from .env), same discipline as
tools/score_underwater.py / tools/breakout_band_probe.py: no write/update/delete.

    python tools/annotated_roster.py
    python tools/annotated_roster.py --json scratch/roster.json   # emit id->swimmer map
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# The local supabase/ folder (SQL migrations) shadows the installed supabase-py package
# when running from the repo root — drop bare-path entries before importing, exactly as
# score_underwater.py:27 / breakout_band_probe.py:38 do.
sys.path = [p for p in sys.path if p not in ("", ".")]

from dotenv import load_dotenv          # noqa: E402
from supabase import create_client      # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

# Athlete rows that are STAND-INS: one athlete_id fronting many individual testers, whose
# identities live in the per-session `name` column, not in the athlete row. Confirmed for
# "AlexGroup" (session names Henry / Ben / Desi / ... ). Matched case-insensitively.
_STANDIN_RE = re.compile(r"alex|group", re.IGNORECASE)


def _client():
    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


def _athletes(sb):
    """{athlete_id: name}. A missing/odd athletes schema degrades to {} (non-fatal)."""
    try:
        return {a["id"]: (a.get("name") or "")
                for a in (sb.table("athletes").select("id, name").execute().data or [])}
    except Exception:
        return {}


def _load_annotated(sb, names):
    """Annotated sessions joined to sessions.athlete_id and athletes.name."""
    anns = (sb.table("session_annotations")
              .select("session_id, phases, stroke_marks_s, source")
              .execute().data) or []
    if not anns:
        sys.exit("No annotated sessions found.")
    ann_by_id = {a["session_id"]: a for a in anns}
    rows = (sb.table("sessions")
              .select("id, name, stroke_type, athlete_id, created_at")
              .in_("id", list(ann_by_id)).execute().data) or []
    sess_by_id = {r["id"]: r for r in rows}

    out = []
    for sid, ann in ann_by_id.items():
        sess = sess_by_id.get(sid)
        if not sess:
            out.append({"session_id": sid, "athlete_id": None, "athlete": "(no session row)",
                        "name": "", "stroke": "?", "created_at": "", "n_marks": 0})
            continue
        aid = sess.get("athlete_id")
        label = names.get(aid) or (aid[:8] if aid else "(no athlete_id)")
        out.append({
            "session_id": sid, "athlete_id": aid, "athlete": label,
            "name": sess.get("name") or "", "stroke": sess.get("stroke_type") or "?",
            "created_at": (sess.get("created_at") or "")[:19].replace("T", " "),
            "n_marks": len(ann.get("stroke_marks_s") or []),
        })
    return out


def _all_sessions(sb):
    return (sb.table("sessions")
              .select("id, name, stroke_type, athlete_id, created_at")
              .execute().data) or []


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", help="also write an id->swimmer map here (for Task 2 tagging)")
    args = ap.parse_args()

    sb = _client()
    names = _athletes(sb)
    recs = _load_annotated(sb, names)
    n = len(recs)

    ids_present = [r for r in recs if r["athlete_id"]]
    distinct_aid = {r["athlete_id"] for r in ids_present}

    # ── A. ANNOTATED CENSUS ────────────────────────────────────────────────────
    print("=" * 78)
    print("A. ANNOTATED-CORPUS SWIMMER CENSUS  (what every scorer fetches)")
    print("=" * 78)
    print(f"Annotated sessions: {n}   |   distinct annotated swimmers: {len(distinct_aid)}")

    by_stroke = defaultdict(lambda: {"sessions": 0, "athletes": set()})
    for r in recs:
        b = by_stroke[r["stroke"]]
        b["sessions"] += 1
        if r["athlete_id"]:
            b["athletes"].add(r["athlete"])
    print(f"\nPER-STROKE  (distinct annotated swimmers):")
    print(f"  {'stroke':<14}{'sessions':>9}{'swimmers':>10}  who")
    for stroke in sorted(by_stroke):
        b = by_stroke[stroke]
        print(f"  {stroke:<14}{b['sessions']:>9}{len(b['athletes']):>10}  "
              f"{', '.join(sorted(b['athletes']))}")

    by_ath = defaultdict(list)
    for r in recs:
        by_ath[r["athlete"]].append(r)
    print(f"\nSESSIONS BY ATHLETE (annotated only)")
    for ath in sorted(by_ath, key=lambda a: (-len(by_ath[a]), a.lower())):
        rows = sorted(by_ath[ath], key=lambda r: r["created_at"])
        print(f"\n  [{ath}]  n={len(rows)}")
        print(f"    {'created':<20}{'stroke':<13}{'marks':>6}  name")
        for r in rows:
            print(f"    {r['created_at']:<20}{r['stroke']:<13}{r['n_marks']:>6}  {r['name']}")

    # ── B. FULL-ROSTER COVERAGE ────────────────────────────────────────────────
    sess = _all_sessions(sb)
    ann_ids = {r["session_id"] for r in recs}
    cov = defaultdict(lambda: {"total": 0, "ann": 0, "strokes": defaultdict(int), "rows": []})
    for s in sess:
        aid = s.get("athlete_id")
        lbl = names.get(aid) or (aid[:8] if aid else "(no athlete_id)")
        c = cov[lbl]
        c["total"] += 1
        c["strokes"][s.get("stroke_type") or "?"] += 1
        c["rows"].append(s)
        if s["id"] in ann_ids:
            c["ann"] += 1

    ann_swimmers = sum(1 for c in cov.values() if c["ann"] > 0)
    pct = (100.0 * len(ann_ids) / len(sess)) if sess else 0.0
    print(f"\n{'=' * 78}")
    print("B. FULL-ROSTER ANNOTATION COVERAGE  (ALL sessions, not just annotated)")
    print("=" * 78)
    print(f"Sessions: {len(sess)} total | annotated: {len(ann_ids)} ({pct:.0f}%) | "
          f"athletes with >=1 annotation: {ann_swimmers} of {len(cov)}")
    print(f"\n  {'athlete':<16}{'total':>6}{'annot':>6}{'unlab':>6}   strokes (total)")
    for lbl in sorted(cov, key=lambda l: -cov[l]["total"]):
        c = cov[lbl]
        st = " ".join(f"{k}:{v}" for k, v in sorted(c["strokes"].items()))
        flag = "  <- UNANNOTATED" if c["ann"] == 0 else ""
        print(f"  {lbl:<16}{c['total']:>6}{c['ann']:>6}{c['total'] - c['ann']:>6}   {st}{flag}")

    gap = {lbl: c for lbl, c in cov.items() if c["ann"] == 0 and c["total"] > 0}
    if gap:
        n_gap_sess = sum(c["total"] for c in gap.values())
        print(f"\nUNANNOTATED SWIMMERS - {len(gap)} athletes, {n_gap_sess} sessions the scorers never see:")
        for lbl in sorted(gap, key=lambda l: -gap[l]["total"]):
            standin = " (STAND-IN: session names are individual testers -> expanded below)" \
                if _STANDIN_RE.search(lbl) else ""
            print(f"  {lbl:<16}{gap[lbl]['total']:>3} sessions{standin}")

    # AlexGroup expansion: the stand-in's per-session names ARE the individual testers.
    for lbl, c in cov.items():
        if not _STANDIN_RE.search(lbl):
            continue
        print(f"\n{lbl.upper()} EXPANSION (stand-in; each session name = a different tester):")
        print(f"  {'created':<20}{'stroke':<13}  name (verbatim = the tester)")
        for s in sorted(c["rows"], key=lambda s: (s.get("created_at") or "")):
            when = (s.get("created_at") or "")[:19].replace("T", " ")
            print(f"  {when:<20}{(s.get('stroke_type') or '?'):<13}  {s.get('name') or '(no name)'}")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        m = {r["session_id"]: {"athlete": r["athlete"], "name": r["name"],
                               "stroke": r["stroke"], "created_at": r["created_at"]}
             for r in recs}
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=1)
        print(f"\nid->swimmer map -> {args.json}")


if __name__ == "__main__":
    main()
