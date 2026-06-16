"""Integration tests for POST /process endpoint."""
import io

import pytest


DATA_QUALITY_KEYS = [
    "magnet_dropout_pct",
    "outlier_cycle_count",
    "implausible_cycle_count",
    "total_cycles_raw",
    "warnings",
]

RESPONSE_TOP_KEYS = [
    "session",
    "cycles",
    "time",
    "velocity",
    "distance",
    "data_quality",
]


def _post_csv(client, csv_bytes: bytes, head_waist_m: float = 0.0):
    """Helper: POST a CSV to /process and return the Response."""
    return client.post(
        "/process",
        files={"file": ("session.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"head_waist_m": str(head_waist_m)},
        headers={"Authorization": "Bearer fake-token-mocked"},
    )


class TestProcessEndpointShape:
    """POST /process — response shape and status."""

    def test_returns_200(self, api_client, synthetic_csv_bytes):
        resp = _post_csv(api_client, synthetic_csv_bytes)
        assert resp.status_code == 200, resp.text

    def test_top_level_keys_present(self, api_client, synthetic_csv_bytes):
        data = _post_csv(api_client, synthetic_csv_bytes).json()
        for key in RESPONSE_TOP_KEYS:
            assert key in data, f"Missing top-level key: {key}"

    def test_time_velocity_distance_are_lists(self, api_client, synthetic_csv_bytes):
        data = _post_csv(api_client, synthetic_csv_bytes).json()
        assert isinstance(data["time"], list)
        assert isinstance(data["velocity"], list)
        assert isinstance(data["distance"], list)
        assert len(data["time"]) > 0

    def test_time_velocity_distance_same_length(self, api_client, synthetic_csv_bytes):
        data = _post_csv(api_client, synthetic_csv_bytes).json()
        assert len(data["time"]) == len(data["velocity"]) == len(data["distance"])


class TestDataQuality:
    """POST /process — data_quality object correctness."""

    def test_data_quality_keys_present(self, api_client, synthetic_csv_bytes):
        data = _post_csv(api_client, synthetic_csv_bytes).json()
        dq = data["data_quality"]
        for key in DATA_QUALITY_KEYS:
            assert key in dq, f"Missing data_quality key: {key}"

    def test_warnings_is_nonempty_list(self, api_client, synthetic_csv_bytes):
        """Kick-metrics warning must always be present."""
        dq = _post_csv(api_client, synthetic_csv_bytes).json()["data_quality"]
        assert isinstance(dq["warnings"], list)
        assert len(dq["warnings"]) >= 1, "Kick metrics warning must always be in warnings"

    def test_kick_warning_content(self, api_client, synthetic_csv_bytes):
        """Kick warning text mentions 'unreliable' or 'LP filter'."""
        dq = _post_csv(api_client, synthetic_csv_bytes).json()["data_quality"]
        combined = " ".join(dq["warnings"]).lower()
        assert "unreliable" in combined or "lp filter" in combined

    def test_magnet_dropout_zero_for_clean_csv(self, api_client, synthetic_csv_bytes):
        """Clean CSV (all magnet_ok=1) should have dropout_pct == 0.0."""
        dq = _post_csv(api_client, synthetic_csv_bytes).json()["data_quality"]
        assert dq["magnet_dropout_pct"] == 0.0

    def test_magnet_dropout_nonzero_for_dropout_csv(self, api_client, synthetic_csv_with_dropout):
        """CSV with 10% dropout rows should produce dropout_pct ≈ 10.0."""
        dq = _post_csv(api_client, synthetic_csv_with_dropout).json()["data_quality"]
        assert dq["magnet_dropout_pct"] > 0.0
        assert abs(dq["magnet_dropout_pct"] - 10.0) < 2.0, (
            f"Expected ~10.0% dropout, got {dq['magnet_dropout_pct']}"
        )

    def test_quality_count_types(self, api_client, synthetic_csv_bytes):
        dq = _post_csv(api_client, synthetic_csv_bytes).json()["data_quality"]
        assert isinstance(dq["total_cycles_raw"], int)
        assert isinstance(dq["outlier_cycle_count"], int)
        assert isinstance(dq["implausible_cycle_count"], int)
        assert isinstance(dq["magnet_dropout_pct"], (int, float))

    def test_no_athlete_id_still_returns_data_quality(self, api_client, synthetic_csv_bytes):
        """data_quality must appear in response even when athlete_id is omitted."""
        data = _post_csv(api_client, synthetic_csv_bytes).json()
        assert "data_quality" in data


# ── GET /reports/{token} (public parent report) ───────────────────────────────

REPORT_ROW = {
    "athlete_id": "ath-1",
    "config_json": {
        "start": "2026-05-01T00:00:00Z",
        "end": None,
        "metrics": ["mean_vel_ms", "lap_time_s"],
        "message": "Great progress!",
    },
    "created_at": "2026-06-11T00:00:00Z",
}

ATHLETE_ROW = {"name": "Lucas Wong", "parent_name": "Mei"}

SESSION_ROWS = [
    {"created_at": "2026-05-05T00:00:00Z",
     "metrics_json": {"session": {"mean_vel_ms": 0.80, "lap_time_s": 31.0, "max_vel_ms": 1.9}}},
    {"created_at": "2026-06-01T00:00:00Z",
     "metrics_json": {"session": {"mean_vel_ms": 0.88, "lap_time_s": 28.5, "max_vel_ms": 2.0}}},
    {"created_at": "2026-06-02T00:00:00Z",
     "metrics_json": {}},  # session metrics missing — must be skipped
]


def _fake_admin(report=REPORT_ROW, athlete=ATHLETE_ROW, sessions=SESSION_ROWS):
    """MagicMock supabase admin client serving the three tables the endpoint reads."""
    from unittest.mock import MagicMock

    admin = MagicMock()

    def table(name):
        t = MagicMock()
        result = MagicMock()
        if name == "reports":
            result.data = report
        elif name == "athletes":
            result.data = athlete
        elif name == "sessions":
            result.data = sessions
        # every chained call returns the same mock; execute() yields the result
        t.select.return_value = t
        t.eq.return_value = t
        t.gte.return_value = t
        t.lte.return_value = t
        t.order.return_value = t
        t.single.return_value = t
        t.execute.return_value = result
        return t

    admin.table.side_effect = table
    return admin


@pytest.fixture
def report_client(monkeypatch):
    """TestClient with _get_supabase_admin patched to the fake admin."""
    from fastapi.testclient import TestClient
    import api

    monkeypatch.setattr(api, "_get_supabase_admin", lambda: _fake_admin())
    return TestClient(api.app, raise_server_exceptions=True)


class TestPublicReport:
    """GET /reports/{token} — public, no auth header."""

    def test_unknown_token_404(self, monkeypatch):
        from fastapi.testclient import TestClient
        import api

        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _fake_admin(report=None))
        client = TestClient(api.app, raise_server_exceptions=True)
        resp = client.get("/reports/not-a-real-token")
        assert resp.status_code == 404

    def test_valid_token_shape(self, report_client):
        resp = report_client.get("/reports/tok-123")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for key in ("athlete", "period", "message", "metrics", "sessions", "generated_at"):
            assert key in data, f"Missing key: {key}"
        assert data["athlete"]["name"] == "Lucas Wong"
        assert data["message"] == "Great progress!"
        assert data["metrics"] == ["mean_vel_ms", "lap_time_s"]

    def test_sessions_filtered_and_ordered(self, report_client):
        data = report_client.get("/reports/tok-123").json()
        # third row has no session metrics → skipped
        assert len(data["sessions"]) == 2
        dates = [s["date"] for s in data["sessions"]]
        assert dates == sorted(dates)
        # values restricted to requested metric keys
        for s in data["sessions"]:
            assert set(s["values"].keys()) <= {"mean_vel_ms", "lap_time_s"}
        assert data["sessions"][0]["values"]["mean_vel_ms"] == 0.80

    def test_no_sessions_returns_empty_list(self, monkeypatch):
        from fastapi.testclient import TestClient
        import api

        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _fake_admin(sessions=[]))
        client = TestClient(api.app, raise_server_exceptions=True)
        data = client.get("/reports/tok-123").json()
        assert data["sessions"] == []


