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
    "phases",
]


def _post_csv(client, csv_bytes: bytes, head_waist_m: float = 0.0, go_signal_s=None,
              session_start_utc_ms=None, sync_error_ms=None, clock_offset_ms=None):
    """Helper: POST a CSV to /process and return the Response.

    go_signal_s and the three Phase 86-01 session-clock fields are added to the form ONLY
    when supplied, so the ~20 existing callers keep posting the exact field set they always
    did (AC-2 depends on that being true).
    """
    data = {"head_waist_m": str(head_waist_m)}
    if go_signal_s is not None:
        data["go_signal_s"] = str(go_signal_s)
    if session_start_utc_ms is not None:
        data["session_start_utc_ms"] = str(session_start_utc_ms)
    if sync_error_ms is not None:
        data["sync_error_ms"] = str(sync_error_ms)
    if clock_offset_ms is not None:
        data["clock_offset_ms"] = str(clock_offset_ms)
    return client.post(
        "/process",
        files={"file": ("session.csv", io.BytesIO(csv_bytes), "text/csv")},
        data=data,
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


class TestPhaseMetricsScaffold:
    """POST /process — the additive `phases` object (75-01 skeleton, 75-02 boundaries)."""

    def test_phases_has_four_buckets_and_go_signal(self, api_client, synthetic_csv_bytes):
        phases = _post_csv(api_client, synthetic_csv_bytes).json()["phases"]
        for bucket in ("start", "underwater", "swim", "whole"):
            assert bucket in phases
            assert isinstance(phases[bucket], dict)
            assert len(phases[bucket]) > 0
        assert "go_signal_s" in phases
        assert phases["go_signal_s"] is None  # the field is simply not sent on this post

    def test_every_planned_metric_reads_as_an_empty_slot(self, api_client, synthetic_csv_bytes):
        """A `planned` entry is a reserved slot: null value, and it says so. (75-01
        asserted this of EVERY metric; 75-02 implements the first six, so the assertion
        narrows to the still-planned ones and stays true for the rest of Step 2.)"""
        phases = _post_csv(api_client, synthetic_csv_bytes).json()["phases"]
        for bucket in ("start", "underwater", "swim", "whole"):
            for key, entry in phases[bucket].items():
                assert entry["status"] in ("planned", "implemented")
                if entry["status"] == "planned":
                    assert entry["value"] is None, f"{bucket}.{key} should be null (planned)"

    def test_boundaries_are_resolved_with_per_key_sources(self, api_client, synthetic_csv_bytes):
        """Phase 75-02: /process has no annotation to read, so nothing resolves 'manual'."""
        phases = _post_csv(api_client, synthetic_csv_bytes).json()["phases"]
        bounds = phases["boundaries"]
        for key in ("dive_start_s", "underwater_start_s", "stroke_start_s", "finish_s"):
            assert key in bounds
            assert bounds["sources"][key] in ("auto", "detected", "none")
        assert bounds["sources"]["underwater_start_s"] in ("detected", "none")

    def test_the_four_underwater_metrics_report_implemented(self, api_client, synthetic_csv_bytes):
        phases = _post_csv(api_client, synthetic_csv_bytes).json()["phases"]
        for key in ("uw_duration", "uw_distance", "uw_avg_speed", "uw_surface_ratio"):
            assert phases["underwater"][key]["status"] == "implemented"

    def test_reaction_time_reserved_under_start(self, api_client, synthetic_csv_bytes):
        phases = _post_csv(api_client, synthetic_csv_bytes).json()["phases"]
        assert "reaction_time" in phases["start"]

    def test_phases_addition_does_not_disturb_existing_session_dict(self, api_client, synthetic_csv_bytes):
        """Additive-only proof: session/cycles/data_quality shape is unchanged by this plan."""
        data = _post_csv(api_client, synthetic_csv_bytes).json()
        for key in DATA_QUALITY_KEYS:
            assert key in data["data_quality"]
        assert isinstance(data["session"], dict)
        assert isinstance(data["cycles"], list)


class TestGoSignalOnProcess:
    """POST /process — the optional `go_signal_s` form field (Phase 84-02, the coach GO marker).

    The app converts its raw press time onto the session clock against the META correlation it
    has computed since Phase 47, so what arrives here is already in session-clock seconds.
    """

    def test_go_signal_absent_stays_none(self, api_client, synthetic_csv_bytes):
        """AC-2 — every pre-84-02 caller omits the field, and must be unaffected."""
        data = _post_csv(api_client, synthetic_csv_bytes).json()
        assert data["phases"]["go_signal_s"] is None
        assert data["phases"]["start"]["reaction_time"]["value"] is None

    def test_go_signal_form_field_threads_through(self, api_client, synthetic_csv_bytes):
        """AC-1 — the field reaches PhaseContext instead of the old hardcoded None."""
        resp = _post_csv(api_client, synthetic_csv_bytes, go_signal_s="3.5")
        assert resp.status_code == 200, resp.text
        assert resp.json()["phases"]["go_signal_s"] == 3.5

    @pytest.mark.parametrize("bad", ["-1.0", "nan", "inf", "-inf"])
    def test_go_signal_bad_value_is_dropped_not_rejected(
        self, api_client, synthetic_csv_bytes, bad,
    ):
        """AC-3 — the request carries the swim, which is irreplaceable; the marker is not.

        ⚠ Do NOT "fix" this into a 422 to match PUT /sessions/{id}/go-signal. That endpoint is
        allowed to reject because the request is ONLY about the GO time. Here, rejecting would
        cost the coach the session.
        """
        resp = _post_csv(api_client, synthetic_csv_bytes, go_signal_s=bad)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["phases"]["go_signal_s"] is None
        assert body["session"]["mean_vel_ms"] is not None  # the swim still processed

    def test_go_signal_unparseable_is_the_one_422(self, api_client, synthetic_csv_bytes):
        """The single AC-3 case that does NOT reach the handler: FastAPI 422s at the
        Optional[float] coercion before any of our code runs. Pinned here so the asymmetry
        with the test above is deliberate and visible, not a latent surprise."""
        resp = _post_csv(api_client, synthetic_csv_bytes, go_signal_s="banana")
        assert resp.status_code == 422

    def test_reaction_time_computes_with_go_signal(self, api_client, synthetic_csv_bytes):
        """The point of the whole plan: reaction_time stops being structurally null.

        The synthetic fixture spins the wheel at a constant rate from t=0, so detect_phases
        puts motion onset at t[0] = 0.0 s. A positive GO would therefore resolve to a negative
        reaction time and correctly return None. GO = 0.0 is the only value this fixture can
        carry, and it yields the degenerate-but-real 0.0 — enough to prove the value is computed
        from the supplied marker rather than short-circuited. The honest reaction-time magnitude
        is a device question, not a fixture one (see the plan's human-verify).
        """
        body = _post_csv(api_client, synthetic_csv_bytes, go_signal_s="0.0").json()
        assert body["phases"]["go_signal_s"] == 0.0
        entry = body["phases"]["start"]["reaction_time"]
        assert entry["value"] is not None
        assert entry["value"] >= 0


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


def _team_admin(anchor=ANCHOR_ROW, athletes=None, team_sessions=None, coach_id="coach-1",
                team_id="team-1", scope_log=None):
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
                r.data = {"id": coach_id, "team_id": team_id} if coach_id else None
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
        # Roster scoping is split by design (Phase 51-02): athletes has no coach_id column, so the
        # roster is team-scoped; sessions does have one and stays coach-scoped.
        assert any(q["table"] == "athletes" and q.get("team_id") == "team-1" for q in scope_log)
        assert not any(q["table"] == "athletes" and "coach_id" in q for q in scope_log)
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
        assert speed["provisional"] is False     # Phase 54: segmentation no longer gates this

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
            res.data = [{"id": coach_id, "team_id": "team-1"}] if coach_id else []
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


# ── Regression: POST /athletes insert chain must not call .single() on a mutation builder ──
# Bug (Phase 48): supabase-py's .insert() returns a SyncQueryRequestBuilder, and .select()
# after it stays a mutation builder that has NO .single() method — so `.insert().select()
# .single()` raised `'SyncQueryRequestBuilder' object has no attribute 'single'` and blocked
# all athlete creation. The endpoint must call .execute() and index resp.data[0] instead.
#
# This guard imports the REAL postgrest builder class. It deliberately does NOT go through the
# app's supabase client: conftest globally mocks `create_client` to return a MagicMock (which
# has every attribute), and that mock is exactly why this bug reached production undetected.

def test_mutation_builder_class_lacks_single():
    """The builder .insert() returns must have no .single() — so the endpoint can't reintroduce it."""
    from postgrest._sync.request_builder import SyncQueryRequestBuilder

    assert not hasattr(SyncQueryRequestBuilder, "single")


# ── Phase 52: /process persists the TRUE decimated sample rate ────────────────
# run_pipeline decimates by an integer factor, so the requested 100 Hz is never
# achieved. api.py used to discard the real value (API-AUDIT F3), leaving every
# consumer to guess — and guess wrong (F2).

class TestSampleRatePersisted:
    def _admin_and_post(self, api_client, monkeypatch, csv_bytes):
        from unittest.mock import MagicMock
        import api
        admin = MagicMock()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        monkeypatch.setattr(
            api, "_get_coach_row",
            lambda *a, **k: {"id": "coach-1", "device_limit": None,
                             "monthly_session_limit": None},
        )
        resp = api_client.post(
            "/process",
            files={"file": ("session.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"head_waist_m": "0.0", "athlete_id": "ath-1"},
            headers={"Authorization": "Bearer fake-token-mocked"},
        )
        assert resp.status_code == 200, resp.text
        return admin.table.return_value.insert.call_args[0][0]

    def test_insert_carries_real_rate(self, api_client, monkeypatch,
                                      synthetic_csv_bytes):
        """AC-1: the synthetic fixture is ~270 Hz → factor 3 → ~90 Hz, not 100.

        The exact value comes from the fixture's real timestamp spacing (~269.98 Hz),
        so this asserts the neighbourhood, not a nominal constant — asserting an exact
        90.0 would just be re-encoding the same wrong-constant mistake.
        """
        row = self._admin_and_post(api_client, monkeypatch, synthetic_csv_bytes)
        assert "sample_rate_hz" in row
        assert row["sample_rate_hz"] == pytest.approx(90.0, rel=1e-3)
        assert row["sample_rate_hz"] != 100

    def test_rate_is_a_plain_float(self, api_client, monkeypatch,
                                   synthetic_csv_bytes):
        """A numpy scalar here would break JSON serialization on insert."""
        row = self._admin_and_post(api_client, monkeypatch, synthetic_csv_bytes)
        assert type(row["sample_rate_hz"]) is float

    def test_rate_matches_the_returned_profile_length(self, api_client, monkeypatch,
                                                      synthetic_csv_bytes):
        """The stored rate must describe the stored profile, not a nominal target."""
        row = self._admin_and_post(api_client, monkeypatch, synthetic_csv_bytes)
        from conftest import SYNTHETIC_DURATION_S
        n = len(row["velocity_profile"])
        assert n / row["sample_rate_hz"] == pytest.approx(SYNTHETIC_DURATION_S, abs=0.5)

    def test_insert_carries_acceleration_profile(self, api_client, monkeypatch,
                                                 synthetic_csv_bytes):
        """Phase 64-02: /process persists acceleration_profile, same length as velocity,
        a plain list (numpy would break JSON serialization), NaNs cleaned to None."""
        row = self._admin_and_post(api_client, monkeypatch, synthetic_csv_bytes)
        assert "acceleration_profile" in row
        accel = row["acceleration_profile"]
        assert isinstance(accel, list)
        assert len(accel) == len(row["velocity_profile"])
        assert all(x is None or isinstance(x, float) for x in accel)


# ── Phase 70 QR slate: /process persists recording_token ONLY when sent ───────
# The phone displays this token as a QR at record start; the web decodes it to match a clip to a
# session. It must be stored when sent, and ABSENT from the insert when not — so the payload stays
# valid on a DB that has not yet had patch_13 applied (existing mobile builds send nothing).

class TestRecordingTokenPersisted:
    def _row(self, api_client, monkeypatch, csv_bytes, token):
        from unittest.mock import MagicMock
        import api
        admin = MagicMock()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        monkeypatch.setattr(
            api, "_get_coach_row",
            lambda *a, **k: {"id": "coach-1", "device_limit": None,
                             "monthly_session_limit": None},
        )
        data = {"head_waist_m": "0.0", "athlete_id": "ath-1"}
        if token is not None:
            data["recording_token"] = token
        resp = api_client.post(
            "/process",
            files={"file": ("session.csv", io.BytesIO(csv_bytes), "text/csv")},
            data=data,
            headers={"Authorization": "Bearer fake-token-mocked"},
        )
        assert resp.status_code == 200, resp.text
        return admin.table.return_value.insert.call_args[0][0]

    def test_token_carried_when_sent(self, api_client, monkeypatch, synthetic_csv_bytes):
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes, "tok_abc123")
        assert row["recording_token"] == "tok_abc123"

    def test_token_absent_when_not_sent(self, api_client, monkeypatch, synthetic_csv_bytes):
        """No token → the key must NOT be in the insert (valid on a pre-patch_13 DB)."""
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes, None)
        assert "recording_token" not in row


# ── Schema contract ───────────────────────────────────────────────────────────
# Promoted from tools/schema_contract.py (Phase 51-01) into the suite so the phantom-column
# bug class cannot silently return. This guards code against a SNAPSHOT, not against the live
# database — supabase/live_schema.json is point-in-time. After any migration, refresh it with:
#     python tools/introspect_schema.py
# A mock-based test cannot cover this: conftest replaces create_client with a MagicMock that
# answers every attribute, so a chain naming a nonexistent column passes happily. The guard
# has to be static.

class TestSchemaContract:
    """Every column api.py names against a table must exist in the live-schema snapshot."""

    @staticmethod
    def _schema():
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        return json.loads((root / "supabase" / "live_schema.json").read_text(encoding="utf-8"))

    def test_api_py_names_no_unknown_columns(self):
        from pathlib import Path
        from tools.schema_contract import find_violations

        root = Path(__file__).resolve().parent.parent
        src = root / "api.py"
        violations = find_violations(src.read_text(encoding="utf-8"), self._schema())

        assert not violations, "api.py references columns absent from the live schema:\n" + "\n".join(
            f"  {src}:{v.line}  {v.table}.{v.column}  [{v.kind}]" for v in violations
        )

    def test_extractor_catches_a_known_bad_reference(self):
        """Self-check: a silently broken extractor would make the test above pass forever."""
        from tools.schema_contract import find_violations

        schema = {"athletes": ["id", "team_id", "name"]}
        bad = 'sb.table("athletes").select("id").eq("coach_id", x).execute()'
        violations = find_violations(bad, schema)

        assert len(violations) == 1
        assert violations[0].table == "athletes"
        assert violations[0].column == "coach_id"
        assert violations[0].kind == "eq"

    def test_extractor_catches_bad_insert_payload_keys(self):
        """The live blocker was an insert payload key, not a filter — cover that path too."""
        from tools.schema_contract import find_violations

        schema = {"athletes": ["id", "team_id", "name"]}
        bad = 'sb.table("athletes").insert({"team_id": t, "coach_id": c, "name": n}).execute()'
        violations = find_violations(bad, schema)

        assert [ (v.table, v.column, v.kind) for v in violations ] == [
            ("athletes", "coach_id", "insert")
        ]

    def test_extractor_ignores_response_dicts_and_star_selects(self):
        """The regex version's failure mode: response-dict keys read as column names."""
        from tools.schema_contract import find_violations

        schema = {"sessions": ["id", "coach_id"]}
        ok = (
            'sb.table("sessions").select("*").eq("id", i).execute()\n'
            'payload = {"session": {}, "cycles": [], "ok": True}\n'
        )
        assert find_violations(ok, schema) == []


# ── Phase 59-02: /process forwards stroke_type to the segmenter dispatch ───────
# compute_session_metrics gained a stroke_type parameter that selects the segmenter
# via metrics.SEGMENTER_BY_STROKE. The value was already in scope at api.py:139 as a
# Form field; it was simply never passed on. Today this changes nothing (the registry
# is empty, so every stroke resolves to the wavelet) — it is wired now so 59-05 is a
# one-line table edit rather than a hunt for call sites.

class TestStrokeTypeForwardedToMetrics:
    def _capture(self, api_client, monkeypatch, csv_bytes, stroke_type):
        import api
        captured = {}
        real = api.m.compute_session_metrics

        def spy(*args, **kwargs):
            captured.update(kwargs)
            return real(*args, **kwargs)

        monkeypatch.setattr(api.m, "compute_session_metrics", spy)
        data = {"head_waist_m": "0.0"}
        if stroke_type is not None:
            data["stroke_type"] = stroke_type
        resp = api_client.post(
            "/process",
            files={"file": ("session.csv", io.BytesIO(csv_bytes), "text/csv")},
            data=data,
            headers={"Authorization": "Bearer fake-token-mocked"},
        )
        assert resp.status_code == 200, resp.text
        return captured

    def test_stroke_type_value_reaches_compute_session_metrics(
            self, api_client, monkeypatch, synthetic_csv_bytes):
        """Assert the VALUE arrives, not merely that the key exists.

        A wired-but-wrong argument (e.g. always None, or the athlete id) is the failure
        mode worth catching — it would look fine until 59-05 filled the registry and
        every stroke silently took the default anyway.
        """
        captured = self._capture(api_client, monkeypatch, synthetic_csv_bytes, "butterfly")
        assert captured.get("stroke_type") == "butterfly"

    def test_omitted_stroke_type_forwards_none(
            self, api_client, monkeypatch, synthetic_csv_bytes):
        """stroke_type is an optional Form field; absent must forward None, not "" or
        a crash, because None is what resolves to the default segmenter."""
        captured = self._capture(api_client, monkeypatch, synthetic_csv_bytes, None)
        assert captured.get("stroke_type") is None


class TestVideoUploadSizeGuard:
    """POST /sessions/{id}/video — oversized clips are rejected before buffering (Phase 67-02).

    The guard runs BEFORE _get_supabase_admin(), so an over-cap file 413s even without Storage
    configured — which is why this test needs no supabase mock. The cap is monkeypatched tiny so
    the test never allocates a real 500 MB buffer.
    """

    def test_oversized_video_returns_413(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "MAX_VIDEO_BYTES", 100)  # tiny cap; a 500-byte clip exceeds it
        resp = api_client.post(
            "/sessions/00000000-0000-0000-0000-000000000000/video",
            files={"file": ("clip.mp4", io.BytesIO(b"x" * 500), "video/mp4")},
            headers={"Authorization": "Bearer fake-token-mocked"},
        )
        assert resp.status_code == 413, resp.text
        assert "too large" in resp.text.lower()


class TestSessionVideos:
    """POST/GET/PATCH/DELETE /sessions/{id}/videos — external multi-camera videos (Phase 69)."""

    def test_oversized_external_returns_413(self, api_client, monkeypatch):
        import api
        monkeypatch.setattr(api, "MAX_VIDEO_BYTES", 100)  # guard runs before admin/ownership
        resp = api_client.post(
            "/sessions/00000000-0000-0000-0000-000000000000/videos",
            files={"file": ("ext.mp4", io.BytesIO(b"x" * 500), "video/mp4")},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 413, resp.text

    def test_external_cap_returns_409(self, api_client, monkeypatch):
        import api
        from unittest.mock import MagicMock
        mock_admin = MagicMock()
        mock_admin.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "a"}, {"id": "b"}, {"id": "c"}  # already at the 3-external cap
        ]
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: mock_admin)
        monkeypatch.setattr(api, "_owned_session", lambda *a, **k: (None, {}))
        resp = api_client.post(
            "/sessions/sess-1/videos",
            files={"file": ("ext.mp4", io.BytesIO(b"tiny"), "video/mp4")},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 409, resp.text
        assert "max" in resp.text.lower()

    def test_list_unifies_primary_and_externals(self, api_client, monkeypatch):
        import api
        from unittest.mock import MagicMock
        mock_admin = MagicMock()
        mock_admin.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"id": "ext-1", "storage_path": "sess-1/ext-1.mp4", "origin_s": 1.5, "label": "Underwater", "created_at": "t"}
        ]
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: mock_admin)
        monkeypatch.setattr(
            api, "_owned_session",
            lambda *a, **k: (None, {"video_path": "sess-1.mp4", "video_origin_s": 0.2}),
        )
        monkeypatch.setattr(api, "_signed_video_url", lambda sb, path: f"signed://{path}")
        resp = api_client.get("/sessions/sess-1/videos", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        vids = resp.json()["videos"]
        assert vids[0]["role"] == "phone" and vids[0]["label"] == "Phone"
        assert any(v["role"] == "external" and v["label"] == "Underwater" for v in vids)

    def test_external_upload_passes_bytes_to_storage(self, api_client, monkeypatch):
        # Regression guard: storage3 rejects a SpooledTemporaryFile, so the handler MUST pass bytes.
        # (The 67-02 "streaming" bug passed file.file and 500'd every real upload; mocks hid it.)
        import api
        from unittest.mock import MagicMock
        mock_admin = MagicMock()
        mock_admin.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: mock_admin)
        monkeypatch.setattr(api, "_owned_session", lambda *a, **k: (None, {}))
        monkeypatch.setattr(api, "_signed_video_url", lambda sb, path: "signed://x")
        resp = api_client.post(
            "/sessions/sess-1/videos",
            files={"file": ("ext.mp4", io.BytesIO(b"realbytes"), "video/mp4")},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200, resp.text
        up = mock_admin.storage.from_.return_value.upload
        assert up.called
        sent = up.call_args.kwargs.get("file")
        assert isinstance(sent, (bytes, bytearray)), (
            f"upload got {type(sent).__name__}; must be bytes (storage3 rejects SpooledTemporaryFile)"
        )


class TestDeleteSessionVideoCleanup:
    """DELETE /sessions/{id} — session-delete video-storage cleanup (Phase 82).

    Two leak sources fixed here: the primary `video_path` was never removed from the `videos`
    bucket, and `session_videos` externals cascade-delete their DB row (ON DELETE CASCADE)
    without their storage object ever being removed — so the storage_path list must be read
    BEFORE the sessions delete fires, or it's gone.
    """

    def _admin(self, session_row, session_videos_rows=None, coach_id="coach-1"):
        from unittest.mock import MagicMock

        admin = MagicMock()

        def table(name):
            t = MagicMock()
            result = MagicMock()
            if name == "coaches":
                result.data = {"id": coach_id}
            elif name == "sessions":
                result.data = session_row
            elif name == "session_videos":
                result.data = session_videos_rows or []
            t.select.return_value = t
            t.delete.return_value = t
            t.eq.return_value = t
            t.single.return_value = t
            t.execute.return_value = result
            return t

        admin.table.side_effect = table
        return admin

    def test_primary_video_removed(self, api_client, monkeypatch):
        import api

        admin = self._admin(session_row={"raw_csv_path": "a/1.csv", "video_path": "sess-1.mp4"})
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.delete("/sessions/sess-1", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        calls = admin.storage.from_.return_value.remove.call_args_list
        assert any(c.args[0] == ["sess-1.mp4"] for c in calls), calls

    def test_external_videos_removed(self, api_client, monkeypatch):
        import api

        admin = self._admin(
            session_row={"raw_csv_path": None, "video_path": None},
            session_videos_rows=[
                {"storage_path": "sess-1/a.mp4"},
                {"storage_path": "sess-1/b.mp4"},
            ],
        )
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.delete("/sessions/sess-1", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        calls = admin.storage.from_.return_value.remove.call_args_list
        assert any(sorted(c.args[0]) == ["sess-1/a.mp4", "sess-1/b.mp4"] for c in calls), calls

    def test_no_video_no_remove_call(self, api_client, monkeypatch):
        import api

        admin = self._admin(session_row={"raw_csv_path": None, "video_path": None})
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.delete("/sessions/sess-1", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        assert not admin.storage.from_.return_value.remove.called

    def test_storage_removal_failure_is_nonfatal(self, api_client, monkeypatch):
        import api

        admin = self._admin(session_row={"raw_csv_path": None, "video_path": "sess-1.mp4"})
        admin.storage.from_.return_value.remove.side_effect = Exception("boom")
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        resp = api_client.delete("/sessions/sess-1", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": True}


# ── Phase 86-01 session clock: /process persists the absolute start + its error bars ──
# session_start_utc_ms is the phone's measured UTC instant of encoder sample #0. Like the
# QR slate's recording_token, each key is written ONLY when a value survived validation, so
# the insert stays valid on a DB that has not yet had patch_14 applied. Absent key and
# explicit NULL are indistinguishable in the stored row (nullable, no default).

class TestSessionClockPersisted:
    # A real instant, comfortably inside the sanity window.
    GOOD_MS = 1756500000123

    def _row(self, api_client, monkeypatch, csv_bytes, **clock):
        from unittest.mock import MagicMock
        import api
        admin = MagicMock()
        monkeypatch.setattr(api, "_get_supabase_admin", lambda: admin)
        monkeypatch.setattr(
            api, "_get_coach_row",
            lambda *a, **k: {"id": "coach-1", "device_limit": None,
                             "monthly_session_limit": None},
        )
        data = {"head_waist_m": "0.0", "athlete_id": "ath-1"}
        for key, val in clock.items():
            if val is not None:
                data[key] = str(val)
        resp = api_client.post(
            "/process",
            files={"file": ("session.csv", io.BytesIO(csv_bytes), "text/csv")},
            data=data,
            headers={"Authorization": "Bearer fake-token-mocked"},
        )
        assert resp.status_code == 200, resp.text
        return admin.table.return_value.insert.call_args[0][0]

    def test_valid_start_is_persisted(self, api_client, monkeypatch, synthetic_csv_bytes):
        """AC-1: a plausible epoch-ms instant reaches the insert unchanged, as an int."""
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes,
                        session_start_utc_ms=self.GOOD_MS)
        assert row["session_start_utc_ms"] == self.GOOD_MS
        assert type(row["session_start_utc_ms"]) is int

    def test_absent_start_leaves_the_key_off(self, api_client, monkeypatch,
                                             synthetic_csv_bytes):
        """AC-2: no field sent -> key absent -> column NULL, and valid pre-patch_14."""
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes)
        assert "session_start_utc_ms" not in row
        assert "sync_error_ms" not in row
        assert "clock_offset_ms" not in row

    def test_absent_start_changes_no_other_stored_field(self, api_client, monkeypatch,
                                                        synthetic_csv_bytes):
        """AC-2: an upload without the new fields stores exactly the pre-change key set."""
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes)
        assert set(row) == {
            "athlete_id", "coach_id", "metrics_json", "velocity_profile",
            "distance_profile", "acceleration_profile", "sample_rate_hz",
            "raw_csv_path", "upload_status", "name", "notes", "stroke_type", "device_id",
        }

    @pytest.mark.parametrize("bad", [
        -5,                # negative
        0,                 # zero
        1756500000,        # SECONDS, not milliseconds - the realistic client bug
        1756500000123456,  # microseconds, not milliseconds
    ])
    def test_bad_start_is_dropped_but_the_swim_is_saved(self, api_client, monkeypatch,
                                                        synthetic_csv_bytes, bad):
        """AC-3: 200, session still inserted, the bad value simply never reaches the row.

        The request carries the swim, which is unrepeatable - losing it over a malformed
        clock annotation would trade an irreplaceable measurement for a replaceable one.
        """
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes,
                        session_start_utc_ms=bad)
        assert "session_start_utc_ms" not in row
        assert row["velocity_profile"]  # the session itself was still saved

    def test_error_bars_ride_along(self, api_client, monkeypatch, synthetic_csv_bytes):
        """AC-5: both diagnostics persist as plain floats."""
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes,
                        sync_error_ms=7.4, clock_offset_ms=-32.1)
        assert row["sync_error_ms"] == pytest.approx(7.4)
        assert row["clock_offset_ms"] == pytest.approx(-32.1)
        assert type(row["sync_error_ms"]) is float

    def test_error_bars_are_independent_of_each_other(self, api_client, monkeypatch,
                                                      synthetic_csv_bytes):
        """AC-5: supplying one must not gate the other."""
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes, sync_error_ms=7.4)
        assert row["sync_error_ms"] == pytest.approx(7.4)
        assert "clock_offset_ms" not in row

        row = self._row(api_client, monkeypatch, synthetic_csv_bytes, clock_offset_ms=-32.1)
        assert row["clock_offset_ms"] == pytest.approx(-32.1)
        assert "sync_error_ms" not in row

    def test_error_bars_do_not_gate_on_a_valid_start(self, api_client, monkeypatch,
                                                     synthetic_csv_bytes):
        """AC-5: a REJECTED start with a recorded offset is the forensic case these exist for."""
        row = self._row(api_client, monkeypatch, synthetic_csv_bytes,
                        session_start_utc_ms=-5, sync_error_ms=7.4, clock_offset_ms=-32.1)
        assert "session_start_utc_ms" not in row
        assert row["sync_error_ms"] == pytest.approx(7.4)
        assert row["clock_offset_ms"] == pytest.approx(-32.1)

    def test_new_fields_are_optional_on_the_plain_post_path(self, api_client,
                                                            synthetic_csv_bytes):
        """AC-2: the ~20 existing callers that send nothing still get a 200."""
        assert _post_csv(api_client, synthetic_csv_bytes).status_code == 200
        assert _post_csv(api_client, synthetic_csv_bytes,
                         session_start_utc_ms=self.GOOD_MS,
                         sync_error_ms=7.4, clock_offset_ms=-32.1).status_code == 200


