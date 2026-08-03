"""
annotations.py — trial-annotation seed building + validation (Phase 47).

Pure functions, no I/O (same convention as metrics.py / ratings.py). Shared source
of truth for the annotation contract served by api.py:

    {
      "phases": {
        "dive_start_s":       float | null,
        "underwater_start_s": float | null,   # displayed as "pulldown" for breaststroke
        "breakout_start_s":   float | null,
        "stroke_start_s":     float | null,
        "finish_s":           float | null,
      },
      "stroke_marks_s": [float, ...],          # sorted, individual stroke boundaries
      "source": "manual" | "seeded",
    }

Phase model (user decision, 2026-07-11): a trial is a SINGLE ORDERED PASS —
dive → underwater kick/pulldown → breakout → stroke → finish. Any subset of phases
may be annotated; present times must be non-decreasing in canonical order.
Times are seconds on the session's own clock (sample index / sample rate). The rate is
per session — `sessions.sample_rate_hz`, written by /process from the pipeline's real
decimated rate (Phase 52). Callers pass it as `fs_hz`; it is NOT 100 in practice.
"""

# Fallback rate only, for sessions recorded before Phase 52 that have no
# sample_rate_hz. Decimation is by an integer factor (round(268.5/100) = 3), so the
# real rate is ~89.5 Hz — never assume this constant for a session that has its own.
FS_HZ = 100

PHASE_KEYS = [
    "dive_start_s",
    "underwater_start_s",
    "breakout_start_s",
    "stroke_start_s",
    "finish_s",
]

SOURCES = ("manual", "seeded")