# ── POST /coach/chat (AI coaching proxy) ───────────────────────────────────────

COACH_SESSION_ROW = {
    "coach_id": "coach-1",
    "stroke_type": "breaststroke",
    "metrics_json": {
        "session": {"mean_dps_m": 1.4, "stroke_rate_spm": 32.0, "cv_isi": 0.12},
        "cycles": [
            {"duration_s": 2.0, "peak_idx": 200, "arm_peak_vel": 1.3,
             "trough_vel_ms": 0.10, "coast_fraction": 0.3, "dist_m": 1.5, "phase": "steady"},
            {"duration_s": 2.1, "peak_idx": 410, "arm_peak_vel": 1.1,
             "trough_vel_ms": 0.05, "coast_fraction": 0.4, "dist_m": 1.4, "phase": "steady"},
        ],
    },
}


def _coach_admin(session_row=COACH_SESSION_ROW, coach_id="coach-1"):
    """Fake supabase admin serving coaches + sessions for /coach/chat."""
    from unittest.mock import MagicMock

    admin = MagicMock()

    def table(name):
        t = MagicMock()
        result = MagicMock()
        if name == "coaches":
            result.data = {"id": coach_id} if coach_id else None
        elif name == "sessions":
            result.data = session_row
        t.select.return_value = t
        t.eq.return_value = t
        t.single.return_value = t
        t.execute.return_value = result
        return t

    admin.table.side_effect = table
    return admin


