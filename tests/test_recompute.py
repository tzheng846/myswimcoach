"""Tests for POST /sessions/{id}/recompute — the Phase 75-01 backfill seam that
rebuilds metrics_json.phases from STORED profiles (supabase mocked, no network).
Mirrors the mocking pattern in tests/test_annotations.py."""
from unittest.mock import MagicMock

import numpy as np
import pytest

# Realistic 30 s @ 100 Hz profiles
_N = 3000
_t_fix = np.arange(_N) / 100.0
_vel_fix = np.maximum(0.8 + 0.4 * np.sin(2 * np.pi * 0.5 * _t_fix), 0.05)
_dist_fix = np.concatenate([[0.0], np.cumsum(_vel_fix[:-1] / 100.0)])
_accel_fix = np.gradient(_vel_fix, _t_fix)

OLD_METRICS_JSON = {
    "session": {"baseline_end_s": 1.2, "lap_time_s": 30.0},
    "initial_phase": {"initial_phase_end_idx": 450, "dive_detected": True},
    "cycles": [{"cycle_num": 0, "start_idx": 500, "end_idx": 700}],
    "data_quality": {"magnet_dropout_pct": 3.5, "warnings": []},
    "phases": {"schema_version": 1, "go_signal_s": None,
               "start": {}, "underwater": {}, "swim": {}, "whole": {}},
}

SESSION_ROW = {
    "id": "sess-1",
    "metrics_json": OLD_METRICS_JSON,
    "velocity_profile": _vel_fix.tolist(),
    "distance_profile": _dist_fix.tolist(),
    "acceleration_profile": _accel_fix.tolist(),
    "sample_rate_hz": 100.0,
    "stroke_type": "breaststroke",
}

AUTH = {"Authorization": "Bearer fake-token-mocked"}


def _recompute_admin(session_row=SESSION_ROW, coach_id="coach-1"):
    """Fake supabase admin: coaches -> coach_id, sessions -> session_row.
    Table mocks are memoized so tests can assert on the update() call."""
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
        for method in ("select", "eq", "limit", "update", "upsert", "delete", "in_"):
            getattr(t, method).return_value = t
        t.execute.return_value = result
        admin._tables[name] = t
        return t

    admin.table.side_effect = table
    return admin


class TestRecomputeAuth:
    def test_no_auth_401(self):
        from fastapi.testclient import TestClient
        import api
        client = TestClient(api.app, raise_server_exceptions=True)
        resp = client.post("/sessions/sess-1/recompute")
        assert resp.status_code == 401

    def test_no_coach_profile_403(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _recompute_admin(coach_id=None))
        resp = api_client.post("/sessions/sess-1/recompute", headers=AUTH)
        assert resp.status_code == 403

    def test_foreign_session_404(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _recompute_admin(session_row=None))
        resp = api_client.post("/sessions/other/recompute", headers=AUTH)
        assert resp.status_code == 404


class TestRecomputeHappyPath:
    def test_rebuilds_phases_and_preserves_other_keys(self, api_client, monkeypatch):
        import api
        admin = _recompute_admin()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)

        resp = api_client.post("/sessions/sess-1/recompute", headers=AUTH)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["session_id"] == "sess-1"
        assert data["recomputed"] is True
        for bucket in ("start", "underwater", "swim", "whole"):
            assert bucket in data["phases"]
        assert data["phases"]["go_signal_s"] is None

        # session/cycles/initial_phase/data_quality preserved verbatim; only phases changed
        updated = admin._tables["sessions"].update.call_args[0][0]
        new_mj = updated["metrics_json"]
        assert new_mj["session"] == OLD_METRICS_JSON["session"]
        assert new_mj["cycles"] == OLD_METRICS_JSON["cycles"]
        assert new_mj["initial_phase"] == OLD_METRICS_JSON["initial_phase"]
        assert new_mj["data_quality"] == OLD_METRICS_JSON["data_quality"]
        assert new_mj["phases"]["schema_version"] == 1

    def test_idempotent_second_call_same_shape(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _recompute_admin())

        first = api_client.post("/sessions/sess-1/recompute", headers=AUTH).json()
        second = api_client.post("/sessions/sess-1/recompute", headers=AUTH).json()
        assert first["phases"] == second["phases"]

    def test_missing_acceleration_profile_still_succeeds(self, api_client, monkeypatch):
        """Pre-Phase-64 sessions have no acceleration_profile column value."""
        import api
        row = {**SESSION_ROW, "acceleration_profile": None}
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _recompute_admin(session_row=row))
        resp = api_client.post("/sessions/sess-1/recompute", headers=AUTH)
        assert resp.status_code == 200, resp.text

    def test_missing_velocity_profile_422(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "velocity_profile": [], "distance_profile": []}
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _recompute_admin(session_row=row))
        resp = api_client.post("/sessions/sess-1/recompute", headers=AUTH)
        assert resp.status_code == 422

    def test_mismatched_profile_lengths_422(self, api_client, monkeypatch):
        import api
        row = {**SESSION_ROW, "distance_profile": _dist_fix[:100].tolist()}
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _recompute_admin(session_row=row))
        resp = api_client.post("/sessions/sess-1/recompute", headers=AUTH)
        assert resp.status_code == 422
