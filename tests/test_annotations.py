"""Tests for the Phase 47 trial-annotation contract — annotations.py (pure) +
the /sessions/{id}/annotations + video endpoints (supabase mocked, no network)."""
import io
from unittest.mock import MagicMock

import numpy as np
import pytest

import annotations as annot


# ── Fixtures ──────────────────────────────────────────────────────────────────

METRICS_JSON = {
    "session": {"baseline_end_s": 1.2, "lap_time_s": 30.0},
    "initial_phase": {
        "initial_phase_end_idx": 450,
        "dive_detected": True,
        "dive_duration_s": 0.8,
        "pulldown_detected": True,
    },
    "cycles": [
        {"cycle_num": 0, "start_idx": 500, "end_idx": 700},
        {"cycle_num": 1, "start_idx": 700, "end_idx": 910},
    ],
    "data_quality": {"magnet_dropout_pct": 3.5, "warnings": ["kick metrics unreliable"]},
}

# Realistic 30 s @ 100 Hz profiles so the recompute path exercises the real pipeline
_N = 3000
_t_fix = np.arange(_N) / 100.0
_vel_fix = np.maximum(0.8 + 0.4 * np.sin(2 * np.pi * 0.5 * _t_fix), 0.05)
_dist_fix = np.concatenate([[0.0], np.cumsum(_vel_fix[:-1] / 100.0)])

SESSION_ROW = {
    "id": "sess-1",
    "metrics_json": METRICS_JSON,
    "metrics_json_auto": None,
    "velocity_profile": _vel_fix.tolist(),  # 30.0 s at 100 Hz
    "distance_profile": _dist_fix.tolist(),
    "stroke_type": "breaststroke",
    "created_at": "2026-07-01T00:00:00Z",
    "raw_csv_path": "ath-1/123.csv",
    "video_path": None,
    "video_origin_s": None,
}

ANNOTATION_ROW = {
    "phases": {"dive_start_s": 1.0, "stroke_start_s": 4.0, "finish_s": 9.0},
    "stroke_marks_s": [5.0, 6.1, 7.3],
    "source": "manual",
    "updated_at": "2026-07-11T00:00:00Z",
}


def _annot_admin(session_row=SESSION_ROW, annotation_row=None, coach_id="coach-1"):
    """Fake supabase admin for the annotation/video endpoints. Query data is
    list-shaped (endpoints use .limit(1) + data[0], the ratings pattern).
    Table mocks are memoized on the admin so tests can assert on calls."""
    admin = MagicMock()
    admin._tables = {}

    def table(name):
        if name in admin._tables:
            return admin._tables[name]
        t = MagicMock()
        result = MagicMock()
        if name == "coaches":
            result.data = [{"id": coach_id}] if coach_id else []
        elif name == "sessions":
            result.data = [session_row] if session_row else []
        elif name == "session_annotations":
            result.data = [annotation_row] if annotation_row else []
        for method in ("select", "eq", "limit", "update", "upsert", "delete", "in_"):
            getattr(t, method).return_value = t
        t.execute.return_value = result
        admin._tables[name] = t
        return t

    admin.table.side_effect = table
    admin.storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://signed.example/videos/sess-1.mp4"
    }
    return admin


AUTH = {"Authorization": "Bearer fake-token-mocked"}


# ── annotations.py (pure) ─────────────────────────────────────────────────────