def _num(v):
    """Return v as float if it is a real (non-bool) finite number, else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    if f != f or f in (float("inf"), float("-inf")):  # NaN / inf
        return None
    return f


def _fs(fs_hz):
    """Coerce a caller-supplied sample rate to a usable positive float, else FS_HZ.

    Never raises and never returns 0 — a missing or malformed rate must degrade to the
    pre-Phase-52 behavior, not to a ZeroDivisionError inside a pure function.
    """
    f = _num(fs_hz)
    return f if f is not None and f > 0 else float(FS_HZ)


def build_seed(metrics_json, fs_hz=FS_HZ):
    """Best-effort draft annotation from a session's stored metrics_json.

    fs_hz is the session's own sample rate (sessions.sample_rate_hz); it defaults to the
    FS_HZ fallback for rows recorded before Phase 52.

    Sources (all optional — anything undetected stays null, never raises):
      dive_start_s       ← session.baseline_end_s (swim motion begins)
      underwater_start_s ← dive peak (baseline_end_s + initial_phase.dive_duration_s)
      breakout_start_s   ← null (no automatic detection exists)
      stroke_start_s     ← initial_phase.initial_phase_end_idx / fs, else first cycle start
      finish_s           ← last cycle end_idx / fs
      stroke_marks_s     ← each cycle's start_idx / fs (the 39-05 overlay convention)
    """
    fs = _fs(fs_hz)
    mj = metrics_json if isinstance(metrics_json, dict) else {}
    session = mj.get("session") if isinstance(mj.get("session"), dict) else {}
    initial = mj.get("initial_phase") if isinstance(mj.get("initial_phase"), dict) else {}
    cycles = mj.get("cycles") if isinstance(mj.get("cycles"), list) else []

    phases = {k: None for k in PHASE_KEYS}

    baseline_end_s = _num(session.get("baseline_end_s"))
    phases["dive_start_s"] = baseline_end_s

    dive_dur = _num(initial.get("dive_duration_s"))
    if initial.get("dive_detected") and baseline_end_s is not None and dive_dur is not None:
        phases["underwater_start_s"] = baseline_end_s + dive_dur

    ip_end_idx = _num(initial.get("initial_phase_end_idx"))
    if ip_end_idx is not None and ip_end_idx > 0:
        phases["stroke_start_s"] = ip_end_idx / fs

    marks = []
    last_end = None
    for c in cycles:
        if not isinstance(c, dict):
            continue
        start = _num(c.get("start_idx"))
        if start is not None:
            marks.append(start / fs)
        end = _num(c.get("end_idx"))
        if end is not None:
            last_end = end / fs
    marks.sort()

    if phases["stroke_start_s"] is None and marks:
        phases["stroke_start_s"] = marks[0]
    phases["finish_s"] = last_end

    # Seeded phases must themselves satisfy the ordering contract; detection stages are
    # independent and can disagree (e.g. a dive+duration underwater estimate landing after
    # the first cycle). Walk backwards so the cycle-derived anchors (stroke_start, finish)
    # win and the more speculative upstream estimates get dropped.
    next_val = None
    for k in reversed(PHASE_KEYS):
        v = phases[k]
        if v is None:
            continue
        if next_val is not None and v > next_val:
            phases[k] = None
        else:
            next_val = v

    return {"phases": phases, "stroke_marks_s": marks, "source": "seeded"}


def annotation_to_overrides(annotation, n_samples, fs_hz=FS_HZ):
    """Map an annotation doc to compute_session_metrics(manual=...) overrides (Phase 47).

    fs_hz must be the SAME rate build_seed used and the same one the UI displayed against,
    or marks land on a different sample than the coach clicked (Phase 52).

    Index convention: idx = round(time_s × fs_hz), clamped to [0, n_samples−1];
    swim_end_idx is an exclusive slice end (finish idx + 1). Cycle boundaries =
    stroke_marks_s plus finish_s when it lies beyond the last mark; consecutive
    boundary pairs become cycle_bounds — fewer than 2 boundaries → no cycle_bounds.
    Pure, never raises; malformed input yields {} or a partial dict.
    """
    if not isinstance(annotation, dict) or not isinstance(n_samples, int) or n_samples < 2:
        return {}
    fs = _fs(fs_hz)
    phases = annotation.get("phases")
    phases = phases if isinstance(phases, dict) else {}

    def to_idx(time_s):
        return min(max(int(round(time_s * fs)), 0), n_samples - 1)

    out = {}
    dive = _num(phases.get("dive_start_s"))
    if dive is not None:
        out["baseline_end_idx"] = to_idx(dive)
    stroke = _num(phases.get("stroke_start_s"))
    if stroke is not None:
        out["ip_end_idx"] = to_idx(stroke)
    finish = _num(phases.get("finish_s"))
    if finish is not None:
        out["swim_end_idx"] = min(to_idx(finish) + 1, n_samples)

    raw_marks = annotation.get("stroke_marks_s")
    marks = sorted(
        m for m in (_num(v) for v in (raw_marks if isinstance(raw_marks, list) else []))
        if m is not None
    )
    boundaries = list(marks)
    if finish is not None and (not boundaries or finish > boundaries[-1]):
        boundaries.append(finish)

    idxs = []
    for b in boundaries:
        i = to_idx(b)
        if not idxs or i > idxs[-1]:
            idxs.append(i)
    bounds = [
        (idxs[i], idxs[i + 1])
        for i in range(len(idxs) - 1)
        if idxs[i + 1] - idxs[i] >= 2
    ]
    if bounds:
        out["cycle_bounds"] = bounds
    return out


def validate_annotation(doc, duration_s=None):
    """Validate an annotation doc. Returns a list of error strings (empty = valid).

    Light-touch by design: any subset of phases is fine, stroke marks are not
    required to sit inside the stroke phase span. Rejects only structural problems —
    unknown phase keys, non-numeric/negative/out-of-range times, phases out of
    canonical order, unsorted stroke marks, bad source.
    """
    errors = []
    if not isinstance(doc, dict):
        return ["annotation body must be a JSON object"]

    phases = doc.get("phases", {})
    if not isinstance(phases, dict):
        errors.append("phases must be an object")
        phases = {}

    for key in phases:
        if key not in PHASE_KEYS:
            errors.append(f"unknown phase key: {key}")

    def check_time(label, v):
        if v is None:
            return None
        f = _num(v)
        if f is None:
            errors.append(f"{label} must be a number")
            return None
        if f < 0:
            errors.append(f"{label} must be >= 0")
            return None
        if duration_s is not None and duration_s > 0 and f > duration_s:
            errors.append(f"{label} exceeds session duration ({duration_s:.2f} s)")
            return None
        return f

    prev_key, prev_val = None, None
    for key in PHASE_KEYS:
        f = check_time(key, phases.get(key))
        if f is None:
            continue
        if prev_val is not None and f < prev_val:
            errors.append(f"{key} must not precede {prev_key}")
        prev_key, prev_val = key, f

    marks = doc.get("stroke_marks_s", [])
    if not isinstance(marks, list):
        errors.append("stroke_marks_s must be an array")
        marks = []
    prev_mark = None
    for i, v in enumerate(marks):
        f = check_time(f"stroke_marks_s[{i}]", v)
        if f is None:
            continue
        if prev_mark is not None and f < prev_mark:
            errors.append(f"stroke_marks_s[{i}] is out of order")
        prev_mark = f

    source = doc.get("source", "manual")
    if source not in SOURCES:
        errors.append(f"source must be one of {list(SOURCES)}")

    return errors
