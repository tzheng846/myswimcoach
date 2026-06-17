"""Unit tests for drills — flag derivation + matching (33-03)."""

import drills


def test_library_well_formed():
    """Every drill has the required fields and only known target flags."""
    required = {"id", "name", "how_to", "targets", "why", "level"}
    ids = set()
    for d in drills.DRILLS:
        assert required <= set(d), f"{d.get('id')} missing fields"
        assert d["targets"], f"{d['id']} has no targets"
        assert set(d["targets"]) <= drills.FLAGS, f"{d['id']} has unknown flag"
        ids.add(d["id"])
    assert len(ids) == len(drills.DRILLS), "duplicate drill ids"


def test_every_flag_has_a_drill():
    covered = set()
    for d in drills.DRILLS:
        covered |= set(d["targets"])
    assert covered == drills.FLAGS, f"flags with no drill: {drills.FLAGS - covered}"


def test_flags_threshold_boundaries():
    assert "low_dps" in drills.flags_from_session({"mean_dps_m": 1.4})
    assert "low_dps" not in drills.flags_from_session({"mean_dps_m": 1.6})
    assert "high_cv_isi" in drills.flags_from_session({"cv_isi": 0.20})
    assert "high_cv_isi" not in drills.flags_from_session({"cv_isi": 0.10})
    assert "low_trough_vel" in drills.flags_from_session({"mean_trough_vel_ms": 0.02})
    assert "high_fatigue" in drills.flags_from_session({"fatigue_index_pct": 12})
    assert "inconsistent_power" in drills.flags_from_session({"cv_arm_peak_vel": 0.30})


def test_passive_coast_is_compound():
    # High coast alone is NOT passive — needs low dps too.
    assert "passive_coast" not in drills.flags_from_session({"mean_coast_fraction": 0.7, "mean_dps_m": 1.8})
    assert "passive_coast" in drills.flags_from_session({"mean_coast_fraction": 0.7, "mean_dps_m": 1.2})


def test_missing_metrics_produce_no_flags():
    assert drills.flags_from_session({}) == set()
    assert drills.flags_from_session({"mean_dps_m": None}) == set()


def test_match_ranks_by_overlap_and_handles_empty():
    assert drills.match_drills(set()) == []
    # A session flagged low_dps + low_trough_vel should surface the drill targeting BOTH first.
    matched = drills.match_drills({"low_dps", "low_trough_vel"})
    assert matched[0]["id"] == "streamline-glide-hold"
    assert all(set(d["targets"]) & {"low_dps", "low_trough_vel"} for d in matched)


def test_match_respects_limit():
    matched = drills.match_drills({"low_dps"}, limit=1)
    assert len(matched) == 1