class TestBuildSeed:
    def test_representative_metrics(self):
        seed = annot.build_seed(METRICS_JSON)
        p = seed["phases"]
        assert p["dive_start_s"] == pytest.approx(1.2)
        assert p["underwater_start_s"] == pytest.approx(2.0)  # baseline + dive duration
        assert "breakout_start_s" not in p  # retired from the contract (Phase 58 D7a)
        assert p["stroke_start_s"] == pytest.approx(4.5)  # initial_phase_end_idx / 100
        assert p["finish_s"] == pytest.approx(9.1)  # last cycle end_idx / 100
        assert seed["stroke_marks_s"] == [5.0, 7.0]
        assert seed["stroke_marks_s"] == sorted(seed["stroke_marks_s"])
        assert seed["source"] == "seeded"

    @pytest.mark.parametrize("mj", [None, {}, {"session": None, "cycles": "junk"}])
    def test_missing_or_malformed_metrics_all_null(self, mj):
        seed = annot.build_seed(mj)
        assert all(v is None for v in seed["phases"].values())
        assert seed["stroke_marks_s"] == []

    def test_stored_boundary_wins_over_the_dive_peak(self):
        """Phase 75-02: a row that carries phases.boundaries seeds from the detector."""
        mj = {**METRICS_JSON,
              "phases": {"boundaries": {"underwater_start_s": 3.4}}}
        p = annot.build_seed(mj)["phases"]
        assert p["underwater_start_s"] == pytest.approx(3.4)   # not 2.0, the dive peak

    def test_falls_back_to_the_dive_peak_without_a_phases_key(self):
        """Every session recorded before 75-01 has no phases key at all."""
        assert "phases" not in METRICS_JSON
        p = annot.build_seed(METRICS_JSON)["phases"]
        assert p["underwater_start_s"] == pytest.approx(2.0)

    @pytest.mark.parametrize("boundaries", [None, {}, "junk", {"underwater_start_s": None},
                                            {"underwater_start_s": "3.4"}])
    def test_malformed_stored_boundary_falls_back(self, boundaries):
        mj = {**METRICS_JSON, "phases": {"boundaries": boundaries}}
        p = annot.build_seed(mj)["phases"]
        assert p["underwater_start_s"] == pytest.approx(2.0)

    def test_stored_boundary_still_obeys_the_ordering_walk(self):
        """A stored value that would land after stroke_start is dropped like any other."""
        mj = {**METRICS_JSON,
              "phases": {"boundaries": {"underwater_start_s": 99.0}}}
        p = annot.build_seed(mj)["phases"]
        assert p["underwater_start_s"] is None
        assert p["stroke_start_s"] == pytest.approx(4.5)

    def test_stored_dive_start_wins_over_baseline_end(self):
        """Phase 79: a row that carries phases.boundaries.dive_start_s seeds from the
        foot-of-surge detector, not from motion-onset baseline_end (1.2)."""
        mj = {**METRICS_JSON,
              "phases": {"boundaries": {"dive_start_s": 0.7}}}
        p = annot.build_seed(mj)["phases"]
        assert p["dive_start_s"] == pytest.approx(0.7)

    def test_dive_start_falls_back_to_baseline_end_without_a_phases_key(self):
        """Pre-79 rows have no phases key → dive_start keeps motion-onset baseline_end."""
        assert "phases" not in METRICS_JSON
        p = annot.build_seed(METRICS_JSON)["phases"]
        assert p["dive_start_s"] == pytest.approx(1.2)

    @pytest.mark.parametrize("boundaries", [None, {}, "junk", {"dive_start_s": None},
                                            {"dive_start_s": "0.7"}])
    def test_malformed_stored_dive_start_falls_back(self, boundaries):
        mj = {**METRICS_JSON, "phases": {"boundaries": boundaries}}
        p = annot.build_seed(mj)["phases"]
        assert p["dive_start_s"] == pytest.approx(1.2)

    def test_stroke_start_falls_back_to_first_cycle(self):
        mj = {"cycles": [{"start_idx": 300, "end_idx": 500}]}
        seed = annot.build_seed(mj)
        assert seed["phases"]["stroke_start_s"] == pytest.approx(3.0)

    def test_misordered_detection_dropped(self):
        # Pulldown/dive estimate lands AFTER the first cycle start → drop it, keep order.
        mj = {
            "session": {"baseline_end_s": 1.0},
            "initial_phase": {"dive_detected": True, "dive_duration_s": 10.0,
                              "initial_phase_end_idx": 450},
            "cycles": [{"start_idx": 500, "end_idx": 700}],
        }
        seed = annot.build_seed(mj)
        p = seed["phases"]
        assert p["underwater_start_s"] is None  # 11.0 would precede... follow order rule
        assert p["dive_start_s"] == pytest.approx(1.0)
        assert p["stroke_start_s"] == pytest.approx(4.5)
        # remaining present phases are non-decreasing
        present = [v for k, v in ((k, p[k]) for k in annot.PHASE_KEYS) if v is not None]
        assert present == sorted(present)


class TestValidateAnnotation:
    def test_valid_full_doc(self):
        # Deliberately still carries breakout_start_s: after Phase 58 retired that key this
        # doubles as the "a doc written under the old contract still validates" case.
        doc = {
            "phases": {"dive_start_s": 1.0, "underwater_start_s": 2.0,
                       "breakout_start_s": 3.0, "stroke_start_s": 4.0, "finish_s": 9.0},
            "stroke_marks_s": [5.0, 6.0, 7.0],
            "source": "manual",
        }
        assert annot.validate_annotation(doc, 30.0) == []

    def test_legacy_breakout_key_tolerated(self):
        # Phase 58 D7b: retired keys are ignored on read, never rejected and never honored.
        doc = {"phases": {"breakout_start_s": 3.0}}
        assert annot.validate_annotation(doc, 30.0) == []
        # ...and it reaches no metric boundary — the proof that D7 recomputes nothing.
        overrides = annot.annotation_to_overrides(doc, 1000, 100.0)
        assert "baseline_end_idx" not in overrides
        assert "ip_end_idx" not in overrides
        assert "swim_end_idx" not in overrides
        assert overrides == {}
        # An out-of-order legacy value is ignored rather than enforced against.
        assert annot.validate_annotation(
            {"phases": {"breakout_start_s": 99.0, "dive_start_s": 1.0}}, 30.0
        ) == []

    def test_valid_partial_doc(self):
        assert annot.validate_annotation({"phases": {"finish_s": 9.0}}, 30.0) == []
        assert annot.validate_annotation({"stroke_marks_s": []}, 30.0) == []
        assert annot.validate_annotation({}, 30.0) == []

    def test_misordered_phases(self):
        errs = annot.validate_annotation(
            {"phases": {"dive_start_s": 5.0, "stroke_start_s": 2.0}}, 30.0)
        assert any("must not precede" in e for e in errs)

    def test_out_of_range_time(self):
        errs = annot.validate_annotation({"phases": {"finish_s": 99.0}}, 30.0)
        assert any("exceeds session duration" in e for e in errs)
        errs = annot.validate_annotation({"phases": {"dive_start_s": -1.0}}, 30.0)
        assert any(">= 0" in e for e in errs)

    def test_unsorted_marks(self):
        errs = annot.validate_annotation({"stroke_marks_s": [6.0, 4.0]}, 30.0)
        assert any("out of order" in e for e in errs)

    def test_unknown_phase_key(self):
        errs = annot.validate_annotation({"phases": {"bogus_s": 1.0}}, 30.0)
        assert any("unknown phase key" in e for e in errs)

    def test_non_numeric_time(self):
        errs = annot.validate_annotation({"phases": {"dive_start_s": "abc"}}, 30.0)
        assert any("must be a number" in e for e in errs)

    def test_bad_source(self):
        errs = annot.validate_annotation({"source": "robot"}, 30.0)
        assert any("source" in e for e in errs)


# ── Endpoints ─────────────────────────────────────────────────────────────────

