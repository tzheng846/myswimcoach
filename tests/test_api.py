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


# ── POST /coach/chat — tool use (33-01: cross-session data access) ──────────────

def test_coach_tools_declared():
    """Two read-only tools exist and the prompt invites trend look-ups (AC-1)."""
    import coach

    names = {t["name"] for t in coach.COACH_TOOLS}
    assert names == {"list_athlete_sessions", "get_session_metrics"}
    assert "trends" in coach._build_system_prompt("breaststroke").lower()


ANCHOR_ROW = {**COACH_SESSION_ROW, "athlete_id": "ath-1"}


class _FakeSessionsQuery:
    """A chainable sessions query whose returned data depends on the eq() filters applied."""

    def __init__(self, resolver):
        self._resolver = resolver
        self._eqs = {}

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def single(self, *a, **k):
        return self

    def eq(self, col, val):
        self._eqs[col] = val
        return self

    def execute(self):
        from unittest.mock import MagicMock
        r = MagicMock()
        r.data = self._resolver(self._eqs)
        return r


def _tool_admin(anchor=ANCHOR_ROW, list_rows=None, detail_row=None, coach_id="coach-1", scope_log=None):
    """Fake admin for the tool tests. Routes the three sessions-query shapes by their filters
    and records every sessions query's eq() filters into scope_log for scoping assertions."""
    from unittest.mock import MagicMock
    log = scope_log if scope_log is not None else []
    list_rows = [] if list_rows is None else list_rows

    def resolver(eqs):
        log.append(dict(eqs))
        if "id" in eqs and "athlete_id" in eqs:
            return detail_row                 # get_session_metrics detail fetch
        if "id" in eqs:
            return anchor                     # anchor (ownership) fetch
        return list_rows                      # list_athlete_sessions

    admin = MagicMock()

    def table(name):
        if name == "coaches":
            t = MagicMock()
            res = MagicMock()
            res.data = {"id": coach_id} if coach_id else None
            t.select.return_value = t
            t.eq.return_value = t
            t.single.return_value = t
            t.execute.return_value = res
            return t
        if name == "sessions":
            return _FakeSessionsQuery(resolver)
        return MagicMock()

    admin.table.side_effect = table
    return admin


def _text_resp(text):
    from unittest.mock import MagicMock
    block = MagicMock()
    block.type = "text"
    block.text = text
    r = MagicMock()
    r.stop_reason = "end_turn"
    r.content = [block]
    return r


def _tool_resp(name, tool_input, tool_id="tu-1"):
    from unittest.mock import MagicMock
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = tool_input
    block.id = tool_id
    r = MagicMock()
    r.stop_reason = "tool_use"
    r.content = [block]
    return r


def _mock_anthropic_seq(monkeypatch, responses):
    """Patch Anthropic so successive create() calls return the given responses in order."""
    from unittest.mock import MagicMock
    import api

    create = MagicMock(side_effect=list(responses))
    client = MagicMock()
    client.messages.create = create
    monkeypatch.setattr(api.anthropic, "Anthropic", lambda *a, **k: client)
    return create