# ── Phase 86-01: GET /time ────────────────────────────────────────────────────
# Deliberately unauthenticated. The client measures its own RTT against this endpoint and
# derives its clock offset from RTT/2, so any network call inside the handler (require_auth
# does one, to Supabase, per request) would land inside the interval being measured.

class TestServerTimeEndpoint:
    def test_returns_epoch_ms_without_auth(self, api_client):
        """AC-4: 200 and an integer, with NO Authorization header sent."""
        resp = api_client.get("/time")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body) == {"server_utc_ms"}
        assert isinstance(body["server_utc_ms"], int)
        assert not isinstance(body["server_utc_ms"], bool)

    def test_value_tracks_the_host_clock(self, api_client):
        import time as _t
        before = int(_t.time() * 1000)
        got = api_client.get("/time").json()["server_utc_ms"]
        after = int(_t.time() * 1000)
        assert before <= got <= after

    def test_handler_performs_no_network_io(self, api_client, monkeypatch):
        """AC-4: prove it, do not assert it in prose - make every Supabase path explode."""
        import api

        def boom(*a, **k):
            raise AssertionError("GET /time must not touch the network")

        monkeypatch.setattr(api, "_get_supabase", boom)
        monkeypatch.setattr(api, "_get_supabase_admin", boom)
        monkeypatch.setattr(api, "create_client", boom)
        assert api_client.get("/time").status_code == 200

    def test_auth_header_is_neither_required_nor_rejected(self, api_client):
        """A client that sends one anyway must not be 401ed - and still must not be verified."""
        resp = api_client.get("/time", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 200