class TestGetAnnotations:
    def test_unannotated_session_returns_seed(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _annot_admin())
        resp = api_client.get("/sessions/sess-1/annotations", headers=AUTH)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["annotation"] is None
        assert data["seed"]["phases"]["dive_start_s"] == pytest.approx(1.2)
        assert data["seed"]["stroke_marks_s"] == [5.0, 7.0]
        assert data["video"] is None  # velocity-only sessions fully supported
        assert data["duration_s"] == pytest.approx(30.0)

    def test_saved_annotation_and_video_returned(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "video_path": "sess-1.mp4", "video_origin_s": 2.1}
        monkeypatch.setattr(
            api, "_get_supabase_admin",
            lambda: _annot_admin(session_row=row, annotation_row=ANNOTATION_ROW))
        data = api_client.get("/sessions/sess-1/annotations", headers=AUTH).json()
        assert data["annotation"]["stroke_marks_s"] == [5.0, 6.1, 7.3]
        assert data["video"] == {"path": "sess-1.mp4", "origin_s": 2.1}

    def test_foreign_session_404(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(session_row=None))
        resp = api_client.get("/sessions/other/annotations", headers=AUTH)
        assert resp.status_code == 404

    def test_no_coach_profile_403(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(coach_id=None))
        resp = api_client.get("/sessions/sess-1/annotations", headers=AUTH)
        assert resp.status_code == 403

    def test_no_auth_401(self):
        from fastapi.testclient import TestClient
        import api
        client = TestClient(api.app, raise_server_exceptions=True)
        resp = client.get("/sessions/sess-1/annotations")
        assert resp.status_code == 401