class TestCoachChatTools:
    """The bounded tool-use loop: execution, athlete/coach scoping, termination, backward-compat."""

    def test_tool_runs_then_answers(self, api_client, monkeypatch):
        """Model requests list_athlete_sessions; server runs it (athlete+coach scoped) and answers (AC-1)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        scope_log = []
        list_rows = [{
            "id": "sess-0", "created_at": "2026-06-01T00:00:00Z", "name": "Old swim",
            "stroke_type": "breaststroke",
            "metrics_json": {"session": {"mean_dps_m": 1.2, "stroke_rate_spm": 30.0}},
        }]
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _tool_admin(list_rows=list_rows, scope_log=scope_log))
        create = _mock_anthropic_seq(monkeypatch, [
            _tool_resp("list_athlete_sessions", {"limit": 5}),
            _text_resp("Her DPS is trending up."),
        ])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["reply"] == "Her DPS is trending up."
        assert create.call_count == 2
        # The list query was scoped to BOTH coach_id and athlete_id.
        list_q = [q for q in scope_log if "id" not in q]
        assert any(q.get("coach_id") == "coach-1" and q.get("athlete_id") == "ath-1" for q in list_q)
        # A tool_result was fed back on the second model call.
        second_msgs = create.call_args_list[1].kwargs["messages"]
        assert any(isinstance(msg.get("content"), list)
                   and any(b.get("type") == "tool_result" for b in msg["content"])
                   for msg in second_msgs)

    def test_foreign_session_blocked_no_leak(self, api_client, monkeypatch):
        """get_session_metrics for a session outside the athlete returns an error, never data (AC-2)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        scope_log = []
        # detail_row=None simulates "no row matches id + this athlete + this coach".
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _tool_admin(detail_row=None, scope_log=scope_log))
        create = _mock_anthropic_seq(monkeypatch, [
            _tool_resp("get_session_metrics", {"session_id": "someone-elses-session"}),
            _text_resp("I don't have that session for her."),
        ])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        # The detail query was filtered by coach_id AND athlete_id.
        detail_q = [q for q in scope_log if "id" in q and "athlete_id" in q]
        assert detail_q and detail_q[0]["coach_id"] == "coach-1" and detail_q[0]["athlete_id"] == "ath-1"
        # The tool result fed back to the model carried an error, not foreign metrics.
        tool_result = None
        for msg in create.call_args_list[1].kwargs["messages"]:
            if isinstance(msg.get("content"), list):
                for b in msg["content"]:
                    if b.get("type") == "tool_result":
                        tool_result = b["content"]
        assert tool_result is not None
        assert "not available" in tool_result.lower()
        assert "Session Metrics" not in tool_result

    def test_loop_terminates_under_cap(self, api_client, monkeypatch):
        """A model that only ever asks for tools still terminates with a reply (AC-3)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _tool_admin(list_rows=[]))
        always_tool = [_tool_resp("list_athlete_sessions", {}) for _ in range(api.MAX_TOOL_ITERS)]
        create = _mock_anthropic_seq(monkeypatch, always_tool)
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["reply"]  # non-empty fallback
        assert create.call_count == api.MAX_TOOL_ITERS

    def test_no_tool_single_call(self, api_client, monkeypatch):
        """No tool needed → one model call, reply as before (backward compatible, AC-3)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _tool_admin())
        create = _mock_anthropic_seq(monkeypatch, [_text_resp("Solid and steady.")])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["reply"] == "Solid and steady."
        assert create.call_count == 1


# ── POST /coach/chat — team-wide tools (33-02) ─────────────────────────────────

def test_team_tools_declared():
    """Three roster tools exist and the prompt mentions the kick caveat (AC-3)."""
    import coach

    names = {t["name"] for t in coach.TEAM_TOOLS}
    assert names == {"rank_athletes", "rank_progress", "team_summary"}
    assert "kick" in coach._build_system_prompt("freestyle").lower()


