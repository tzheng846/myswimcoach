"""drills.py — drill library + metric-driven recommender. Pure, no I/O.

This is the BRIDGE the chat uses for its call-to-action: a swimmer's session metrics produce
"problem flags", and each drill is tagged with the flags it addresses, so a recommendation is
grounded (metric problem -> drill that fixes it -> why) rather than invented.

DRAFT CONTENT: the drill descriptions, the metric->flag thresholds, and the flag->drill
mapping are a first expert-informed draft and should be reviewed/tuned by a real coach before
they are trusted in front of customers. Thresholds reuse coach.py's prose numbers where those
exist. Descriptions are written in our own words (no third-party library text is copied).
"""

# Canonical problem flags. Every drill targets one or more of these; flags_from_session emits them.
FLAGS = {
    "low_dps",            # short distance per stroke — not carrying momentum
    "low_trough_vel",     # velocity collapses between strokes — drag / dead spot
    "high_cv_isi",        # inconsistent stroke rhythm
    "inconsistent_power", # arm-pull peak varies a lot cycle to cycle
    "high_fatigue",       # speed fading across the swim — pacing / conditioning
    "passive_coast",      # lots of coasting WITHOUT distance — drifting, not gliding
}


DRILLS = [
    {
        "id": "streamline-glide-hold",
        "name": "Streamline Glide Hold",
        "how_to": "Push off in a tight streamline and hold the glide until you feel yourself "
                  "start to slow, then begin your stroke. Repeat, trying to ride each push a "
                  "little farther.",
        "targets": ["low_dps", "low_trough_vel"],
        "why": "When distance-per-stroke is low and speed collapses between strokes, momentum "
               "is leaking in the glide. Holding streamline trains you to ride the impulse longer.",
        "level": "all",
    },
    {
        "id": "dps-golf",
        "name": "Distance-Per-Stroke Golf",
        "how_to": "Swim a length counting strokes and noting your time; add them for your "
                  "'score'. Try to lower the score each round by taking longer, not faster, strokes.",
        "targets": ["low_dps"],
        "why": "Directly rewards covering more water per stroke, which is exactly what a low "
               "distance-per-stroke needs.",
        "level": "all",
    },
    {
        "id": "tempo-trainer-pace",
        "name": "Tempo Trainer Pacing",
        "how_to": "Set a tempo beeper (or count out loud) to a steady interval and start each "
                  "stroke on the beat, keeping the spacing identical every cycle.",
        "targets": ["high_cv_isi"],
        "why": "An external beat smooths out an inconsistent rhythm so each stroke comes at the "
               "same interval.",
        "level": "all",
    },
    {
        "id": "catch-up-timing",
        "name": "Catch-Up Timing",
        "how_to": "Let one hand wait extended out front until the other hand touches it before "
                  "starting the next pull, making each cycle deliberate and evenly spaced.",
        "targets": ["high_cv_isi"],
        "why": "Forces a consistent, repeatable cycle so the stroke-to-stroke timing stops drifting.",
        "level": "all",
    },
    {
        "id": "front-scull",
        "name": "Front Scull",
        "how_to": "Float face-down and make small, firm figure-eight sculls out front, feeling "
                  "constant pressure on the water against your forearm and hand.",
        "targets": ["inconsistent_power"],
        "why": "Builds a repeatable feel for the catch so each arm pull generates similar power "
               "instead of varying cycle to cycle.",
        "level": "all",
    },
    {
        "id": "negative-split-set",
        "name": "Negative-Split Set",
        "how_to": "Swim a distance aiming to make the second half FASTER than the first. Hold "
                  "something back early so you finish strong.",
        "targets": ["high_fatigue"],
        "why": "Trains pacing and late-swim strength directly against a velocity that fades as "
               "the swim goes on.",
        "level": "all",
    },
    {
        "id": "pace-clock-threshold",
        "name": "Pace-Clock Threshold Repeats",
        "how_to": "Swim repeats on a fixed send-off that gives short rest, holding the same "
                  "time on every repeat. Stop the set when you can no longer hold the time.",
        "targets": ["high_fatigue"],
        "why": "Builds the aerobic base that keeps speed from collapsing late in a swim.",
        "level": "intermediate",
    },
    {
        "id": "surge-glide-control",
        "name": "Surge-and-Glide Control",
        "how_to": "Take one strong, committed stroke, then ride the glide in a tight body line "
                  "before the next — make the glide WORK, covering real distance, not just drifting.",
        "targets": ["passive_coast", "low_dps"],
        "why": "Turns passive coasting (lots of glide time but little distance) into productive "
               "gliding that actually carries you forward.",
        "level": "all",
    },
]


def flags_from_session(session: dict) -> set:
    """Active problem flags for a session metrics dict. Thresholds are a DRAFT (see module
    docstring); coach.py prose numbers are reused where they exist. Missing metrics are skipped."""
    s = session or {}
    flags = set()

    def _num(key):
        v = s.get(key)
        return v if isinstance(v, (int, float)) else None

    dps     = _num("mean_dps_m")
    trough  = _num("mean_trough_vel_ms")
    cv_isi  = _num("cv_isi")
    cv_arm  = _num("cv_arm_peak_vel")
    fatigue = _num("fatigue_index_pct")
    coast   = _num("mean_coast_fraction")

    if dps is not None and dps < 1.5:
        flags.add("low_dps")
    if trough is not None and trough < 0.05:
        flags.add("low_trough_vel")
    if cv_isi is not None and cv_isi > 0.15:
        flags.add("high_cv_isi")
    if cv_arm is not None and cv_arm > 0.20:
        flags.add("inconsistent_power")
    if fatigue is not None and fatigue > 8:
        flags.add("high_fatigue")
    if coast is not None and dps is not None and coast > 0.5 and dps < 1.5:
        flags.add("passive_coast")

    return flags


def match_drills(flags, limit=3):
    """Drills whose targets intersect `flags`, ranked by overlap count (desc), stable. [] if none."""
    flags = set(flags or ())
    if not flags:
        return []
    scored = []
    for d in DRILLS:
        overlap = len(set(d["targets"]) & flags)
        if overlap:
            scored.append((overlap, d))
    scored.sort(key=lambda x: -x[0])  # stable: preserves DRILLS order within equal overlap
    return [d for _, d in scored[:limit]]
