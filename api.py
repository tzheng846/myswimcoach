import csv as _csv
import datetime
import io as _io
import json
import math
import os
import tempfile
import time
from typing import Optional

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from supabase import Client, create_client
import stripe as _stripe

SUPABASE_URL              = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY         = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
STRIPE_SECRET_KEY          = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET      = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_STARTER_PRICE_ID    = os.getenv("STRIPE_STARTER_PRICE_ID", "")
STRIPE_ENTERPRISE_PRICE_ID = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "")

_supabase: Client | None = None
_supabase_admin: Client | None = None

def _get_supabase() -> Client | None:
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_ANON_KEY:
        _supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase

def _get_supabase_admin() -> Client | None:
    global _supabase_admin
    if _supabase_admin is None and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        _supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_admin

import metrics as m
import vel_acc_extraction as vae
import coach
import roster_metrics
import anthropic

app = FastAPI()


def require_auth(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = auth_header[7:].strip()
    sb = _get_supabase()
    if sb is None:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    try:
        response = sb.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        request.state.user_id = response.user.id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clean(obj):
    """Recursively sanitize nested dicts/lists for JSON serialization.
    Converts numpy types and NaN/inf to JSON-safe equivalents.
    """
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    return obj


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process")
async def process_session(
    request: Request,
    file: UploadFile = File(...),
    athlete_id: Optional[str] = Form(None),
    head_waist_m: float = Form(0.0),
    name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    stroke_type: Optional[str] = Form(None),
    device_id: Optional[str] = Form(None),
    firmware_version: Optional[str] = Form(None),
    _auth=Depends(require_auth),
):
    raw_path = None
    raw_bytes = None
    try:
        raw_bytes = await file.read()

        # ── Magnet dropout fraction ───────────────────────────────────────────
        _total_rows = 0
        _dropout_rows = 0
        try:
            _reader = _csv.DictReader(_io.StringIO(raw_bytes.decode("utf-8", errors="replace")))
            for _row in _reader:
                _total_rows += 1
                if _row.get("magnet_ok", "1") == "0":
                    _dropout_rows += 1
        except Exception:
            pass
        magnet_dropout_pct = round(100.0 * _dropout_rows / _total_rows, 1) if _total_rows > 0 else 0.0

        # Save upload to temp file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(raw_bytes)
            raw_path = tmp.name

        # ── Signal processing ─────────────────────────────────────────────
        df = vae.load_data(raw_path)
        t_dec, dist_dec, vel, _accel, _actual_fs = vae.run_pipeline(df, 100.0)

        # ── Metrics ──────────────────────────────────────────────────────
        result = m.compute_session_metrics(t_dec, vel, dist_dec, head_waist_m=head_waist_m)

        # ── Data quality summary ──────────────────────────────────────────────
        _dq_warnings = []
        _dq_warnings.append(
            "Kick metrics (pct_cycles_with_kick, mean_arm_kick_ratio, mean_arm_kick_delay_s) "
            "are unreliable — LP filter at default cutoff merges arm-pull and kick peaks"
        )
        if result["session"].get("implausible_cycle_count", 0) > 0:
            _dq_warnings.append(
                f"{result['session']['implausible_cycle_count']} cycle(s) have implausible duration "
                f"(< 0.5 s or > 4.0 s) — possible segmentation artifact"
            )
        if magnet_dropout_pct > 5.0:
            _dq_warnings.append(
                f"Magnet signal lost for {magnet_dropout_pct:.1f}% of samples — encoder reliability reduced"
            )
        if not result["session"].get("segmentation_reliable", False):
            _dq_warnings.append(
                "Cycle segmentation is experimental (wavelet ridge, all strokes) — metrics are provisional"
            )

        data_quality = {
            "magnet_dropout_pct":      magnet_dropout_pct,
            "outlier_cycle_count":     result["session"].get("outlier_cycle_count", 0),
            "implausible_cycle_count": result["session"].get("implausible_cycle_count", 0),
            "total_cycles_raw":        result["session"].get("total_cycles_raw", 0),
            "segmentation_reliable":   result["session"].get("segmentation_reliable", False),
            "warnings":                _dq_warnings,
        }

        # ── Supabase storage + session save ───────────────────────────────
        session_save_error = None
        storage_path = None
        session_id_saved = None
        sb_admin = _get_supabase_admin()

        if athlete_id:
            if not sb_admin:
                session_save_error = "Cloud storage not configured on server"
            else:
                # ── Coach row + limit checks ──────────────────────────────
                coach = _get_coach_row(
                    sb_admin, request.state.user_id,
                    "id, device_limit, monthly_session_limit"
                )
                coach_row_id = coach["id"] if coach else None

                if coach:
                    # Monthly session limit
                    if coach.get("monthly_session_limit") is not None:
                        _now = datetime.datetime.utcnow()
                        _month_start = _now.replace(
                            day=1, hour=0, minute=0, second=0, microsecond=0
                        ).isoformat()
                        try:
                            _sr = (
                                sb_admin.table("sessions")
                                .select("id", count="exact")
                                .eq("coach_id", coach_row_id)
                                .gte("created_at", _month_start)
                                .execute()
                            )
                            _session_count = _sr.count or 0
                        except Exception:
                            _session_count = 0
                        if _session_count >= coach["monthly_session_limit"]:
                            raise HTTPException(
                                status_code=402,
                                detail=(
                                    f"Monthly session limit reached "
                                    f"({coach['monthly_session_limit']} sessions). "
                                    "Upgrade your plan to record more."
                                ),
                            )

                    # Device limit (only when a new device is presented)
                    if device_id and coach.get("device_limit") is not None:
                        try:
                            _ex = (
                                sb_admin.table("devices")
                                .select("chip_id")
                                .eq("chip_id", device_id)
                                .eq("coach_id", coach_row_id)
                                .execute()
                            )
                            _is_new_device = not (_ex.data and len(_ex.data) > 0)
                        except Exception:
                            _is_new_device = False
                        if _is_new_device:
                            try:
                                _dr = (
                                    sb_admin.table("devices")
                                    .select("chip_id", count="exact")
                                    .eq("coach_id", coach_row_id)
                                    .execute()
                                )
                                _device_count = _dr.count or 0
                            except Exception:
                                _device_count = 0
                            if _device_count >= coach["device_limit"]:
                                raise HTTPException(
                                    status_code=402,
                                    detail=(
                                        f"Device limit reached ({coach['device_limit']} device(s)). "
                                        "Upgrade your plan to register more devices."
                                    ),
                                )

                timestamp = int(time.time())
                storage_path = f"{athlete_id}/{timestamp}.csv"

                try:
                    sb_admin.storage.from_("raw-csvs").upload(
                        path=storage_path,
                        file=raw_bytes,
                        file_options={"content-type": "text/csv"},
                    )
                except Exception as upload_exc:
                    storage_path = None  # non-fatal — session row still saved
                    session_save_error = f"Storage upload failed: {upload_exc}"

                if device_id:
                    try:
                        sb_admin.table("devices").upsert({
                            "chip_id":          device_id,
                            "coach_id":         coach_row_id,
                            "firmware_version": firmware_version,
                            "last_seen_at":     "now()",
                        }, on_conflict="chip_id").execute()
                    except Exception:
                        pass  # non-fatal

                try:
                    session_row = {
                        "athlete_id":       athlete_id,
                        "coach_id":         coach_row_id,
                        "metrics_json":     _clean({"session": result["session"], "cycles": result["cycles"], "initial_phase": result.get("initial_phase", {}), "data_quality": data_quality}),
                        "velocity_profile": _clean(vel.tolist()),
                        "distance_profile": _clean(dist_dec.tolist()),
                        "raw_csv_path":     storage_path,
                        "upload_status":    "complete",
                        "name":             name,
                        "notes":            notes,
                        "stroke_type":      stroke_type,
                        "device_id":        device_id,
                    }
                    insert_resp = sb_admin.table("sessions").insert(session_row).select("id").execute()
                    session_id_saved = insert_resp.data[0]["id"] if insert_resp.data else None
                    if not (session_save_error and "Storage upload" in session_save_error):
                        session_save_error = None  # insert succeeded; clear any storage error
                except Exception as e:
                    session_save_error = str(e)

        return {
            "session_id":         session_id_saved,
            "session":            _clean(result["session"]),
            "cycles":             _clean(result["cycles"]),
            "initial_phase":      _clean(result.get("initial_phase", {})),
            "time":               _clean(t_dec.tolist()),
            "velocity":           _clean(vel.tolist()),
            "distance":           _clean(dist_dec.tolist()),
            "raw_csv_path":       storage_path,
            "athlete_id_received": athlete_id,
            "session_save_error": session_save_error,
            "data_quality":       _clean(data_quality),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if raw_path and os.path.exists(raw_path):
            os.unlink(raw_path)


@app.get("/sessions/{session_id}/export")
async def export_session_csv(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Return a session's 100 Hz signal data as a downloadable CSV.

    Columns: time_s, velocity_ms, distance_m, cycle_id
    cycle_id is 1-based (0 = not inside a detected stroke cycle).
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    # Resolve coach row so we can enforce ownership
    coach_row_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
    except Exception:
        pass

    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    # Fetch session — coach_id filter enforces ownership
    try:
        resp = (
            sb_admin.table("sessions")
            .select("velocity_profile, distance_profile, metrics_json, created_at")
            .eq("id", session_id)
            .eq("coach_id", coach_row_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")

    if not resp.data:
        raise HTTPException(status_code=404, detail="Session not found")

    data      = resp.data
    vel       = data.get("velocity_profile") or []
    dist      = data.get("distance_profile") or []
    mj        = data.get("metrics_json") or {}
    n         = len(vel)

    if n == 0:
        raise HTTPException(status_code=422, detail="Session has no signal data")

    # Build cycle_id array: index → 1-based cycle number (0 = not in any cycle)
    cycles    = mj.get("cycles") or []
    cycle_ids = [0] * n
    for cycle_num, cycle in enumerate(cycles, start=1):
        s = cycle.get("start_idx", 0)
        e = cycle.get("end_idx", 0)
        for i in range(max(0, s), min(e + 1, n)):
            cycle_ids[i] = cycle_num

    # Write CSV into memory
    buf = _io.StringIO()
    w   = _csv.writer(buf)
    w.writerow(["time_s", "velocity_ms", "distance_m", "cycle_id"])
    for i in range(n):
        v = vel[i]
        d = dist[i]
        w.writerow([
            round(i / 100.0, 4),
            round(float(v), 6) if v is not None else "",
            round(float(d), 6) if d is not None else "",
            cycle_ids[i],
        ])

    csv_bytes = buf.getvalue().encode("utf-8")
    date_str  = (data.get("created_at") or "")[:10].replace("-", "")
    filename  = f"session_{date_str}_{session_id[:8]}.csv"

    return StreamingResponse(
        _io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Update mutable session metadata: name, notes, is_starred.
    Only fields present in the request body are updated.
    Coach ownership is enforced via coach_id on the sessions row.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    allowed = {"name", "notes", "is_starred"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    coach_row_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
    except Exception:
        pass

    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    try:
        sb_admin.table("sessions").update(updates).eq("id", session_id).eq("coach_id", coach_row_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True}


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Hard-delete a session and its raw CSV in storage. Coach ownership
    enforced via coach_id. Sessions with null coach_id (legacy) cannot be
    deleted via this endpoint.
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    coach_row_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
    except Exception:
        pass

    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    # Capture the storage path before the row disappears
    raw_csv_path = None
    try:
        path_resp = (
            sb_admin.table("sessions")
            .select("raw_csv_path")
            .eq("id", session_id)
            .eq("coach_id", coach_row_id)
            .single()
            .execute()
        )
        raw_csv_path = path_resp.data.get("raw_csv_path") if path_resp.data else None
    except Exception:
        pass

    try:
        sb_admin.table("sessions").delete().eq("id", session_id).eq("coach_id", coach_row_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if raw_csv_path:
        try:
            sb_admin.storage.from_("raw-csvs").remove([raw_csv_path])
        except Exception:
            pass  # non-fatal — row is gone; orphaned file is the pre-fix status quo

    return {"ok": True}


@app.get("/reports/{token}")
def get_report(token: str):
    """Public (no-auth) parent report payload, looked up by shareable token.

    Parents have no accounts — the token is the only credential, and RLS blocks
    anon reads, so this endpoint assembles the payload with the service role.
    Returns per-session scalar metrics only (no velocity/distance profiles).
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    try:
        report_resp = (
            sb_admin.table("reports")
            .select("athlete_id, config_json, created_at")
            .eq("token", token)
            .single()
            .execute()
        )
        report = report_resp.data
    except Exception:
        report = None
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    config       = report.get("config_json") or {}
    metric_keys  = config.get("metrics") or []
    range_start  = config.get("start")
    range_end    = config.get("end")

    try:
        athlete_resp = (
            sb_admin.table("athletes")
            .select("name, parent_name")
            .eq("id", report["athlete_id"])
            .single()
            .execute()
        )
        athlete = athlete_resp.data or {}
    except Exception:
        athlete = {}

    try:
        q = (
            sb_admin.table("sessions")
            .select("created_at, metrics_json")
            .eq("athlete_id", report["athlete_id"])
        )
        if range_start:
            q = q.gte("created_at", range_start)
        if range_end:
            q = q.lte("created_at", range_end)
        sessions_resp = q.order("created_at", desc=False).execute()
        session_rows = sessions_resp.data or []
    except Exception:
        session_rows = []

    sessions = []
    for row in session_rows:
        session_metrics = (row.get("metrics_json") or {}).get("session")
        if not session_metrics:
            continue
        sessions.append({
            "date":   row.get("created_at"),
            "values": {k: session_metrics.get(k) for k in metric_keys if k in session_metrics},
        })

    return _clean({
        "athlete":  {"name": athlete.get("name"), "parent_name": athlete.get("parent_name")},
        "period":   {"start": range_start, "end": range_end},
        "message":  config.get("message"),
        "metrics":  metric_keys,
        "sessions": sessions,
        "generated_at": report.get("created_at"),
    })


@app.patch("/devices/{chip_id}")
async def rename_device(chip_id: str, request: Request, _auth=Depends(require_auth)):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    coach_row_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
    except Exception:
        pass
    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")
    try:
        sb_admin.table("devices").update({"name": name}).eq("chip_id", chip_id).eq("coach_id", coach_row_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


@app.delete("/devices/{chip_id}")
async def delete_device(chip_id: str, request: Request, _auth=Depends(require_auth)):
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    coach_row_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
    except Exception:
        pass
    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")
    try:
        sb_admin.table("devices").delete().eq("chip_id", chip_id).eq("coach_id", coach_row_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


@app.get("/devices")
async def list_devices(request: Request, _auth=Depends(require_auth)):
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    coach_row_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
    except Exception:
        pass
    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")
    try:
        resp = (
            sb_admin.table("devices")
            .select("chip_id, name, firmware_version, last_seen_at")
            .eq("coach_id", coach_row_id)
            .order("last_seen_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Enrich with session counts — non-fatal if this query fails
    count_map = {}
    try:
        counts_resp = (
            sb_admin.table("sessions")
            .select("device_id")
            .eq("coach_id", coach_row_id)
            .execute()
        )
        for row in counts_resp.data or []:
            did = row.get("device_id")
            if did:
                count_map[did] = count_map.get(did, 0) + 1
    except Exception:
        pass  # session_count defaults to 0 per device
    devices_with_counts = [
        {**d, "session_count": count_map.get(d["chip_id"], 0)}
        for d in (resp.data or [])
    ]
    return {"devices": devices_with_counts}


@app.post("/athletes")
async def create_athlete(request: Request, _auth=Depends(require_auth)):
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    coach = _get_coach_row(sb_admin, request.state.user_id, "id, team_id, athlete_limit")
    if not coach:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    coach_id   = coach["id"]
    team_id    = coach["team_id"]
    limit      = coach.get("athlete_limit")
    if limit is not None:
        try:
            r = (
                sb_admin.table("athletes")
                .select("id", count="exact")
                .eq("coach_id", coach_id)
                .execute()
            )
            count = r.count or 0
        except Exception:
            count = 0
        if count >= limit:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Athlete limit reached ({limit} athletes). "
                    "Upgrade your plan to add more."
                ),
            )

    hw          = body.get("head_waist_m")
    stroke_type = (body.get("stroke_type") or "breaststroke")
    try:
        resp = (
            sb_admin.table("athletes")
            .insert({
                "team_id":      team_id,
                "coach_id":     coach_id,
                "name":         name,
                "stroke_type":  stroke_type,
                "head_waist_m": hw,
            })
            .select("id, name, stroke_type, head_waist_m")
            .single()
            .execute()
        )
        return resp.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Billing ───────────────────────────────────────────────────────────────────

_TIER_LIMITS = {
    "free":       {"athlete_limit": 3,   "device_limit": 1,  "monthly_session_limit": 20},
    "starter":    {"athlete_limit": 20,  "device_limit": 1,  "monthly_session_limit": None},
    "enterprise": {"athlete_limit": 500, "device_limit": 10, "monthly_session_limit": None},
}


def _get_coach_row(sb_admin, user_id: str, fields: str = "id"):
    try:
        resp = (
            sb_admin.table("coaches")
            .select(fields)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return resp.data
    except Exception:
        return None


_SIMPLE_PREAMBLE = """\
You are a friendly swim coach giving feedback to a swimmer who doesn't know technical terms.
Use plain, encouraging language. Focus on 1-2 concrete things they can work on next.
Avoid jargon: say 'stroke rate' not 'SPM', 'how far each stroke takes you' not 'DPS',
'glide' not 'coast fraction', 'arm power' not 'arm-peak velocity or CV'.
Keep your answer short — 3 to 5 sentences maximum.
"""

# Max model<->tool round-trips per chat turn. Bounds latency/cost and guarantees termination.
MAX_TOOL_ITERS = 5
# Session-level metric keys returned in the list_athlete_sessions summary (compact, no raw cycles).
_SESSION_SUMMARY_KEYS = ["mean_vel_ms", "mean_dps_m", "stroke_rate_spm", "fatigue_index_pct", "cv_isi"]


@app.post("/coach/chat")
async def coach_chat(request: Request, _auth=Depends(require_auth)):
    """AI coaching chat for one saved session.

    Body: {session_id, messages:[{role,content}...], simple?}
    The Anthropic key is server-side only. The prompt is rebuilt here from the stored
    session's metrics_json — the client never supplies the metrics, and no athlete PII
    enters the prompt. Coach ownership is enforced BEFORE any model call.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="Coaching not configured")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    session_id = body.get("session_id")
    messages   = body.get("messages")
    simple     = bool(body.get("simple"))

    if not session_id or not isinstance(session_id, str):
        raise HTTPException(status_code=400, detail="session_id is required")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") not in ("user", "assistant") \
                or not isinstance(msg.get("content"), str):
            raise HTTPException(status_code=400, detail="Each message needs role (user|assistant) and string content")
    if messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    coach_row_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
    except Exception:
        pass
    if not coach_row_id:
        raise HTTPException(status_code=403, detail="No coach profile found")

    try:
        session_resp = (
            sb_admin.table("sessions")
            .select("metrics_json, stroke_type, coach_id, athlete_id")
            .eq("id", session_id)
            .single()
            .execute()
        )
        row = session_resp.data
    except Exception:
        row = None
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.get("coach_id") != coach_row_id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")

    stroke     = row.get("stroke_type") or "breaststroke"
    athlete_id = row.get("athlete_id")
    metrics    = row.get("metrics_json") or {}
    session    = metrics.get("session", {}) or {}
    cycles     = metrics.get("cycles", []) or []

    def _attach_t_peak(cyc):
        # peak_idx is an index into the 100 Hz grid; t_peak_s lets the per-cycle table render.
        for c in cyc:
            idx = c.get("peak_idx")
            if isinstance(idx, (int, float)) and idx is not None:
                c["t_peak_s"] = float(idx) / 100.0
        return cyc

    data_block = coach._build_user_message(stroke, session, _attach_t_peak(cycles))
    if simple:
        system = (_SIMPLE_PREAMBLE + "\n" + coach._TOOLS_HINT + "\n" + coach._TEAM_HINT + "\n"
                  + coach._GUARDRAILS + "\n\nSESSION DATA:\n" + data_block)
    else:
        system = coach._build_system_prompt(stroke) + "\n\nSESSION DATA:\n" + data_block

    # ── Tool executors — ALWAYS scoped to the anchor session's athlete AND the owning coach.
    # The model may *request* a tool; the server decides whether to honor it. A session_id the
    # model supplies is re-validated against coach_id + athlete_id — never trusted as given.
    def _exec_list_athlete_sessions(args):
        if not athlete_id:
            return {"error": "No athlete is linked to this session, so history is unavailable."}
        try:
            limit = int(args.get("limit") or 10)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 25))
        q = (sb_admin.table("sessions")
             .select("id, created_at, name, stroke_type, metrics_json")
             .eq("coach_id", coach_row_id)
             .eq("athlete_id", athlete_id)
             .order("created_at", desc=True)
             .limit(limit))
        stroke_filter = args.get("stroke")
        if stroke_filter:
            q = q.eq("stroke_type", stroke_filter)
        try:
            rows = q.execute().data or []
        except Exception:
            return {"error": "Could not load sessions."}
        out = []
        for r in rows:
            sess = (r.get("metrics_json") or {}).get("session", {}) or {}
            out.append({
                "session_id": r.get("id"),
                "date": (r.get("created_at") or "")[:10],
                "name": r.get("name"),
                "stroke": r.get("stroke_type"),
                **{k: sess.get(k) for k in _SESSION_SUMMARY_KEYS},
            })
        return {"sessions": out, "count": len(out)}

    def _exec_get_session_metrics(args):
        sid = args.get("session_id")
        if not sid or not isinstance(sid, str):
            return {"error": "session_id is required."}
        if not athlete_id:
            return {"error": "No athlete is linked to this session."}
        try:
            r = (sb_admin.table("sessions")
                 .select("metrics_json, stroke_type")
                 .eq("id", sid)
                 .eq("coach_id", coach_row_id)
                 .eq("athlete_id", athlete_id)
                 .single()
                 .execute()).data
        except Exception:
            r = None
        if not r:
            return {"error": "That session is not available for this athlete."}
        mj = r.get("metrics_json") or {}
        return {"data": coach._build_user_message(
            r.get("stroke_type") or "breaststroke",
            mj.get("session", {}) or {},
            _attach_t_peak(mj.get("cycles", []) or []),
        )}

    # ── Team executors — scoped to the coach's whole roster (coach_id), NOT one athlete.
    # One athletes query + one sessions query per turn, cached for the request; aggregation
    # is pure (roster_metrics) so the model only ever sees compact tables, never raw cycles.
    _roster_cache = {}

    def _load_roster_rows():
        if "rows" in _roster_cache:
            return _roster_cache["rows"]
        try:
            arows = (sb_admin.table("athletes").select("id, name")
                     .eq("coach_id", coach_row_id).execute()).data or []
        except Exception:
            arows = []
        names = {a.get("id"): a.get("name") for a in arows}
        try:
            srows = (sb_admin.table("sessions")
                     .select("athlete_id, created_at, metrics_json")
                     .eq("coach_id", coach_row_id)
                     .order("created_at", desc=True)
                     .execute()).data or []
        except Exception:
            srows = []
        rows = []
        for s in srows:
            aid = s.get("athlete_id")
            if aid not in names:          # defense in depth: only this coach's roster
                continue
            rows.append({
                "athlete_id": aid,
                "athlete_name": names.get(aid),
                "date": (s.get("created_at") or "")[:10],
                "session": (s.get("metrics_json") or {}).get("session", {}) or {},
            })
        _roster_cache["rows"] = rows
        return rows

    def _exec_rank_athletes(args):
        metric = args.get("metric")
        if not metric:
            return {"error": "metric is required."}
        ascending = bool(args.get("ascending", True))
        try:
            limit = int(args["limit"]) if args.get("limit") is not None else None
        except (TypeError, ValueError):
            limit = None
        ranking = roster_metrics.rank_athletes(
            roster_metrics.latest_per_athlete(_load_roster_rows()),
            metric, ascending=ascending, limit=limit)
        return {"metric": metric, "ascending": ascending, "ranking": ranking, "athletes": len(ranking)}

    def _exec_rank_progress(args):
        metric = args.get("metric")
        if not metric:
            return {"error": "metric is required."}
        try:
            min_sessions = int(args.get("min_sessions") or 2)
        except (TypeError, ValueError):
            min_sessions = 2
        return {"metric": metric,
                **roster_metrics.rank_progress(_load_roster_rows(), metric, min_sessions=min_sessions)}

    def _exec_team_summary(args):
        return roster_metrics.team_summary(_load_roster_rows(), _SESSION_SUMMARY_KEYS)

    _EXECUTORS = {
        "list_athlete_sessions": _exec_list_athlete_sessions,
        "get_session_metrics": _exec_get_session_metrics,
        "rank_athletes": _exec_rank_athletes,
        "rank_progress": _exec_rank_progress,
        "team_summary": _exec_team_summary,
    }

    # Structured tool results surfaced to the client alongside the prose reply, so a future
    # "show the data" / compare deep-link panel is front-end-only (no backend rework).
    used_data = []
    try:
        client = anthropic.Anthropic()
        convo = list(messages)
        reply = ""
        for _ in range(MAX_TOOL_ITERS):
            resp = client.messages.create(
                model=coach.MODEL,
                max_tokens=2048,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                tools=coach.COACH_TOOLS + coach.TEAM_TOOLS,
                messages=convo,
            )
            if getattr(resp, "stop_reason", None) != "tool_use":
                reply = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
                break
            # Model asked for tool(s): run each, feed results back, loop.
            convo.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for blk in resp.content:
                if getattr(blk, "type", None) != "tool_use":
                    continue
                executor = _EXECUTORS.get(blk.name)
                result = executor(blk.input or {}) if executor else {"error": f"Unknown tool: {blk.name}"}
                used_data.append({"tool": blk.name, "input": blk.input or {}, "result": result})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": blk.id,
                    "content": json.dumps(result),
                })
            convo.append({"role": "user", "content": tool_results})
        else:
            reply = reply or "I couldn't finish analyzing that — try asking something more specific."
    except anthropic.APIStatusError as e:
        if e.status_code == 529 or "overloaded" in str(e).lower():
            raise HTTPException(status_code=503, detail="The coaching service is busy — try again in a few seconds.")
        raise HTTPException(status_code=502, detail=f"Coaching service error ({e.status_code}).")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Connection error reaching the coaching service — try again.")

    return {"reply": reply, "data": used_data}


@app.post("/billing/checkout-session")
async def create_checkout_session(request: Request, _auth=Depends(require_auth)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Billing not configured")
    _stripe.api_key = STRIPE_SECRET_KEY
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    tier = body.get("tier", "")
    if tier == "starter":
        price_id = STRIPE_STARTER_PRICE_ID
    elif tier == "enterprise":
        price_id = STRIPE_ENTERPRISE_PRICE_ID
    else:
        raise HTTPException(status_code=400, detail="tier must be 'starter' or 'enterprise'")
    if not price_id:
        raise HTTPException(status_code=503, detail="Price not configured for that tier")

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    coach = _get_coach_row(sb_admin, request.state.user_id, "id, stripe_customer_id")
    if not coach:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    stripe_customer_id = coach.get("stripe_customer_id")
    if not stripe_customer_id:
        customer = _stripe.Customer.create(metadata={"coach_id": str(coach["id"])})
        stripe_customer_id = customer.id
        sb_admin.table("coaches").update({"stripe_customer_id": stripe_customer_id}).eq("id", coach["id"]).execute()

    session = _stripe.checkout.Session.create(
        customer=stripe_customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="https://swimnetics-api-production.up.railway.app/billing/complete",
        cancel_url="https://swimnetics-api-production.up.railway.app/billing/complete",
    )
    return {"url": session.url}


@app.post("/billing/portal-session")
async def create_portal_session(request: Request, _auth=Depends(require_auth)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Billing not configured")
    _stripe.api_key = STRIPE_SECRET_KEY
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    coach = _get_coach_row(sb_admin, request.state.user_id, "stripe_customer_id")
    if not coach or not coach.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No billing account found. Subscribe first.")
    session = _stripe.billing_portal.Session.create(
        customer=coach["stripe_customer_id"],
        return_url="https://swimnetics-api-production.up.railway.app/billing/complete",
    )
    return {"url": session.url}


@app.get("/billing/complete")
def billing_complete():
    from fastapi.responses import HTMLResponse
    return HTMLResponse("<h2>Payment processed. Return to the Swimnetics app.</h2>")


@app.post("/billing/webhook")
async def billing_webhook(request: Request):
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Billing not configured")
    _stripe.api_key = STRIPE_SECRET_KEY
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = _stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except _stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        return {"received": True}

    event_type = event["type"]
    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        status = sub["status"]
        price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else ""
        if price_id == STRIPE_STARTER_PRICE_ID:
            tier = "starter"
        elif price_id == STRIPE_ENTERPRISE_PRICE_ID:
            tier = "enterprise"
        else:
            tier = "free"
        limits = _TIER_LIMITS[tier]
        try:
            sb_admin.table("coaches").update({
                "subscription_tier": tier,
                "subscription_status": status,
                **limits,
            }).eq("stripe_customer_id", customer_id).execute()
        except Exception:
            pass

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        limits = _TIER_LIMITS["free"]
        try:
            sb_admin.table("coaches").update({
                "subscription_tier": "free",
                "subscription_status": "active",
                **limits,
            }).eq("stripe_customer_id", customer_id).execute()
        except Exception:
            pass

    return {"received": True}


@app.get("/billing/status")
async def billing_status(request: Request, _auth=Depends(require_auth)):
    import datetime
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    coach = _get_coach_row(
        sb_admin, request.state.user_id,
        "id, subscription_tier, subscription_status, athlete_limit, device_limit, monthly_session_limit"
    )
    if not coach:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    coach_id = coach["id"]
    now = datetime.datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    athlete_count, device_count, session_count = 0, 0, 0
    try:
        r = sb_admin.table("athletes").select("id", count="exact").eq("coach_id", coach_id).execute()
        athlete_count = r.count or 0
    except Exception:
        pass
    try:
        r = sb_admin.table("devices").select("chip_id", count="exact").eq("coach_id", coach_id).execute()
        device_count = r.count or 0
    except Exception:
        pass
    try:
        r = sb_admin.table("sessions").select("id", count="exact").eq("coach_id", coach_id).gte("created_at", month_start).execute()
        session_count = r.count or 0
    except Exception:
        pass

    return {
        "tier":                    coach["subscription_tier"],
        "subscription_status":     coach["subscription_status"],
        "athlete_limit":           coach["athlete_limit"],
        "device_limit":            coach["device_limit"],
        "monthly_session_limit":   coach["monthly_session_limit"],
        "athlete_count":           athlete_count,
        "device_count":            device_count,
        "session_count_this_month": session_count,
    }