class TestPutAnnotations:
    VALID_DOC = {
        "phases": {"dive_start_s": 1.1, "stroke_start_s": 4.2, "finish_s": 9.4},
        "stroke_marks_s": [5.0, 6.2],
    }

    def test_round_trip_upsert(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=self.VALID_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["phases"]["stroke_start_s"] == pytest.approx(4.2)
        assert data["phases"]["underwater_start_s"] is None  # absent keys normalized
        # api.py rebuilds `phases` from PHASE_KEYS, so a retired key never reaches the row.
        # This is the strict-write half of Phase 58 D7b.
        assert "breakout_start_s" not in data["phases"]
        assert data["stroke_marks_s"] == [5.0, 6.2]
        assert data["source"] == "manual"
        record, kwargs = (admin._tables["session_annotations"].upsert.call_args[0][0],
                          admin._tables["session_annotations"].upsert.call_args[1])
        assert record["session_id"] == "sess-1"
        assert record["updated_by"] == "coach-1"
        assert kwargs.get("on_conflict") == "session_id"

    def test_invalid_doc_422_with_errors(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _annot_admin())
        resp = api_client.put(
            "/sessions/sess-1/annotations",
            json={"phases": {"dive_start_s": 99.0}},  # beyond 30 s duration
            headers=AUTH)
        assert resp.status_code == 422
        assert any("exceeds session duration" in e
                   for e in resp.json()["detail"]["errors"])

    def test_foreign_session_404(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(session_row=None))
        resp = api_client.put("/sessions/other/annotations", json=self.VALID_DOC,
                              headers=AUTH)
        assert resp.status_code == 404


class TestDeleteAnnotations:
    def test_delete_ok(self, api_client, monkeypatch):
        import api
        admin = _annot_admin(annotation_row=ANNOTATION_ROW)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.delete("/sessions/sess-1/annotations", headers=AUTH)
        assert resp.status_code == 200
        admin._tables["session_annotations"].delete.assert_called_once()


class TestVideoEndpoints:
    def test_upload_video_sets_path_and_origin(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.post(
            "/sessions/sess-1/video",
            files={"file": ("trial.mp4", io.BytesIO(b"fake-mp4-bytes"), "video/mp4")},
            data={"video_origin_s": "2.05"},
            headers=AUTH)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["video_path"] == "sess-1.mp4"
        assert data["video_origin_s"] == pytest.approx(2.05)
        upload_kwargs = admin.storage.from_.return_value.upload.call_args[1]
        assert upload_kwargs["path"] == "sess-1.mp4"
        update_arg = admin._tables["sessions"].update.call_args[0][0]
        assert update_arg == {"video_path": "sess-1.mp4",
                              "video_origin_s": pytest.approx(2.05)}

    def test_origin_only_update(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.post("/sessions/sess-1/video",
                               data={"video_origin_s": "1.5"}, headers=AUTH)
        assert resp.status_code == 200, resp.text
        admin.storage.from_.return_value.upload.assert_not_called()
        update_arg = admin._tables["sessions"].update.call_args[0][0]
        assert update_arg == {"video_origin_s": pytest.approx(1.5)}

    def test_neither_file_nor_origin_422(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _annot_admin())
        resp = api_client.post("/sessions/sess-1/video", headers=AUTH)
        assert resp.status_code == 422

    def test_video_url_without_video_404(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _annot_admin())
        resp = api_client.get("/sessions/sess-1/video-url", headers=AUTH)
        assert resp.status_code == 404

    def test_video_url_signed(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "video_path": "sess-1.mp4", "video_origin_s": 2.1}
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(session_row=row))
        resp = api_client.get("/sessions/sess-1/video-url", headers=AUTH)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["url"].startswith("https://signed.example/")
        assert data["origin_s"] == pytest.approx(2.1)


# ── Phase 47-04: recompute on save / restore on delete / export ───────────────

RECOMPUTE_DOC = {
    "phases": {"dive_start_s": 1.1, "stroke_start_s": 4.2, "finish_s": 9.4},
    "stroke_marks_s": [5.0, 6.2],  # + finish → 3 boundaries → 2 cycles
}


def _session_updates(admin):
    """Every payload written to `sessions`, in order.

    PUT /annotations now issues TWO writes (Phase 75-06): the cycle recompute, then the
    phases rebuild. Tests must therefore pick the write they mean instead of reading
    `update.call_args`, which is only ever the LAST one.
    """
    return [c[0][0] for c in admin._tables["sessions"].update.call_args_list]


def _recompute_update(admin):
    """The cycle-recompute write, or None when no recompute happened.

    PUT /annotations issues at most two writes, in a fixed order (Phase 75-06): the cycle
    recompute (only when the annotation yields cycles), then the phases rebuild (always
    attempted). Since the rebuild MERGES onto the stored metrics_json, both payloads carry
    a full one — cycles and session included — so they are told apart by position, not by
    content.
    """
    writes = _session_updates(admin)
    return writes[0] if len(writes) >= 2 else None


class TestRecomputeOnSave:
    def test_recompute_overwrites_and_backs_up_once(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()  # metrics_json_auto is None → backup expected
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        assert resp.json()["recomputed"] is True
        updates = _recompute_update(admin)
        assert updates is not None and "metrics_json" in updates
        assert updates["metrics_json_auto"] == METRICS_JSON  # once-only backup
        new_mj = updates["metrics_json"]
        # Recomputed from the human boundaries
        assert new_mj["session"]["total_cycles_raw"] == 2
        assert new_mj["session"]["segmentation_reliable"] is True
        assert [(c["start_idx"], c["end_idx"]) for c in new_mj["cycles"]] == [
            (500, 620), (620, 940)]
        # Non-recomputable quality fields carried over; provenance marked
        dq = new_mj["data_quality"]
        assert dq["magnet_dropout_pct"] == 3.5
        assert dq["recomputed_from_annotation"] is True
        assert dq["segmentation_reliable"] is True
        # dive/pulldown detection carried from the original
        assert new_mj["initial_phase"]["dive_detected"] is True

    def test_backup_not_overwritten_on_second_save(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "metrics_json_auto": {"session": {"orig": True}}}
        admin = _annot_admin(session_row=row)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.json()["recomputed"] is True
        updates = _recompute_update(admin)
        assert updates is not None and "metrics_json" in updates
        assert "metrics_json_auto" not in updates  # backup preserved

    def test_too_few_boundaries_saves_without_recompute(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put(
            "/sessions/sess-1/annotations",
            json={"phases": {"dive_start_s": 1.0}, "stroke_marks_s": [5.0]},
            headers=AUTH)
        assert resp.status_code == 200, resp.text
        assert resp.json()["recomputed"] is False
        admin._tables["session_annotations"].upsert.assert_called_once()
        # No CYCLE recompute — but the phases rebuild still runs (Phase 75-06), because a
        # boundaries-only annotation must still promote those boundaries to source="manual".
        # It was previously asserted that nothing was written at all.
        assert _recompute_update(admin) is None
        writes = _session_updates(admin)
        assert len(writes) == 1 and "phases" in writes[0]["metrics_json"]
        assert all("metrics_json_auto" not in w for w in writes)

    def test_recompute_failure_keeps_annotation(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "distance_profile": [0.0, 1.0]}  # mismatched → error
        admin = _annot_admin(session_row=row)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["recomputed"] is False
        assert "recompute_error" in body
        admin._tables["session_annotations"].upsert.assert_called_once()
        admin._tables["sessions"].update.assert_not_called()


class TestPhasesSurviveAnnotation:
    """Phase 75-06 AC-3. Saving an annotation used to rebuild metrics_json as a fresh
    4-key dict, silently deleting `phases` and `go_signal_s`. Annotated sessions — the ones
    with the best ground truth — were therefore the ONLY ones with no race-phase metrics."""

    ROW = {
        **SESSION_ROW,
        "metrics_json": {
            **METRICS_JSON,
            "go_signal_s": 2.5,
            "phases": {"schema_version": 3, "start": {}, "underwater": {},
                       "swim": {}, "whole": {}},
        },
    }

    def _phases_write(self, admin):
        """The last write's phases object — the rebuild lands after the recompute."""
        return _session_updates(admin)[-1]["metrics_json"]

    def test_go_signal_and_phases_are_not_dropped(self, api_client, monkeypatch):
        import api
        admin = _annot_admin(session_row=self.ROW)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        recompute_mj = _recompute_update(admin)["metrics_json"]
        assert recompute_mj["go_signal_s"] == pytest.approx(2.5)
        assert "phases" in recompute_mj

    def test_phases_are_rebuilt_from_the_manual_boundaries(self, api_client, monkeypatch):
        import api
        admin = _annot_admin(session_row=self.ROW, annotation_row=RECOMPUTE_DOC)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        phases = self._phases_write(admin)["phases"]
        sources = phases["boundaries"]["sources"]
        assert sources["dive_start_s"] == "manual"
        assert sources["stroke_start_s"] == "manual"
        assert phases["boundaries"]["finish_s"] == pytest.approx(9.4)

    def test_per_cycle_metrics_lose_provisional_once_annotated(self, api_client, monkeypatch):
        """The whole point of annotations-first: the coach's cycles are trusted cycles."""
        import api
        admin = _annot_admin(session_row=self.ROW, annotation_row=RECOMPUTE_DOC)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC, headers=AUTH)
        swim = self._phases_write(admin)["phases"]["swim"]
        assert swim["dead_spot_timing"]["provisional"] is False
        assert swim["sr_dps_coupling"]["provisional"] is False

    def test_rebuild_failure_never_loses_the_annotation(self, api_client, monkeypatch):
        import api

        def _boom(*_a, **_kw):
            raise RuntimeError("phases exploded")

        admin = _annot_admin(session_row=self.ROW)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        monkeypatch.setattr(api, "_rebuild_phases", _boom)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        assert resp.json()["phases_error"] == "phases exploded"
        admin._tables["session_annotations"].upsert.assert_called_once()


class TestDeleteRestoresAuto:
    def test_delete_restores_metrics_from_backup(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "metrics_json_auto": {"session": {"orig": True}}}
        admin = _annot_admin(session_row=row, annotation_row=ANNOTATION_ROW)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.delete("/sessions/sess-1/annotations", headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["metrics_restored"] is True
        admin._tables["session_annotations"].delete.assert_called_once()
        updates = admin._tables["sessions"].update.call_args[0][0]
        assert updates == {"metrics_json": {"session": {"orig": True}}}

    def test_delete_without_backup_no_restore(self, api_client, monkeypatch):
        import api
        admin = _annot_admin(annotation_row=ANNOTATION_ROW)  # metrics_json_auto None
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.delete("/sessions/sess-1/annotations", headers=AUTH)
        assert resp.json()["metrics_restored"] is False
        admin._tables["sessions"].update.assert_not_called()


class TestExport:
    def test_export_shape(self, api_client, monkeypatch):
        import api
        ann = {**ANNOTATION_ROW, "session_id": "sess-1"}
        admin = _annot_admin(annotation_row=ann)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.get("/annotations/export", headers=AUTH)
        assert resp.status_code == 200, resp.text
        sessions = resp.json()["sessions"]
        assert len(sessions) == 1
        rec = sessions[0]
        assert rec["session_id"] == "sess-1"
        assert rec["stroke_type"] == "breaststroke"
        assert rec["duration_s"] == 30.0
        assert rec["raw_csv_path"] == "ath-1/123.csv"
        assert rec["annotation"]["stroke_marks_s"] == [5.0, 6.1, 7.3]
        assert rec["annotation"]["source"] == "manual"

    def test_export_empty_when_no_sessions(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(session_row=None))
        resp = api_client.get("/annotations/export", headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["sessions"] == []

    def test_export_requires_auth(self):
        from fastapi.testclient import TestClient
        import api
        client = TestClient(api.app, raise_server_exceptions=True)
        assert client.get("/annotations/export").status_code == 401


# ── Phase 52: per-session sample rate (API-AUDIT F2 + F3) ─────────────────────
#
# The stored profiles are ~89.5 Hz, not 100 (decimation is by an integer factor).
# Everything below pins two properties: times follow the session's OWN rate, and a
# session with no recorded rate behaves exactly as it did before Phase 52.

FS_REAL = 89.5


class TestSampleRatePure:
    def test_build_seed_uses_supplied_rate(self):
        seed = annot.build_seed(METRICS_JSON, FS_REAL)
        assert seed["phases"]["stroke_start_s"] == pytest.approx(450 / FS_REAL)
        assert seed["phases"]["finish_s"] == pytest.approx(910 / FS_REAL)
        assert seed["stroke_marks_s"] == pytest.approx([500 / FS_REAL, 700 / FS_REAL])

    def test_build_seed_defaults_to_100(self):
        assert annot.build_seed(METRICS_JSON) == annot.build_seed(METRICS_JSON, 100)

    @pytest.mark.parametrize("bad", [None, 0, -5, float("nan"), "89.5", True])
    def test_bad_rate_falls_back_never_raises(self, bad):
        assert annot.build_seed(METRICS_JSON, bad) == annot.build_seed(METRICS_JSON, 100)
        assert (annot.annotation_to_overrides(ANNOTATION_ROW, 3000, bad)
                == annot.annotation_to_overrides(ANNOTATION_ROW, 3000, 100))

    @pytest.mark.parametrize("fs", [89.5, 100, 268.5])
    def test_index_round_trip_preserved(self, fs):
        """AC-6: seed at a rate, convert back at the same rate, land on the same sample."""
        seed = annot.build_seed(METRICS_JSON, fs)
        manual = annot.annotation_to_overrides(seed, 3000, fs)
        assert manual["ip_end_idx"] == 450
        assert [b[0] for b in manual["cycle_bounds"]] == [500, 700]

    def test_overrides_scale_with_rate(self):
        at_100 = annot.annotation_to_overrides(RECOMPUTE_DOC, 3000, 100)
        at_real = annot.annotation_to_overrides(RECOMPUTE_DOC, 3000, FS_REAL)
        assert at_100["cycle_bounds"] == [(500, 620), (620, 940)]
        assert at_real["cycle_bounds"] == [(448, 555), (555, 841)]


class TestSampleRateEndpoints:
    def test_duration_uses_session_rate(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "sample_rate_hz": FS_REAL}
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(session_row=row))
        body = api_client.get("/sessions/sess-1/annotations", headers=AUTH).json()
        assert body["duration_s"] == pytest.approx(3000 / FS_REAL)
        assert body["sample_rate_hz"] == pytest.approx(FS_REAL)
        assert body["seed"]["phases"]["finish_s"] == pytest.approx(910 / FS_REAL)

    @pytest.mark.parametrize("stored", [None, 0, "not-a-number"])
    def test_missing_or_bad_rate_is_pre_phase_52_behavior(self, api_client,
                                                          monkeypatch, stored):
        """AC-4: NULL (and anything unusable) must reproduce the old 100 Hz output."""
        import api
        row = {**SESSION_ROW, "sample_rate_hz": stored}
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(session_row=row))
        body = api_client.get("/sessions/sess-1/annotations", headers=AUTH).json()
        assert body["duration_s"] == pytest.approx(30.0)
        assert body["seed"] == annot.build_seed(METRICS_JSON, 100)

    def test_session_row_without_the_column_at_all(self, api_client, monkeypatch):
        """The pre-migration shape — no key present, not even null."""
        import api
        assert "sample_rate_hz" not in SESSION_ROW
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _annot_admin())
        body = api_client.get("/sessions/sess-1/annotations", headers=AUTH).json()
        assert body["duration_s"] == pytest.approx(30.0)

    def test_recompute_runs_on_the_true_clock(self, api_client, monkeypatch):
        """AC-3: the boundaries the coach clicked map through the session's own rate."""
        import api
        row = {**SESSION_ROW, "sample_rate_hz": FS_REAL}
        admin = _annot_admin(session_row=row)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        assert resp.json()["recomputed"] is True
        new_mj = admin._tables["sessions"].update.call_args[0][0]["metrics_json"]
        # Same doc at 100 Hz produced (500, 620), (620, 940) — see TestRecomputeOnSave
        assert [(c["start_idx"], c["end_idx"]) for c in new_mj["cycles"]] == [
            (448, 555), (555, 841)]


# ── Phase 57: arm-entry marks + authoritative swim window ─────────────────────
#
# One mark is one ARM ENTRY, not one cycle. Free/back alternate arms (2 entries per
# cycle); fly/breast move both together (1). Everything not in MARKS_PER_CYCLE must
# behave exactly as it did before Phase 57 — that is the safe default this pins.

# 5 arm entries at 100 Hz → idx 200/260/320/380/440. finish == the last mark, so the
# k == 1 finish-append does not fire and the two conventions differ ONLY by pairing.
DOC_5_MARKS = {
    "phases": {"stroke_start_s": 2.0, "finish_s": 4.4},
    "stroke_marks_s": [2.0, 2.6, 3.2, 3.8, 4.4],
}

# finish beyond the last mark — isolates the k == 1 finish-append asymmetry.
DOC_FINISH_BEYOND = {
    "phases": {"stroke_start_s": 2.0, "finish_s": 5.0},
    "stroke_marks_s": [2.0, 2.6, 3.2, 3.8],
}

LEGACY_STROKES = ["butterfly", "breaststroke", "im", "udk", None, "", "nonsense"]


class TestMarksPerCycle:
    @pytest.mark.parametrize("stroke,expected", [
        ("freestyle", 2), ("backstroke", 2),
        ("butterfly", 1), ("breaststroke", 1), ("im", 1), ("udk", 1),
        (None, 1), ("", 1), ("Freestyle", 1),  # case-sensitive: stored values are lowercase
    ])
    def test_factor(self, stroke, expected):
        assert annot.marks_per_cycle(stroke) == expected


class TestArmEntryPairing:
    def test_freestyle_pairs_marks_into_cycles(self):
        out = annot.annotation_to_overrides(DOC_5_MARKS, 3000, 100, "freestyle")
        # boundaries at marks 0/2/4 → idx 200/320/440
        assert out["cycle_bounds"] == [(200, 320), (320, 440)]

    def test_backstroke_pairs_too(self):
        assert (annot.annotation_to_overrides(DOC_5_MARKS, 3000, 100, "backstroke")
                == annot.annotation_to_overrides(DOC_5_MARKS, 3000, 100, "freestyle"))

    def test_butterfly_is_one_mark_one_cycle(self):
        out = annot.annotation_to_overrides(DOC_5_MARKS, 3000, 100, "butterfly")
        assert out["cycle_bounds"] == [(200, 260), (260, 320), (320, 380), (380, 440)]

    def test_trailing_odd_arm_entry_makes_no_cycle(self):
        """5 entries = 2 complete cycles; the 5th dangles. It must not become a cycle,
        but it stays in the caller's stored stroke_marks_s (this function never edits it)."""
        out = annot.annotation_to_overrides(DOC_5_MARKS, 3000, 100, "freestyle")
        assert len(out["cycle_bounds"]) == 2
        assert DOC_5_MARKS["stroke_marks_s"][-1] == 4.4  # untouched

    def test_finish_closes_the_last_cycle_only_when_one_mark_is_one_cycle(self):
        """At k == 1 the wall legitimately ends the last cycle. At k == 2 a boundary is a
        SAME-SIDE arm entry and finish_s is a wall touch — appending it would manufacture
        a half-populated cycle that skews stroke_rate_spm."""
        k1 = annot.annotation_to_overrides(DOC_FINISH_BEYOND, 3000, 100, "butterfly")
        k2 = annot.annotation_to_overrides(DOC_FINISH_BEYOND, 3000, 100, "freestyle")
        assert k1["cycle_bounds"] == [(200, 260), (260, 320), (320, 380), (380, 500)]
        assert k2["cycle_bounds"] == [(200, 320)]  # NOT (320, 500)

    def test_too_few_marks_to_pair(self):
        doc = {"phases": {"stroke_start_s": 2.0, "finish_s": 2.6},
               "stroke_marks_s": [2.0, 2.6]}
        # 2 arm entries = 1 cycle for free, but only one boundary survives pairing
        assert "cycle_bounds" not in annot.annotation_to_overrides(
            doc, 3000, 100, "freestyle")

    @pytest.mark.parametrize("stroke", LEGACY_STROKES)
    @pytest.mark.parametrize("doc", [DOC_5_MARKS, DOC_FINISH_BEYOND,
                                     ANNOTATION_ROW, RECOMPUTE_DOC])
    def test_non_alternating_strokes_are_byte_identical_to_pre_phase_57(self, stroke, doc):
        """The safe default: anything outside MARKS_PER_CYCLE must produce exactly what
        the three-argument call produced before this parameter existed."""
        assert (annot.annotation_to_overrides(doc, 3000, 100, stroke)
                == annot.annotation_to_overrides(doc, 3000, 100))


class TestSwimWindowEnforcement:
    def test_mark_before_stroke_start_rejected(self):
        doc = {"phases": {"stroke_start_s": 4.0, "finish_s": 9.0},
               "stroke_marks_s": [3.5, 5.0]}
        errs = annot.validate_annotation(doc, 30.0)
        assert any("before stroke_start_s" in e for e in errs)
        assert any("stroke_marks_s[0]" in e for e in errs)

    def test_mark_after_finish_rejected(self):
        """The dead-tail case: before Phase 57 this silently became a cycle."""
        doc = {"phases": {"stroke_start_s": 4.0, "finish_s": 9.0},
               "stroke_marks_s": [5.0, 21.5]}
        errs = annot.validate_annotation(doc, 30.0)
        assert any("after finish_s" in e for e in errs)
        assert any("stroke_marks_s[1]" in e for e in errs)

    def test_marks_exactly_on_the_bounds_are_accepted(self):
        doc = {"phases": {"stroke_start_s": 4.0, "finish_s": 9.0},
               "stroke_marks_s": [4.0, 6.0, 9.0]}
        assert annot.validate_annotation(doc, 30.0) == []

    def test_bounds_enforced_independently(self):
        only_finish = {"phases": {"finish_s": 9.0}, "stroke_marks_s": [1.0, 9.5]}
        errs = annot.validate_annotation(only_finish, 30.0)
        assert any("after finish_s" in e for e in errs)
        assert not any("before stroke_start_s" in e for e in errs)

        only_start = {"phases": {"stroke_start_s": 4.0}, "stroke_marks_s": [1.0, 9.5]}
        errs = annot.validate_annotation(only_start, 30.0)
        assert any("before stroke_start_s" in e for e in errs)
        assert not any("after finish_s" in e for e in errs)

    def test_unbounded_doc_is_unenforced(self):
        """No window annotated → nothing to enforce (a partial draft must stay saveable)."""
        assert annot.validate_annotation({"stroke_marks_s": [1.0, 20.0]}, 30.0) == []

    def test_malformed_bound_degrades_to_unenforced(self):
        doc = {"phases": {"stroke_start_s": "abc"}, "stroke_marks_s": [1.0]}
        errs = annot.validate_annotation(doc, 30.0)
        assert any("must be a number" in e for e in errs)
        assert not any("before stroke_start_s" in e for e in errs)


class TestStrokeTypeReachesTheEndpoints:
    """stroke_type must be SELECTED, not just referenced — the Phase-52 lesson: an
    un-widened .select() makes the fallback hide the fix instead of applying it."""

    def test_get_select_includes_stroke_type(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        api_client.get("/sessions/sess-1/annotations", headers=AUTH)
        assert "stroke_type" in admin._tables["sessions"].select.call_args[0][0]

    def test_put_select_includes_stroke_type(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC, headers=AUTH)
        assert "stroke_type" in admin._tables["sessions"].select.call_args[0][0]

    @pytest.mark.parametrize("stroke,expected", [
        ("freestyle", 2), ("backstroke", 2), ("breaststroke", 1), ("butterfly", 1),
        ("im", 1), (None, 1),
    ])
    def test_get_publishes_marks_per_cycle(self, api_client, monkeypatch,
                                           stroke, expected):
        import api
        row = {**SESSION_ROW, "stroke_type": stroke}
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _annot_admin(session_row=row))
        body = api_client.get("/sessions/sess-1/annotations", headers=AUTH).json()
        assert body["marks_per_cycle"] == expected

    def test_put_pairs_freestyle_marks_and_reports_the_count(self, api_client,
                                                             monkeypatch):
        import api
        row = {**SESSION_ROW, "stroke_type": "freestyle"}
        admin = _annot_admin(session_row=row)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=DOC_5_MARKS,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["marks_per_cycle"] == 2
        assert body["cycles_derived"] == 2          # 5 arm entries → 2 complete cycles
        assert body["recomputed"] is True
        new_mj = admin._tables["sessions"].update.call_args[0][0]["metrics_json"]
        assert [(c["start_idx"], c["end_idx"]) for c in new_mj["cycles"]] == [
            (200, 320), (320, 440)]

    def test_same_doc_on_breaststroke_is_one_mark_one_cycle(self, api_client,
                                                            monkeypatch):
        """Identical marks, different stroke → different cycle count. This is the
        failure a wrong (unpatchable) stroke_type would cause, made visible."""
        import api
        admin = _annot_admin()  # SESSION_ROW is breaststroke
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        body = api_client.put("/sessions/sess-1/annotations", json=DOC_5_MARKS,
                              headers=AUTH).json()
        assert body["marks_per_cycle"] == 1
        assert body["cycles_derived"] == 4

    def test_mark_past_finish_is_422_and_writes_nothing(self, api_client, monkeypatch):
        import api
        admin = _annot_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        doc = {"phases": {"stroke_start_s": 4.0, "finish_s": 9.0},
               "stroke_marks_s": [5.0, 21.5]}
        resp = api_client.put("/sessions/sess-1/annotations", json=doc, headers=AUTH)
        assert resp.status_code == 422, resp.text
        errs = resp.json()["detail"]["errors"]
        assert any("after finish_s" in e for e in errs)
        # The annotations table is never even reached — validation rejects first.
        # (_annot_admin creates table handles lazily, so absence IS the assertion.)
        assert "session_annotations" not in admin._tables
        admin._tables["sessions"].update.assert_not_called()


# 7 marks = 6 single-arm strokes = 3 cycles, with nothing dangling.
DOC_7_MARKS = {
    "phases": {"stroke_start_s": 2.0, "finish_s": 5.6},
    "stroke_marks_s": [2.0, 2.6, 3.2, 3.8, 4.4, 5.0, 5.6],
}


class TestStrokeBounds:
    """Phase 87-01, AC-3: the SINGLE-ARM view of the same marks."""

    def test_seven_marks_give_six_stroke_bounds_and_three_cycles(self):
        out = annot.annotation_to_overrides(DOC_7_MARKS, 3000, 100, "freestyle")
        assert out["stroke_bounds"] == [(200, 260), (260, 320), (320, 380),
                                        (380, 440), (440, 500), (500, 560)]
        assert out["cycle_bounds"] == [(200, 320), (320, 440), (440, 560)]

    def test_cycle_bounds_are_byte_identical_to_the_pre_change_expectation(self):
        """The pre-87-01 contract, pinned: adding stroke_bounds moved nothing else."""
        out = annot.annotation_to_overrides(DOC_5_MARKS, 3000, 100, "freestyle")
        assert out["cycle_bounds"] == [(200, 320), (320, 440)]
        assert out["ip_end_idx"] == 200
        assert out["swim_end_idx"] == 441

    def test_backstroke_matches_freestyle(self):
        assert (annot.annotation_to_overrides(DOC_7_MARKS, 3000, 100, "backstroke")
                == annot.annotation_to_overrides(DOC_7_MARKS, 3000, 100, "freestyle"))

    @pytest.mark.parametrize("stroke", LEGACY_STROKES)
    def test_no_stroke_bounds_at_one_mark_per_cycle(self, stroke):
        """At k == 1 stroke_bounds would equal cycle_bounds — a pure drift hazard."""
        out = annot.annotation_to_overrides(DOC_7_MARKS, 3000, 100, stroke)
        assert "stroke_bounds" not in out

    def test_finish_is_never_appended_to_stroke_bounds(self):
        """A wall touch is not an arm entry — the k > 1 rule, applied per stroke."""
        out = annot.annotation_to_overrides(DOC_FINISH_BEYOND, 3000, 100, "freestyle")
        assert out["stroke_bounds"] == [(200, 260), (260, 320), (320, 380)]
        assert max(b for _, b in out["stroke_bounds"]) < 500   # finish_s = 5.0 → idx 500

    def test_odd_marks_leave_the_trailing_stroke_paired_but_no_cycle(self):
        out = annot.annotation_to_overrides(DOC_5_MARKS, 3000, 100, "freestyle")
        assert len(out["stroke_bounds"]) == 4      # every consecutive pair of 5 marks
        assert len(out["cycle_bounds"]) == 2


# ── Phase 87-01: strokes persisted from the coach's marks ─────────────────────

FREE_ROW = {**SESSION_ROW, "stroke_type": "freestyle"}

# 7 arm entries → 6 strokes → 3 cycles, all inside [stroke_start_s, finish_s].
FREE_DOC = {
    "phases": {"dive_start_s": 1.1, "stroke_start_s": 4.2, "finish_s": 12.0},
    "stroke_marks_s": [5.0, 6.2, 7.4, 8.6, 9.8, 11.0, 11.9],
}


class TestStrokesPersistedOnAnnotation:
    """AC-5: PUT /annotations replaces metrics_json.strokes from the coach's marks,
    without disturbing anything the 75-06 merge already protects."""

    ROW = {
        **FREE_ROW,
        "metrics_json": {
            **METRICS_JSON,
            "go_signal_s": 2.5,
            "strokes": [{"stroke_num": 0, "start_idx": 1, "end_idx": 2}],  # stale
            "phases": {"schema_version": 3, "start": {}, "underwater": {},
                       "swim": {}, "whole": {}},
        },
    }

    def test_strokes_are_written_from_the_marks(self, api_client, monkeypatch):
        import api
        admin = _annot_admin(session_row=self.ROW)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=FREE_DOC, headers=AUTH)
        assert resp.status_code == 200, resp.text
        mj = _recompute_update(admin)["metrics_json"]
        # 6 single-arm strokes from 7 marks; 3 cycles from every 2nd mark.
        assert [(s["start_idx"], s["end_idx"]) for s in mj["strokes"]] == [
            (500, 620), (620, 740), (740, 860), (860, 980), (980, 1100), (1100, 1190)]
        assert len(mj["cycles"]) == 3
        assert mj["strokes"][0]["stroke_num"] == 0
        assert "duration_s" in mj["strokes"][0]   # same field set as a cycle

    def test_phases_go_signal_and_the_backup_survive(self, api_client, monkeypatch):
        import api
        admin = _annot_admin(session_row=self.ROW)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=FREE_DOC, headers=AUTH)
        assert resp.status_code == 200, resp.text
        updates = _recompute_update(admin)
        mj = updates["metrics_json"]
        assert mj["go_signal_s"] == pytest.approx(2.5)
        assert mj["phases"]["schema_version"] == 3
        assert updates["metrics_json_auto"] == self.ROW["metrics_json"]  # once-only backup

    def test_asymmetry_keys_ride_along_in_session(self, api_client, monkeypatch):
        import api
        admin = _annot_admin(session_row=self.ROW)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        api_client.put("/sessions/sess-1/annotations", json=FREE_DOC, headers=AUTH)
        sess = _recompute_update(admin)["metrics_json"]["session"]
        for k in ("arm_asym_tempo_pct", "arm_asym_dps_pct", "arm_asym_peak_vel_pct",
                  "cv_stroke_interval_a", "cv_stroke_interval_b",
                  "cv_stroke_dps_a", "cv_stroke_dps_b"):
            assert k in sess

    def test_non_alternating_stroke_gets_no_strokes(self, api_client, monkeypatch):
        """breaststroke: one arm entry IS one cycle, so annotation_to_overrides emits no
        stroke_bounds and the stored array is None rather than a copy of cycles."""
        import api
        admin = _annot_admin()          # SESSION_ROW is breaststroke
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.put("/sessions/sess-1/annotations", json=RECOMPUTE_DOC,
                              headers=AUTH)
        assert resp.status_code == 200, resp.text
        assert _recompute_update(admin)["metrics_json"]["strokes"] is None