def _team_admin(anchor=ANCHOR_ROW, athletes=None, team_sessions=None, coach_id="coach-1", scope_log=None):
    """Fake admin for team tests: serves coaches/athletes/sessions and records eq() filters."""
    from unittest.mock import MagicMock
    log = scope_log if scope_log is not None else []
    athletes = [] if athletes is None else athletes
    team_sessions = [] if team_sessions is None else team_sessions

    class _Q:
        def __init__(self, kind):
            self.kind = kind
            self.eqs = {}

        def select(self, *a, **k):
            return self

        def order(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def single(self, *a, **k):
            return self

        def eq(self, col, val):
            self.eqs[col] = val
            return self

        def execute(self):
            log.append({"table": self.kind, **self.eqs})
            r = MagicMock()
            if self.kind == "coaches":
                r.data = {"id": coach_id} if coach_id else None
            elif self.kind == "athletes":
                r.data = athletes
            elif self.kind == "sessions":
                r.data = anchor if "id" in self.eqs else team_sessions
            else:
                r.data = None
            return r

    admin = MagicMock()
    admin.table.side_effect = lambda name: _Q(name)
    return admin


class TestCoachChatTeam:
    """Roster-scoped tools: coach scoping, out-of-roster exclusion, structured data return."""

    def test_rank_athletes_coach_scoped_and_structured(self, api_client, monkeypatch):
        """rank_athletes is coach-scoped, excludes out-of-roster, and returns structured data (AC-1/2)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        scope_log = []
        athletes = [{"id": "ath-1", "name": "Maria"}, {"id": "ath-2", "name": "Sam"}]
        team_sessions = [
            {"athlete_id": "ath-1", "created_at": "2026-06-14T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.4}}},
            {"athlete_id": "ath-2", "created_at": "2026-06-14T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.0}}},
            {"athlete_id": "ath-9", "created_at": "2026-06-14T00:00:00Z",   # not in roster
             "metrics_json": {"session": {"mean_dps_m": 0.1}}},
        ]
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _team_admin(athletes=athletes, team_sessions=team_sessions, scope_log=scope_log))
        create = _mock_anthropic_seq(monkeypatch, [
            _tool_resp("rank_athletes", {"metric": "mean_dps_m", "ascending": True}),
            _text_resp("Sam is lowest on distance per stroke."),
        ])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        # Both roster queries filtered by coach_id.
        assert any(q["table"] == "athletes" and q.get("coach_id") == "coach-1" for q in scope_log)
        assert any(q["table"] == "sessions" and "id" not in q and q.get("coach_id") == "coach-1" for q in scope_log)
        # Structured data returned; out-of-roster athlete excluded; ascending order correct.
        data = resp.json()["data"]
        rank = next(d for d in data if d["tool"] == "rank_athletes")["result"]["ranking"]
        assert [r["athlete_name"] for r in rank] == ["Sam", "Maria"]
        assert "ath-9" not in str(rank)

    def test_rank_progress_excludes_thin_data(self, api_client, monkeypatch):
        """rank_progress reports improvement and sets aside athletes with too few sessions (AC-3)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        athletes = [{"id": "ath-1", "name": "Maria"}, {"id": "ath-2", "name": "Sam"}]
        team_sessions = [
            {"athlete_id": "ath-1", "created_at": "2026-06-14T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.3}}},
            {"athlete_id": "ath-1", "created_at": "2026-06-01T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.0}}},
            {"athlete_id": "ath-2", "created_at": "2026-06-14T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.1}}},  # only one session
        ]
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _team_admin(athletes=athletes, team_sessions=team_sessions))
        _mock_anthropic_seq(monkeypatch, [
            _tool_resp("rank_progress", {"metric": "mean_dps_m"}),
            _text_resp("Maria improved the most."),
        ])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        result = next(d for d in resp.json()["data"] if d["tool"] == "rank_progress")["result"]
        assert [p["athlete_name"] for p in result["progressed"]] == ["Maria"]
        assert result["insufficient_data"] == [{"athlete_name": "Sam", "sessions_with_metric": 1}]

    def test_rank_progress_clamps_nonpositive_min_sessions(self, api_client, monkeypatch):
        """A non-positive min_sessions from the model is clamped, not crashed (no IndexError)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        athletes = [{"id": "ath-1", "name": "Maria"}, {"id": "ath-2", "name": "Sam"}]
        team_sessions = [
            {"athlete_id": "ath-1", "created_at": "2026-06-14T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.3}}},
            {"athlete_id": "ath-1", "created_at": "2026-06-01T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.0}}},
            {"athlete_id": "ath-2", "created_at": "2026-06-14T00:00:00Z",
             "metrics_json": {"session": {"mean_dps_m": 1.1}}},  # only one session
        ]
        monkeypatch.setattr(api, "_get_supabase_admin",
                            lambda: _team_admin(athletes=athletes, team_sessions=team_sessions))
        _mock_anthropic_seq(monkeypatch, [
            _tool_resp("rank_progress", {"metric": "mean_dps_m", "min_sessions": 0}),
            _text_resp("Maria improved the most."),
        ])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        result = next(d for d in resp.json()["data"] if d["tool"] == "rank_progress")["result"]
        # Clamped to the ≥2 floor → behaves like the default, no crash.
        assert [p["athlete_name"] for p in result["progressed"]] == ["Maria"]
        assert result["insufficient_data"] == [{"athlete_name": "Sam", "sessions_with_metric": 1}]


# ── POST /coach/chat — drill recommendation (33-03) ────────────────────────────

def test_drill_tool_declared():
    import coach

    assert any(t["name"] == "recommend_drills" for t in coach.DRILL_TOOLS)
    assert "drill" in coach._build_system_prompt("breaststroke").lower()


def _anchor_with_session(session_metrics):
    """An anchor session row whose metrics_json.session carries the given metrics."""
    return {**ANCHOR_ROW, "metrics_json": {"session": session_metrics, "cycles": []}}


class TestCoachChatDrills:
    """recommend_drills grounds the call-to-action in the library, matched to session metrics."""

    def test_recommends_library_drills_for_flagged_session(self, api_client, monkeypatch):
        """A low-DPS / low-trough session surfaces matching library drills (AC-1)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        anchor = _anchor_with_session({"mean_dps_m": 1.3, "mean_trough_vel_ms": 0.03})
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _tool_admin(anchor=anchor))
        _mock_anthropic_seq(monkeypatch, [
            _tool_resp("recommend_drills", {}),
            _text_resp("Your DPS is 1.3 m — try the streamline glide hold."),
        ])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        result = next(d for d in resp.json()["data"] if d["tool"] == "recommend_drills")["result"]
        ids = {d["id"] for d in result["drills"]}
        assert "streamline-glide-hold" in ids
        assert "low_dps" in result["flags"]

    def test_clean_session_returns_no_drills(self, api_client, monkeypatch):
        """A session with no flagged problem returns an empty list + an honest note (AC-2)."""
        import api

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        anchor = _anchor_with_session({"mean_dps_m": 1.9, "mean_trough_vel_ms": 0.30,
                                       "cv_isi": 0.05, "fatigue_index_pct": 1})
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _tool_admin(anchor=anchor))
        _mock_anthropic_seq(monkeypatch, [
            _tool_resp("recommend_drills", {}),
            _text_resp("Form looks solid."),
        ])
        resp = api_client.post("/coach/chat", json=_chat_body(),
                               headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        result = next(d for d in resp.json()["data"] if d["tool"] == "recommend_drills")["result"]
        assert result["drills"] == []
        assert "note" in result


# ── GET /sessions/{id}/ratings (coach-friendly pillar ratings) ──────────────────

RATINGS_TARGET = {
    "coach_id": "coach-1",
    "stroke_type": "breaststroke",
    "athlete_id": "ath-1",
    "created_at": "2026-06-02T00:00:00Z",
    "metrics_json": {
        "session": {"mean_vel_ms": 1.25, "max_vel_ms": 2.9, "mean_dps_m": 1.6,
                    "cv_arm_peak_vel": 0.09, "cv_isi": 0.2, "fatigue_index_pct": 6.0},
        "data_quality": {"segmentation_reliable": False},
    },
}

RATINGS_PRIOR = [
    {"created_at": "2026-05-20T00:00:00Z",
     "metrics_json": {"session": {"mean_vel_ms": 1.05, "mean_dps_m": 1.4,
                                  "cv_arm_peak_vel": 0.07, "fatigue_index_pct": 3.0},
                      "data_quality": {"segmentation_reliable": False}}},
]


def _ratings_admin(target=RATINGS_TARGET, prior=RATINGS_PRIOR, coach_id="coach-1",
                   prior_raises=False):
    """Fake supabase admin: coaches + sessions. All queries use .limit(...).execute() (no
    .single()). The target session fetch ends at the base chain's execute(); the prior-sessions
    fetch is distinguished by the .lt() call, which switches to a separate chain."""
    from unittest.mock import MagicMock

    admin = MagicMock()

    def table(name):
        t = MagicMock()
        if name == "coaches":
            res = MagicMock()
            res.data = [{"id": coach_id}] if coach_id else []
            t.select.return_value = t
            t.eq.return_value = t
            t.limit.return_value = t
            t.execute.return_value = res
            return t
        if name == "sessions":
            t.select.return_value = t
            t.eq.return_value = t
            t.limit.return_value = t
            target_res = MagicMock()
            target_res.data = [target] if target else []
            t.execute.return_value = target_res   # target fetch: ...limit(1).execute()
            prior_chain = MagicMock()
            prior_chain.order.return_value = prior_chain
            prior_chain.limit.return_value = prior_chain
            prior_res = MagicMock()
            prior_res.data = prior
            if prior_raises:
                prior_chain.execute.side_effect = RuntimeError("simulated DB failure")
            else:
                prior_chain.execute.return_value = prior_res
            t.lt.return_value = prior_chain        # prior fetch: ...lt(...).order(...).limit(10).execute()
            return t
        return MagicMock()

    admin.table.side_effect = table
    return admin


class TestSessionRatings:
    """GET /sessions/{id}/ratings — auth, ownership, pillar payload."""

    def test_no_auth_401(self):
        from fastapi.testclient import TestClient
        import api

        client = TestClient(api.app, raise_server_exceptions=True)
        assert client.get("/sessions/sess-1/ratings").status_code == 401

    def test_owned_session_returns_pillars(self, api_client, monkeypatch):
        import api

        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _ratings_admin())
        resp = api_client.get("/sessions/sess-1/ratings",
                              headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["stroke"] == "breaststroke"
        assert data["has_baseline"] is True
        assert {p["key"] for p in data["pillars"]} == {"speed", "stroke_length", "consistency", "endurance"}
        assert data["rating_colors"]["good"] == "#2d9e5f"
        speed = next(p for p in data["pillars"] if p["key"] == "speed")
        assert speed["band"] == "good"          # 1.25 ≥ 1.20
        assert speed["trend"] == "improved"      # 1.25 vs 1.05 baseline
        assert speed["provisional"] is True      # segmentation unreliable

    def test_first_session_when_no_prior(self, api_client, monkeypatch):
        import api

        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _ratings_admin(prior=[]))
        data = api_client.get("/sessions/sess-1/ratings",
                              headers={"Authorization": "Bearer x"}).json()
        assert data["has_baseline"] is False
        assert all(p["trend"] == "first_session" for p in data["pillars"])

    def test_foreign_session_not_found(self, api_client, monkeypatch):
        import api

        # coach_id filter means a session this coach doesn't own simply isn't returned
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _ratings_admin(target=None))
        resp = api_client.get("/sessions/sess-1/ratings",
                              headers={"Authorization": "Bearer x"})
        assert resp.status_code == 404

    def test_no_coach_profile_403(self, api_client, monkeypatch):
        import api

        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _ratings_admin(coach_id=None))
        resp = api_client.get("/sessions/sess-1/ratings",
                              headers={"Authorization": "Bearer x"})
        assert resp.status_code == 403

    def test_backend_failure_surfaces_5xx(self, monkeypatch):
        """A real DB failure on the prior-sessions query must surface as 5xx, not a degraded 200."""
        from fastapi.testclient import TestClient
        from starlette.requests import Request
        import api
        from api import app, require_auth

        def mock_auth(request: Request):
            request.state.user_id = "test-user-id"

        app.dependency_overrides[require_auth] = mock_auth
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _ratings_admin(prior_raises=True))
        # raise_server_exceptions=False so the unhandled error becomes a 500 response
        client = TestClient(app, raise_server_exceptions=False)
        try:
            resp = client.get("/sessions/sess-1/ratings", headers={"Authorization": "Bearer x"})
            assert resp.status_code >= 500
        finally:
            app.dependency_overrides.clear()