def _mock_anthropic(monkeypatch, reply="MOCK COACHING REPLY"):
    """Patch api.anthropic.Anthropic; return the create() mock for call assertions."""
    from unittest.mock import MagicMock
    import api

    block = MagicMock()
    block.type = "text"
    block.text = reply
    resp = MagicMock()
    resp.content = [block]

    create = MagicMock(return_value=resp)
    client = MagicMock()
    client.messages.create = create
    monkeypatch.setattr(api.anthropic, "Anthropic", lambda *a, **k: client)
    return create


def _chat_body(content="How was my consistency?", role="user"):
    return {"session_id": "sess-1", "messages": [{"role": role, "content": content}]}


class TestCoachChat:
    """POST /coach/chat — auth, ownership, validation, prompt source."""

    def test_no_auth_401(self):
        from fastapi.testclient import TestClient
        import api

        client = TestClient(api.app, raise_server_exceptions=True)
        resp = client.post("/coach/chat", json=_chat_body())
        assert resp.status_code == 401

    def test_not_owner_403_and_no_model_call(self, api_client, monkeypatch):
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _coach_admin(session_row={**COACH_SESSION_ROW, "coach_id": "other-coach"}))
        create = _mock_anthropic(monkeypatch)
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 403, resp.text
        assert not create.called, "Anthropic must not be called when ownership fails"

    def test_session_missing_404(self, api_client, monkeypatch):
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _coach_admin(session_row=None))
        create = _mock_anthropic(monkeypatch)
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 404, resp.text
        assert not create.called

    def test_empty_messages_400(self, api_client, monkeypatch):
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _coach_admin())
        _mock_anthropic(monkeypatch)
        resp = api_client.post("/coach/chat",
                               json={"session_id": "sess-1", "messages": []},
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 400

    def test_last_message_must_be_user_400(self, api_client, monkeypatch):
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _coach_admin())
        _mock_anthropic(monkeypatch)
        resp = api_client.post("/coach/chat", json=_chat_body(role="assistant"),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 400

    def test_happy_path_returns_reply(self, api_client, monkeypatch):
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _coach_admin())
        _mock_anthropic(monkeypatch, reply="Nice rhythm.")
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["reply"] == "Nice rhythm."

    def test_prompt_built_from_stored_metrics_no_pii(self, api_client, monkeypatch):
        """System prompt is rebuilt from metrics_json + carries guardrails; no athlete name."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _coach_admin())
        create = _mock_anthropic(monkeypatch)
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        system_text = create.call_args.kwargs["system"][0]["text"]
        assert "Session Metrics:" in system_text       # built from _build_user_message
        assert "GUARDRAILS" in system_text              # safety scoping present
        assert "Lucas Wong" not in system_text          # no athlete PII ever in prompt

    def test_not_configured_503(self, api_client, monkeypatch):
        import api

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _coach_admin())
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 503


def test_system_prompt_contains_guardrails():
    """coach._build_system_prompt must embed the guardrails block (AC-3)."""
    import coach

    for stroke in ("breaststroke", "freestyle"):
        p = coach._build_system_prompt(stroke)
        assert "GUARDRAILS" in p
        assert "Defer those to the appropriate" in p