# ── GET /team/overview (team coach dashboard) ──────────────────────────────────
from datetime import date as _date, timedelta as _timedelta


def _today_iso(days_ago=0):
    return (_date.today() - _timedelta(days=days_ago)).isoformat() + "T00:00:00Z"


TEAM_ATHLETES = [
    {"id": "ath-1", "name": "Maya R.", "stroke_type": "breaststroke"},
    {"id": "ath-2", "name": "Theo K.", "stroke_type": "breaststroke"},
    {"id": "ath-3", "name": "New Kid", "stroke_type": "breaststroke"},  # no sessions yet
]


def _team_sessions():
    """Newest-first across the roster (mirrors the endpoint's .order(created_at desc))."""
    return [
        {"id": "s-a1-2", "athlete_id": "ath-1", "stroke_type": "breaststroke",
         "created_at": _today_iso(1),
         "metrics_json": {"session": {"mean_vel_ms": 1.25, "mean_dps_m": 1.6,
                                      "cv_arm_peak_vel": 0.09, "fatigue_index_pct": 6.0},
                          "data_quality": {"segmentation_reliable": True}}},
        {"id": "s-a2-1", "athlete_id": "ath-2", "stroke_type": "breaststroke",
         "created_at": _today_iso(2),
         "metrics_json": {"session": {"mean_vel_ms": 0.50, "mean_dps_m": 0.6,
                                      "cv_arm_peak_vel": 0.28, "fatigue_index_pct": 35.0},
                          "data_quality": {"segmentation_reliable": True}}},
        {"id": "s-a1-1", "athlete_id": "ath-1", "stroke_type": "breaststroke",
         "created_at": _today_iso(20),
         "metrics_json": {"session": {"mean_vel_ms": 1.05},
                          "data_quality": {"segmentation_reliable": True}}},
        # foreign athlete not in this coach's roster → must be dropped from ratings + recent
        {"id": "s-foreign", "athlete_id": "ath-X", "stroke_type": "breaststroke",
         "created_at": _today_iso(0),
         "metrics_json": {"session": {"mean_vel_ms": 9.9}}},
    ]


def _team_overview_admin(coach_id="coach-1", athletes=None, sessions=None, sessions_raises=False):
    """Fake supabase admin serving coaches + athletes + sessions for /team/overview."""
    from unittest.mock import MagicMock

    if athletes is None:
        athletes = TEAM_ATHLETES
    if sessions is None:
        sessions = _team_sessions()

    admin = MagicMock()

    def table(name):
        t = MagicMock()
        res = MagicMock()
        if name == "coaches":
            res.data = [{"id": coach_id}] if coach_id else []
        elif name == "athletes":
            res.data = athletes
        elif name == "sessions":
            res.data = sessions
        t.select.return_value = t
        t.eq.return_value = t
        t.order.return_value = t
        t.limit.return_value = t
        if name == "sessions" and sessions_raises:
            t.execute.side_effect = RuntimeError("simulated DB failure")
        else:
            t.execute.return_value = res
        return t

    admin.table.side_effect = table
    return admin


class TestTeamOverview:
    """GET /team/overview — auth, coach scope, dashboard rollup."""

    def test_no_auth_401(self):
        from fastapi.testclient import TestClient
        import api

        client = TestClient(api.app, raise_server_exceptions=True)
        assert client.get("/team/overview").status_code == 401

    def test_shape_scope_and_rollup(self, api_client, monkeypatch):
        import api

        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _team_overview_admin())
        resp = api_client.get("/team/overview", headers={"Authorization": "Bearer x"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert set(data) >= {"athlete_count", "tested_this_week", "pillars", "athletes",
                             "recent", "needs_attention", "rating_colors"}
        assert data["athlete_count"] == 3
        assert data["tested_this_week"] == 2          # ath-1 (1d) + ath-2 (2d), ath-3 untested
        assert data["rating_colors"]["good"] == "#2d9e5f"

        # coach scope: the foreign athlete/session never leaks into ratings or the feed
        ath_ids = {a["athlete_id"] for a in data["athletes"]}
        assert "ath-X" not in ath_ids
        assert all(r["athlete_id"] != "ath-X" for r in data["recent"])
        assert all(r["session_id"] != "s-foreign" for r in data["recent"])

        # no-session athlete present with empty pillars
        new_kid = next(a for a in data["athletes"] if a["athlete_id"] == "ath-3")
        assert new_kid["pillars"] == [] and new_kid["last_tested"] is None

        # band distribution counts both rated athletes' speed pillar
        speed = next(p for p in data["pillars"] if p["key"] == "speed")
        assert speed["good"] == 1 and speed["needs_work"] == 1

        # needs-attention surfaces the weak + the never-tested athlete, not the clean one
        na_ids = {n["athlete_id"] for n in data["needs_attention"]}
        assert {"ath-2", "ath-3"} <= na_ids
        assert "ath-1" not in na_ids                   # good bands, improved, tested recently

    def test_no_coach_profile_403(self, api_client, monkeypatch):
        import api

        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _team_overview_admin(coach_id=None))
        resp = api_client.get("/team/overview", headers={"Authorization": "Bearer x"})
        assert resp.status_code == 403

    def test_backend_failure_surfaces_5xx(self, monkeypatch):
        """A real DB failure on the sessions query must surface as 5xx, not a degraded 200."""
        from fastapi.testclient import TestClient
        from starlette.requests import Request
        import api
        from api import app, require_auth

        def mock_auth(request: Request):
            request.state.user_id = "test-user-id"

        app.dependency_overrides[require_auth] = mock_auth
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: _team_overview_admin(sessions_raises=True))
        client = TestClient(app, raise_server_exceptions=False)
        try:
            resp = client.get("/team/overview", headers={"Authorization": "Bearer x"})
            assert resp.status_code >= 500
        finally:
            app.dependency_overrides.clear()
