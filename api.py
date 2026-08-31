import csv as _csv
import datetime
import io as _io
import json
import math
import os
import tempfile
import time
import uuid
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

# Master switch for ALL tier enforcement — monthly session limit + device limit (/process) and
# athlete limit (POST /athletes). DEFAULT OFF (Phase 54): billing isn't being sold yet, and the
# free-tier caps were blocking real testing. When off the limit-counting queries are skipped
# entirely, not merely made to pass — that keeps them off the upload path and avoids running the
# athlete count against the phantom `athletes.coach_id` column.
# The billing infrastructure is deliberately intact: _TIER_LIMITS, the Stripe webhook writes, and
# GET /billing/status all still work. Re-enable with ENFORCE_TIER_LIMITS=1; the per-coach
# NULL-means-unlimited semantics are nested inside and survive.
ENFORCE_TIER_LIMITS = os.getenv("ENFORCE_TIER_LIMITS", "0").strip().lower() in ("1", "true", "yes")

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
import annotations as annot
import phase_metrics as pm
import coach
import roster_metrics
import drills
import ratings
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


def _session_fs(row) -> float:
    """The session's true sample rate, falling back to annot.FS_HZ (100).

    NULL means the row predates Phase 52 and has no recorded rate — 100 reproduces
    exactly what those sessions did before, so nothing shifts under un-backfilled data.
    Any query feeding this MUST select sample_rate_hz; a missing column looks identical
    to a NULL here and would silently keep the old wrong behavior.
    """
    v = (row or {}).get("sample_rate_hz")
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float(annot.FS_HZ)
    return f if f > 0 and not (math.isnan(f) or math.isinf(f)) else float(annot.FS_HZ)


# Session-clock sanity window (Phase 86-01). A value outside this window is not a clock
# reading, it is a unit error on the client — and the two realistic ones land nowhere near
# a real "now": seconds-instead-of-milliseconds lands in 1970, microseconds-instead-of-
# milliseconds lands tens of thousands of years out. Both are caught by a window this wide,
# so the check costs nothing in false rejections even against a badly skewed phone clock.
_EPOCH_MS_FLOOR           = 1577836800000     # 2020-01-01T00:00:00Z — predates the hardware
_EPOCH_MS_FUTURE_SLACK_MS = 48 * 3600 * 1000  # tolerate a phone clock up to 2 days fast


def _valid_session_start_ms(v) -> bool:
    """True when v is plausibly an absolute epoch-ms instant. See _EPOCH_MS_FLOOR."""
    try:
        ms = int(v)
    except (TypeError, ValueError):
        return False
    if ms <= 0:
        return False
    return _EPOCH_MS_FLOOR <= ms <= int(time.time() * 1000) + _EPOCH_MS_FUTURE_SLACK_MS


def _finite_or_none(v):
    """Coerce a clock diagnostic to float, dropping NaN/inf (they break JSON on insert)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/time")
def server_time():
    """Server UTC in epoch milliseconds.

    UNAUTHENTICATED ON PURPOSE (Phase 86-01) — this is a correctness requirement, not an
    auth oversight, so do NOT add Depends(require_auth). The client calls this to measure
    its own round-trip time and derives its clock offset from RTT/2; require_auth calls
    sb.auth.get_user(), a network round trip to Supabase on every request, which would land
    *inside* the interval being measured and corrupt the very number this exists to produce.

    For the same reason the handler stays free of ALL I/O: no Supabase client, no DB read,
    no logging call that could touch the network. It discloses only the current time.
    """
    return {"server_utc_ms": int(time.time() * 1000)}


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
    recording_token: Optional[str] = Form(None),
    go_signal_s: Optional[float] = Form(None),
    session_start_utc_ms: Optional[int] = Form(None),
    sync_error_ms: Optional[float] = Form(None),
    clock_offset_ms: Optional[float] = Form(None),
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
        # actual_fs is the TRUE rate of the arrays below — decimation is by an integer
        # factor, so the requested 100.0 is never actually achieved (~89.5 Hz typical).
        # It is stored on the session row; every consumer must read it, not assume 100.
        t_dec, dist_dec, vel, accel, actual_fs = vae.run_pipeline(df, 100.0, stroke_type)

        # ── Metrics ──────────────────────────────────────────────────────
        result = m.compute_session_metrics(
            t_dec, vel, dist_dec, head_waist_m=head_waist_m, stroke_type=stroke_type
        )

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

        # ── Race-phase metrics (Phase 75-01 skeleton, 75-02 underwater window) ─
        # go_signal_s arrives as an optional form field from the app's coach "GO" marker
        # (Phase 84-02) and is ALREADY on the session clock — the app converts its raw
        # press time against the META correlation it has computed since Phase 47. It is
        # None whenever the coach did not press GO, or when the session was recorded with
        # the device's own button and pulled in via "Retrieve from Device", where no press
        # exists. A bad marker is dropped below rather than 422'd: the request carries the
        # swim, which is irreplaceable, and the marker is not.
        # annotation_phases is None by construction — a session
        # being processed for the first time cannot already carry a coach annotation, so
        # every boundary here resolves from the seed or from a detector. For the same
        # reason the cycles handed over are ALWAYS the auto segmenter's, and
        # segmentation_reliable is whatever metrics.py decided (False on this path), which
        # is what marks the per-cycle metrics provisional (75-06).
        _go = go_signal_s
        if _go is not None and (not math.isfinite(_go) or _go < 0):
            # A bad marker must not cost the coach the swim — drop it and process anyway.
            print(f"/process: discarding invalid go_signal_s={_go!r}")
            _go = None
        phases = pm.compute_phases(pm.PhaseContext(
            t=t_dec, vel=vel, dist=dist_dec, accel=accel, fs=actual_fs,
            stroke_type=stroke_type, go_signal_s=_go,
            annotation_phases=None,
            seed_phases=annot.build_seed(result, actual_fs)["phases"],
            initial_phase=result.get("initial_phase"),
            cycles=result.get("cycles"),
            segmentation_reliable=bool(
                result["session"].get("segmentation_reliable", False)
            ),
        ))

        # ── Session clock (Phase 86-01) ───────────────────────────────────
        # session_start_utc_ms is the phone's measured UTC instant of encoder sample #0;
        # sync_error_ms and clock_offset_ms are the two diagnostics behind it (measured BLE
        # flight time, measured offset from server UTC). The diagnostics are NOT corrections
        # — the correction is already baked into the start — so they are independently
        # nullable and neither gates the other, nor does either gate on the start being valid.
        # A rejected start with a recorded offset is exactly the forensic case they exist for.
        #
        # All three are None on every app build before 86-02, and NULL is PERMANENT for the
        # sessions that predate it: only the phone can produce this, at record time. A reader
        # must treat NULL as "unknown" and must never substitute recorded_at, which is UPLOAD
        # time, not swim time.
        #
        # Same drop-don't-422 posture as go_signal_s above, for the same reason: this request
        # carries the swim, so a malformed clock annotation costs the annotation, never the
        # session. (PUT /go-signal 422s precisely because nothing is at stake there.)
        _start_ms = session_start_utc_ms
        if _start_ms is not None and not _valid_session_start_ms(_start_ms):
            print(f"/process: discarding implausible session_start_utc_ms={_start_ms!r}")
            _start_ms = None
        _sync_err  = _finite_or_none(sync_error_ms)
        _clock_off = _finite_or_none(clock_offset_ms)

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

                if coach and ENFORCE_TIER_LIMITS:
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
                        "metrics_json":     _clean({"session": result["session"], "cycles": result["cycles"], "initial_phase": result.get("initial_phase", {}), "data_quality": data_quality, "phases": phases}),
                        "velocity_profile":     _clean(vel.tolist()),
                        "distance_profile":     _clean(dist_dec.tolist()),
                        "acceleration_profile": _clean(accel.tolist()),  # Phase 64-02
                        "sample_rate_hz":       float(actual_fs),
                        "raw_csv_path":     storage_path,
                        "upload_status":    "complete",
                        "name":             name,
                        "notes":            notes,
                        "stroke_type":      stroke_type,
                        "device_id":        device_id,
                    }
                    # QR slate (Phase 70): store the phone's recording token ONLY when sent, so the
                    # insert stays valid on a DB that has not yet had patch_13 applied.
                    if recording_token:
                        session_row["recording_token"] = recording_token
                    # Session clock (Phase 86-01): each key is added ONLY when a value
                    # survived validation, for the same reason recording_token is
                    # conditional above — the insert must stay valid on a DB that has not
                    # yet had patch_14 applied, and existing app builds send nothing.
                    # An absent key and an explicit NULL are indistinguishable in the stored
                    # row (all three columns are nullable with no default), so the "store
                    # NULL when absent" contract is met either way and nothing is lost.
                    if _start_ms is not None:
                        session_row["session_start_utc_ms"] = int(_start_ms)
                    if _sync_err is not None:
                        session_row["sync_error_ms"] = _sync_err
                    if _clock_off is not None:
                        session_row["clock_offset_ms"] = _clock_off
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
            "phases":             _clean(phases),
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
            .select("velocity_profile, distance_profile, metrics_json, created_at, sample_rate_hz")
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
    fs        = _session_fs(data)

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
            round(i / fs, 4),
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


@app.get("/sessions/{session_id}/ratings")
async def session_ratings(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Return the coach-friendly pillar ratings (good/ok/needs-work + 0–100 score + trend) for an
    owned session. Trend baseline = the athlete's previous session of the same stroke
    (ratings.select_baseline mode="previous"). All logic lives in ratings.py (shared with the
    clients + chat); this handler only loads data and enforces auth + ownership.
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    # No row → 403; a real query/DB failure propagates as 5xx (not masked as 403).
    coach_resp = (
        sb_admin.table("coaches")
        .select("id")
        .eq("user_id", request.state.user_id)
        .limit(1)
        .execute()
    )
    coach_row_id = coach_resp.data[0]["id"] if coach_resp.data else None
    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    # coach_id filter enforces ownership — a foreign/unknown session returns no row (404),
    # while a genuine query/DB failure propagates as 5xx rather than being masked as 404.
    resp = (
        sb_admin.table("sessions")
        .select("metrics_json, stroke_type, athlete_id, created_at")
        .eq("id", session_id)
        .eq("coach_id", coach_row_id)
        .limit(1)
        .execute()
    )
    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    stroke     = row.get("stroke_type") or "breaststroke"
    athlete_id = row.get("athlete_id")
    created_at = row.get("created_at")
    mj         = row.get("metrics_json") or {}
    # Flatten session metrics + data-quality flags so ratings sees segmentation_reliable.
    metrics = {**(mj.get("session") or {}), **(mj.get("data_quality") or {})}

    # Baseline = this athlete's earlier same-stroke sessions, newest-first, before this one.
    # No try/except: an empty result is the legitimate "no prior session" case (handled by
    # select_baseline → None), so a raised error here is a real failure and should surface as 5xx
    # rather than silently degrading the trend to "first_session".
    prior = []
    if athlete_id and created_at:
        prior_resp = (
            sb_admin.table("sessions")
            .select("metrics_json, created_at")
            .eq("coach_id", coach_row_id)
            .eq("athlete_id", athlete_id)
            .eq("stroke_type", stroke)
            .lt("created_at", created_at)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for r in (prior_resp.data or []):
            pmj = r.get("metrics_json") or {}
            prior.append({**(pmj.get("session") or {}), **(pmj.get("data_quality") or {})})

    baseline = ratings.select_baseline(prior, mode="previous")
    return ratings.rate_session(metrics, baseline, stroke)


@app.get("/team/overview")
async def team_overview(request: Request, _auth=Depends(require_auth)):
    """Team-level coach dashboard payload: each athlete's latest-session pillar verdicts, a team
    band distribution, a needs-attention list, a recent-activity feed, and counts. All rating
    logic is reused from ratings.py (the same path as /sessions/{id}/ratings) — this handler only
    loads data, enforces auth + coach scope, and rolls it up. Contract: 37-01-PLAN DESIGN SPEC.
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    # No row → 403; a real query/DB failure propagates as 5xx (not masked).
    coach_resp = (
        sb_admin.table("coaches")
        .select("id, team_id")
        .eq("user_id", request.state.user_id)
        .limit(1)
        .execute()
    )
    coach_row = coach_resp.data[0] if coach_resp.data else None
    if not coach_row:
        raise HTTPException(status_code=403, detail="Coach profile not found")
    coach_row_id = coach_row["id"]
    team_id = coach_row.get("team_id")

    # Roster is scoped by team_id (the live athletes table has no coach_id column — scoping that
    # the web gets from RLS; the service-role client must filter explicitly). Sessions stay on
    # coach_id (that column exists). A query failure propagates as 5xx, not an empty roster.
    athletes_rows = (
        sb_admin.table("athletes")
        .select("id, name, stroke_type")
        .eq("team_id", team_id)
        .execute()
    ).data or []
    sessions_rows = (
        sb_admin.table("sessions")
        .select("id, athlete_id, stroke_type, created_at, metrics_json")
        .eq("coach_id", coach_row_id)
        .order("created_at", desc=True)
        .execute()
    ).data or []

    # Group sessions by athlete (already newest-first); drop any not in this coach's roster.
    roster = {a["id"]: a for a in athletes_rows}
    by_athlete = {}
    for s in sessions_rows:
        aid = s.get("athlete_id")
        if aid in roster:
            by_athlete.setdefault(aid, []).append(s)

    def _flat(mj):
        mj = mj or {}
        return {**(mj.get("session") or {}), **(mj.get("data_quality") or {})}

    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    athlete_summaries = []
    tested_this_week = 0
    for a in athletes_rows:
        sess = by_athlete.get(a["id"], [])
        if not sess:
            athlete_summaries.append({
                "athlete_id": a["id"], "name": a.get("name"),
                "stroke_type": a.get("stroke_type"),
                "last_tested": None, "last_session_id": None, "pillars": [],
            })
            continue
        latest = sess[0]
        stroke = latest.get("stroke_type") or a.get("stroke_type") or "breaststroke"
        metrics = _flat(latest.get("metrics_json"))
        # Baseline = this athlete's earlier same-stroke sessions, before latest, newest-first.
        prior = [
            _flat(s.get("metrics_json")) for s in sess[1:]
            if (s.get("stroke_type") or a.get("stroke_type") or "breaststroke") == stroke
        ]
        baseline = ratings.select_baseline(prior, mode="previous")
        rated = ratings.rate_session(metrics, baseline, stroke)
        pillars = [
            {"key": p["key"], "label": p["label"], "band": p["band"],
             "trend": p["trend"], "score": p["score"], "provisional": p["provisional"]}
            for p in rated["pillars"]
        ]
        last_tested = (latest.get("created_at") or "")[:10]
        try:
            if last_tested and datetime.date.fromisoformat(last_tested) >= week_ago:
                tested_this_week += 1
        except ValueError:
            pass  # malformed created_at → skip the week count for this row, keep the rest

        athlete_summaries.append({
            "athlete_id": a["id"], "name": a.get("name"), "stroke_type": stroke,
            "last_tested": last_tested or None, "last_session_id": latest.get("id"),
            "pillars": pillars,
        })

    # Recent feed: newest sessions team-wide (cap 10), no per-session rating (keeps compute
    # O(athletes), not O(sessions); the web links each row to its full report card).
    recent = [
        {"athlete_id": s.get("athlete_id"),
         "name": roster.get(s.get("athlete_id"), {}).get("name"),
         "session_id": s.get("id"), "date": (s.get("created_at") or "")[:10],
         "stroke_type": s.get("stroke_type")}
        for s in sessions_rows if s.get("athlete_id") in roster
    ][:10]

    rollup = ratings.summarize_team(athlete_summaries, today)
    return {
        "athlete_count": len(athletes_rows),
        "tested_this_week": tested_this_week,
        "pillars": rollup["pillars"],
        "athletes": athlete_summaries,
        "recent": recent,
        "needs_attention": rollup["needs_attention"],
        "rating_colors": dict(ratings.RATING_COLORS),
    }


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
    """Hard-delete a session and its raw CSV + video(s) in storage. Coach ownership
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

    # Capture storage paths before the row disappears
    raw_csv_path = None
    video_path = None
    try:
        path_resp = (
            sb_admin.table("sessions")
            .select("raw_csv_path, video_path")
            .eq("id", session_id)
            .eq("coach_id", coach_row_id)
            .single()
            .execute()
        )
        if path_resp.data:
            raw_csv_path = path_resp.data.get("raw_csv_path")
            video_path = path_resp.data.get("video_path")
    except Exception:
        pass

    # session_videos rows cascade-delete with the session (ON DELETE CASCADE), which erases the
    # only record of their storage_path — so this must be read before the sessions delete fires.
    external_video_paths = []
    try:
        sv_resp = (
            sb_admin.table("session_videos")
            .select("storage_path")
            .eq("session_id", session_id)
            .execute()
        )
        external_video_paths = [row["storage_path"] for row in (sv_resp.data or []) if row.get("storage_path")]
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

    video_paths_to_remove = ([video_path] if video_path else []) + external_video_paths
    if video_paths_to_remove:
        try:
            sb_admin.storage.from_("videos").remove(video_paths_to_remove)
        except Exception:
            pass  # non-fatal — row is gone; orphaned file is the pre-fix status quo

    return {"ok": True}


# ── Trial annotations (Phase 47) ───────────────────────────────────────────────
# Contract shared by the web annotation GUI (47-02), iOS video upload (47-03), and
# metric recompute (47-04). Doc shape + validation live in annotations.py.

def _owned_session(sb_admin, user_id: str, session_id: str, fields: str):
    """Auth + ownership lookup shared by the annotation/video endpoints.
    Returns the session row. 403 = no coach profile, 404 = foreign/unknown session
    (matching /sessions/{id}/ratings); genuine DB failures propagate as 5xx.
    """
    coach_resp = (
        sb_admin.table("coaches")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    coach_row_id = coach_resp.data[0]["id"] if coach_resp.data else None
    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    resp = (
        sb_admin.table("sessions")
        .select(fields)
        .eq("id", session_id)
        .eq("coach_id", coach_row_id)
        .limit(1)
        .execute()
    )
    row = resp.data[0] if resp.data else None
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return coach_row_id, row


@app.get("/sessions/{session_id}/annotations")
async def get_annotations(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Saved annotation (or null) + an auto-seeded draft from the stored metrics_json,
    plus the video attachment info. Works for velocity-only sessions (video: null).
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    _, row = _owned_session(
        sb_admin, request.state.user_id, session_id,
        "metrics_json, velocity_profile, video_path, video_origin_s, sample_rate_hz, "
        "stroke_type",
    )

    ann_resp = (
        sb_admin.table("session_annotations")
        .select("phases, stroke_marks_s, source, updated_at")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    annotation = ann_resp.data[0] if ann_resp.data else None

    vel = row.get("velocity_profile") or []
    video_path = row.get("video_path")
    fs = _session_fs(row)
    return {
        "annotation": annotation,
        "seed": _clean(annot.build_seed(row.get("metrics_json"), fs)),
        "video": (
            {"path": video_path, "origin_s": row.get("video_origin_s")}
            if video_path else None
        ),
        "duration_s": len(vel) / fs,
        "sample_rate_hz": fs,
        # Arm entries per cycle for this stroke (Phase 57). Published so the web reads
        # the pairing rule from the contract instead of keeping its own copy in JS.
        "marks_per_cycle": annot.marks_per_cycle(row.get("stroke_type")),
    }


@app.put("/sessions/{session_id}/annotations")
async def put_annotations(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Upsert the session's annotation (one row per session, last write wins), then
    RECOMPUTE the session metrics from the human boundaries (Phase 47-04, auto on save):
    metrics_json is overwritten (original auto result backed up once in metrics_json_auto)
    when the annotation yields >=1 cycle. Recompute failure never loses the annotation —
    it is reported as recompute_error. 422 with an errors list on bad docs."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    coach_row_id, row = _owned_session(
        sb_admin, request.state.user_id, session_id,
        # acceleration_profile is here for the phases rebuild below, not the recompute:
        # _rebuild_phases tolerates a missing one as "pre-Phase-64 session", so omitting it
        # would silently null out max_accel / accel_asymmetry / jerk_smoothness on every
        # annotated session rather than failing loudly.
        "velocity_profile, distance_profile, acceleration_profile, metrics_json, "
        "metrics_json_auto, sample_rate_hz, stroke_type",
    )

    vel_list = row.get("velocity_profile") or []
    fs = _session_fs(row)
    duration_s = len(vel_list) / fs
    errors = annot.validate_annotation(body, duration_s or None)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    phases = {k: annot._num(body.get("phases", {}).get(k)) for k in annot.PHASE_KEYS}
    record = {
        "session_id":     session_id,
        "phases":         phases,
        "stroke_marks_s": [float(v) for v in body.get("stroke_marks_s", [])],
        "source":         body.get("source", "manual"),
        "updated_by":     coach_row_id,
        "updated_at":     "now()",
    }
    try:
        sb_admin.table("session_annotations").upsert(
            record, on_conflict="session_id"
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ── recompute from the human boundaries (on the stored profiles, at their own rate) ──
    recomputed = False
    recompute_error = None
    # stroke_type decides how many marks make a cycle (Phase 57) — free/back pair, the
    # rest are 1:1. A missing or unknown value degrades to 1, the pre-Phase-57 behavior.
    manual = annot.annotation_to_overrides(
        record, len(vel_list), fs, row.get("stroke_type")
    )
    if manual.get("cycle_bounds"):
        try:
            vel_arr  = np.asarray(vel_list, dtype=float)
            dist_arr = np.asarray(row.get("distance_profile") or [], dtype=float)
            if dist_arr.size != vel_arr.size or vel_arr.size < 2:
                raise ValueError("velocity/distance profiles missing or mismatched")
            t_arr  = np.arange(vel_arr.size) / fs
            result = m.compute_session_metrics(t_arr, vel_arr, dist_arr, manual=manual)

            old_mj = row.get("metrics_json") or {}
            old_dq = old_mj.get("data_quality") or {}
            # Carry non-recomputable quality fields (dropout/warnings come from the raw
            # CSV); refresh the cycle-derived counts; mark provenance.
            new_dq = {**old_dq}
            for k in ("total_cycles_raw", "outlier_cycle_count", "implausible_cycle_count"):
                if k in result["session"]:
                    new_dq[k] = result["session"][k]
            new_dq["segmentation_reliable"] = True
            new_dq["recomputed_from_annotation"] = True

            # MERGE onto old_mj rather than replacing it (Phase 75-06). Building a fresh
            # dict here silently dropped `phases` and `go_signal_s`, so annotating a session
            # — the one action that produces the BEST data for it — wiped its entire
            # race-phase metric object until someone re-ran tools/backfill_phases.py.
            new_mj = _clean({
                **old_mj,
                "session":       result["session"],
                "cycles":        result["cycles"],
                # dive/pulldown detection unchanged by recompute — carry the original
                "initial_phase": old_mj.get("initial_phase") or result.get("initial_phase", {}),
                "data_quality":  new_dq,
            })
            updates = {"metrics_json": new_mj}
            if row.get("metrics_json_auto") is None and old_mj:
                updates["metrics_json_auto"] = old_mj  # once-only backup of the auto result
            sb_admin.table("sessions").update(updates).eq("id", session_id).execute()
            recomputed = True
        except Exception as e:
            recompute_error = str(e)  # annotation saved; metrics untouched

    # ── refresh metrics_json.phases off the annotation just saved (Phase 75-06) ──
    # Runs whether or not the cycle recompute above fired: even a phases-only annotation
    # (boundaries marked, too few stroke marks to form cycles) must re-resolve the four
    # boundaries as "manual". _rebuild_phases re-reads session_annotations itself, and reads
    # cycles off the row's metrics_json — which now holds the coach's cycles when the
    # recompute ran, so the per-cycle metrics pick them up and drop their provisional flag.
    # Its own write is the last one to land, so it must see the merged metrics_json.
    phases_error = None
    try:
        _rebuild_phases(
            sb_admin, session_id,
            {**row, "metrics_json": new_mj if recomputed else (row.get("metrics_json") or {})},
        )
    except Exception as e:
        # Never fail an annotation save over its phase metrics — same contract as the
        # recompute above. The backfill tool can always re-derive them.
        phases_error = str(e)

    resp = {
        "phases":         record["phases"],
        "stroke_marks_s": record["stroke_marks_s"],
        "source":         record["source"],
        "recomputed":     recomputed,
        # What the server actually built from the marks. Lets the client confirm
        # "18 marks → 9 cycles" and makes a wrong stroke_type visible immediately —
        # it is NOT patchable, so a wrong value cannot be corrected through the API
        # and would otherwise silently halve the stroke rate.
        "cycles_derived": len(manual.get("cycle_bounds") or []),
        "marks_per_cycle": annot.marks_per_cycle(row.get("stroke_type")),
    }
    if recompute_error:
        resp["recompute_error"] = recompute_error
    if phases_error:
        resp["phases_error"] = phases_error
    return resp


@app.delete("/sessions/{session_id}/annotations")
async def delete_annotations(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Remove the session's annotation row (the seed remains available via GET) and
    restore the auto-computed metrics from metrics_json_auto if a recompute had
    overwritten them (Phase 47-04; the backup column itself is kept)."""
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    _, row = _owned_session(
        sb_admin, request.state.user_id, session_id, "metrics_json_auto"
    )
    try:
        sb_admin.table("session_annotations").delete().eq(
            "session_id", session_id
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    restored = False
    if row.get("metrics_json_auto") is not None:
        try:
            sb_admin.table("sessions").update(
                {"metrics_json": row["metrics_json_auto"]}
            ).eq("id", session_id).execute()
            restored = True
        except Exception:
            pass  # annotation row already gone; restore can be retried by re-deleting
    return {"ok": True, "metrics_restored": restored}


# Columns _rebuild_phases needs from a session row — shared by both endpoints below.
_PHASE_REBUILD_FIELDS = (
    "velocity_profile, distance_profile, acceleration_profile, metrics_json, "
    "sample_rate_hz, stroke_type"
)


def _rebuild_phases(sb_admin, session_id: str, row: dict) -> dict:
    """Re-derive metrics_json.phases from a session's STORED velocity/distance/acceleration
    profiles (no raw-CSV reprocessing) and persist it. Shared by POST /recompute and
    PUT /go-signal. The GO time is read from the row's own metrics_json.go_signal_s (None on
    most sessions) so reaction_time derives once a coach has set one. Only metrics_json is
    written; the rest of the row is preserved. Idempotent — always derives fresh from the
    stored profiles. Raises HTTPException on missing/mismatched profiles or a DB write error.
    """
    vel_arr = np.asarray(row.get("velocity_profile") or [], dtype=float)
    dist_arr = np.asarray(row.get("distance_profile") or [], dtype=float)
    # acceleration_profile may be absent on pre-Phase-64 sessions — an empty array is a
    # valid PhaseContext.accel; compute fns that need it (max_accel) handle emptiness.
    accel_arr = np.asarray(row.get("acceleration_profile") or [], dtype=float)
    if vel_arr.size < 2 or dist_arr.size != vel_arr.size:
        raise HTTPException(
            status_code=422,
            detail="velocity/distance profiles missing or mismatched",
        )

    fs = _session_fs(row)
    t_arr = np.arange(vel_arr.size) / fs

    # The coach's own marks outrank every detector (75-02 P2). Most sessions have no
    # annotation row; that is not an error, it just means the boundaries resolve from
    # the seed and the underwater detector instead.
    ann_phases = None
    try:
        _ann = (
            sb_admin.table("session_annotations")
            .select("phases")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if _ann.data:
            ann_phases = _ann.data[0].get("phases")
    except Exception:
        pass

    old_mj = row.get("metrics_json") or {}
    # Phase 75-06 — where "annotations first, auto fallback" lands for per-cycle metrics.
    # No precedence code is needed: PUT /annotations has already replaced metrics_json.cycles
    # with compute_session_metrics(manual=...) output (and flipped segmentation_reliable) for
    # any annotated session, so reading the stored values back gives the coach's cycles when
    # they exist and the segmenter's otherwise.
    old_dq = old_mj.get("data_quality") or {}
    ctx = pm.PhaseContext(
        t=t_arr, vel=vel_arr, dist=dist_arr, accel=accel_arr, fs=fs,
        stroke_type=row.get("stroke_type"), go_signal_s=old_mj.get("go_signal_s"),
        annotation_phases=ann_phases,
        seed_phases=annot.build_seed(old_mj, fs)["phases"],
        initial_phase=old_mj.get("initial_phase"),
        cycles=old_mj.get("cycles"),
        segmentation_reliable=bool(old_dq.get("segmentation_reliable", False)),
    )
    phases = pm.compute_phases(ctx)
    new_mj = _clean({**old_mj, "phases": phases})
    try:
        sb_admin.table("sessions").update(
            {"metrics_json": new_mj}
        ).eq("id", session_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return phases


@app.post("/sessions/{session_id}/recompute")
async def recompute_phases(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Rebuild the session's `phases` object (Phase 75-01) from its STORED
    velocity/distance/acceleration profiles — no raw-CSV reprocessing. This is the
    backfill seam (CONTEXT.md D16): a metric added to phase_metrics.REGISTRY later can
    be filled in on every existing session by re-calling this endpoint, the same pattern
    Phase 64 used to backfill acceleration_profile. Only metrics_json.phases is touched;
    session/cycles/initial_phase/data_quality are preserved unchanged. Idempotent —
    calling it twice in a row yields the same shape, since it always derives fresh from
    the stored profiles rather than accumulating state.
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    _, row = _owned_session(
        sb_admin, request.state.user_id, session_id, _PHASE_REBUILD_FIELDS,
    )
    phases = _rebuild_phases(sb_admin, session_id, row)
    return {"session_id": session_id, "phases": _clean(phases), "recomputed": True}


@app.put("/sessions/{session_id}/go-signal")
async def set_go_signal(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Set (or clear) the coach GO-signal time for a session, then recompute phase metrics so
    reaction_time (Phase 75-04) refreshes. go_signal_s is stored in metrics_json (jsonb, no
    migration) as **session-clock seconds** — the same axis as the velocity trace. This is the
    CORRECTION path; the primary path is the optional go_signal_s form field on POST /process
    (Phase 84-02). ⚠ The note that once stood here — "real phone↔encoder clock sync is deferred
    (CONTEXT D13)" — was stale: the app has computed that correlation since Phase 47 off the
    8-byte META reply. Body: {"go_signal_s": <number ≥ 0 | null>};
    null clears it. reaction_time = first encoder motion onset − go_signal_s (None if unset or
    if GO was logged after the swimmer already moved).
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="invalid JSON body")
    if not isinstance(body, dict) or "go_signal_s" not in body:
        raise HTTPException(status_code=422, detail="body must include go_signal_s")
    go = body["go_signal_s"]
    if go is not None:
        if isinstance(go, bool) or not isinstance(go, (int, float)) \
                or not math.isfinite(go) or go < 0:
            raise HTTPException(
                status_code=422, detail="go_signal_s must be a number ≥ 0 or null",
            )
        go = float(go)

    _, row = _owned_session(
        sb_admin, request.state.user_id, session_id, _PHASE_REBUILD_FIELDS,
    )
    mj = row.get("metrics_json") or {}
    mj["go_signal_s"] = go
    row["metrics_json"] = mj  # feed the updated GO time into the rebuild
    phases = _rebuild_phases(sb_admin, session_id, row)
    return {
        "session_id": session_id,
        "go_signal_s": go,
        "reaction_time": phases.get("start", {}).get("reaction_time", {}).get("value"),
        "phases": _clean(phases),
    }


# Max accepted video upload size. Tracks the ACTIVE Supabase global upload limit — 50 MB on the free
# tier, a hard ceiling that per-bucket limits cannot exceed. Enforced below BEFORE the file is
# buffered, so an oversized external-camera clip 413s instead of OOMing the container, and matches the
# client MAX_VIDEO_BYTES in web/components/portal/VideoPane.js. (Phase 67-02; also partially satisfies
# Phase 49-01's "memory-safe upload size caps".)
# ⚠ ON PRO: raise this to 500, raise the Supabase global limit, and apply supabase/patch_11.
MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50 MB (free-tier ceiling)


@app.post("/sessions/{session_id}/video")
async def upload_session_video(
    session_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    video_origin_s: Optional[float] = Form(None),
    _auth=Depends(require_auth),
):
    """Attach a video to a session (private `videos` bucket, {session_id}.mp4), or
    update just video_origin_s (origin nudge) when no file is sent. origin_s =
    session-clock time at video t=0 (44-03 end-anchor: deviceDuration − videoDuration).
    """
    if file is None and video_origin_s is None:
        raise HTTPException(
            status_code=422, detail="Provide a video file and/or video_origin_s"
        )

    # Phase 67-02: reject an oversized clip BEFORE any Storage work or buffering. Prefer the
    # multipart part size; fall back to Content-Length. This is the memory-safe guard that keeps a
    # large external-camera file from being read into RAM (the upload below streams, never reads).
    if file is not None:
        size = file.size
        if size is None:
            cl = request.headers.get("content-length")
            size = int(cl) if cl and cl.isdigit() else None
        if size is not None and size > MAX_VIDEO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Video too large; max {MAX_VIDEO_BYTES // (1024 * 1024)} MB.",
            )

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    _, row = _owned_session(
        sb_admin, request.state.user_id, session_id, "video_path, video_origin_s"
    )

    updates = {}
    if file is not None:
        # Read into memory and upload BYTES. ⚠ storage3 only accepts bytes / BufferedReader / FileIO;
        # a Starlette SpooledTemporaryFile (`file.file`) is NONE of those, so passing it made storage3
        # fall through to `open(file, "rb")` and raise TypeError — every upload 500'd (the 67-02
        # "streaming" regression that broke phone Record-with-Video). The 413 size guard ABOVE runs
        # before this read, so an oversized file is rejected pre-buffer — reading bytes here is
        # memory-safe for anything within MAX_VIDEO_BYTES (50 MB fits in RAM fine).
        video_bytes = await file.read()
        if not video_bytes:
            raise HTTPException(status_code=422, detail="Empty video file")
        storage_path = f"{session_id}.mp4"
        try:
            sb_admin.storage.from_("videos").upload(
                path=storage_path,
                file=video_bytes,
                file_options={
                    "content-type": file.content_type or "video/mp4",
                    "x-upsert": "true",  # re-upload replaces the previous attachment
                },
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Video upload failed: {e}")
        updates["video_path"] = storage_path
    if video_origin_s is not None:
        updates["video_origin_s"] = video_origin_s

    try:
        sb_admin.table("sessions").update(updates).eq("id", session_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "ok": True,
        "video_path": updates.get("video_path", row.get("video_path")),
        "video_origin_s": updates.get("video_origin_s", row.get("video_origin_s")),
    }


@app.get("/sessions/{session_id}/video-url")
async def session_video_url(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Time-limited signed URL for the session's video (bucket is private; bytes
    never proxy through this API). 404 when the session has no video attached."""
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    _, row = _owned_session(
        sb_admin, request.state.user_id, session_id, "video_path, video_origin_s"
    )
    video_path = row.get("video_path")
    if not video_path:
        raise HTTPException(status_code=404, detail="No video attached to this session")

    try:
        signed = sb_admin.storage.from_("videos").create_signed_url(video_path, 3600)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    url = (signed or {}).get("signedURL") or (signed or {}).get("signedUrl")
    if not url:
        raise HTTPException(status_code=500, detail="Could not create signed URL")
    return {"url": url, "origin_s": row.get("video_origin_s")}


# ── Multi-camera external videos (Phase 69) ───────────────────────────────────
# The phone/primary video stays in sessions.video_path/video_origin_s (legacy /video +
# /video-url above, unchanged). These endpoints manage the <=3 EXTERNAL videos in the
# session_videos table (patch_12). Access is service-role through the API; RLS denies anon.
MAX_EXTERNAL_VIDEOS = 3


def _signed_video_url(sb_admin, storage_path: str) -> Optional[str]:
    """3600 s signed URL for an object in the private `videos` bucket, or None on failure."""
    try:
        signed = sb_admin.storage.from_("videos").create_signed_url(storage_path, 3600)
    except Exception:
        return None
    return (signed or {}).get("signedURL") or (signed or {}).get("signedUrl")


@app.get("/sessions/{session_id}/videos")
async def list_session_videos(
    session_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Unified camera list for the multi-cam player: the phone/primary video (from the legacy
    sessions columns) plus every external (session_videos), each with a signed URL. Phase 69."""
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    _, row = _owned_session(
        sb_admin, request.state.user_id, session_id, "video_path, video_origin_s"
    )

    videos = []
    primary_path = row.get("video_path")
    if primary_path:
        videos.append({
            "id": "primary",
            "role": "phone",
            "label": "Phone",
            "url": _signed_video_url(sb_admin, primary_path),
            "origin_s": row.get("video_origin_s"),
        })

    try:
        ext = (
            sb_admin.table("session_videos")
            .select("id, storage_path, origin_s, label, created_at")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    for r in ext.data or []:
        videos.append({
            "id": r["id"],
            "role": "external",
            "label": r.get("label"),
            "url": _signed_video_url(sb_admin, r["storage_path"]),
            "origin_s": r.get("origin_s"),
        })

    return {"videos": videos}


@app.post("/sessions/{session_id}/videos")
async def add_session_video(
    session_id: str,
    request: Request,
    file: UploadFile = File(...),
    label: Optional[str] = Form(None),
    _auth=Depends(require_auth),
):
    """Attach an EXTERNAL video (multipart) to a session — up to MAX_EXTERNAL_VIDEOS. The
    phone/primary video uses the legacy POST /video instead. Phase 69."""
    # Reject oversized BEFORE buffering (same memory-safe guard as /video, Phase 67-02).
    size = file.size
    if size is None:
        cl = request.headers.get("content-length")
        size = int(cl) if cl and cl.isdigit() else None
    if size is not None and size > MAX_VIDEO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Video too large; max {MAX_VIDEO_BYTES // (1024 * 1024)} MB.",
        )

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    _owned_session(sb_admin, request.state.user_id, session_id, "id")

    try:
        existing = (
            sb_admin.table("session_videos").select("id").eq("session_id", session_id).execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if len(existing.data or []) >= MAX_EXTERNAL_VIDEOS:
        raise HTTPException(
            status_code=409, detail=f"Max {MAX_EXTERNAL_VIDEOS} external videos per session"
        )

    # Upload BYTES — storage3 rejects a SpooledTemporaryFile (`file.file`); the size guard above
    # already rejected anything over MAX_VIDEO_BYTES pre-buffer, so this read is memory-safe.
    video_bytes = await file.read()
    if not video_bytes:
        raise HTTPException(status_code=422, detail="Empty video file")

    vid = str(uuid.uuid4())
    storage_path = f"{session_id}/{vid}.mp4"
    try:
        sb_admin.storage.from_("videos").upload(
            path=storage_path,
            file=video_bytes,
            file_options={
                "content-type": file.content_type or "video/mp4",
                "x-upsert": "true",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video upload failed: {e}")

    try:
        sb_admin.table("session_videos").insert({
            "id": vid,
            "session_id": session_id,
            "storage_path": storage_path,
            "label": label,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "id": vid,
        "role": "external",
        "label": label,
        "url": _signed_video_url(sb_admin, storage_path),
        "origin_s": None,
    }


@app.patch("/sessions/{session_id}/videos/{video_id}")
async def update_session_video(
    session_id: str,
    video_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Update an external video's label and/or origin_s (per-camera push-off sync). Phase 69."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    allowed = {"label", "origin_s"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    _owned_session(sb_admin, request.state.user_id, session_id, "id")

    try:
        resp = (
            sb_admin.table("session_videos")
            .update(updates)
            .eq("id", video_id)
            .eq("session_id", session_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not (resp.data or []):
        raise HTTPException(status_code=404, detail="Video not found on this session")
    return resp.data[0]


@app.delete("/sessions/{session_id}/videos/{video_id}")
async def delete_session_video(
    session_id: str,
    video_id: str,
    request: Request,
    _auth=Depends(require_auth),
):
    """Delete one external video — its storage object (non-fatal) then the row. Phase 69."""
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")
    _owned_session(sb_admin, request.state.user_id, session_id, "id")

    try:
        resp = (
            sb_admin.table("session_videos")
            .select("storage_path")
            .eq("id", video_id)
            .eq("session_id", session_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not (resp.data or []):
        raise HTTPException(status_code=404, detail="Video not found on this session")

    try:
        sb_admin.storage.from_("videos").remove([resp.data[0]["storage_path"]])
    except Exception:
        pass  # storage removal non-fatal (mirrors DELETE /sessions)

    try:
        sb_admin.table("session_videos").delete().eq("id", video_id).eq(
            "session_id", session_id
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


@app.get("/annotations/export")
async def export_annotations(request: Request, _auth=Depends(require_auth)):
    """Ground-truth bulk export (Phase 47-04): every annotated session owned by the
    calling coach, with the annotation doc + enough session context to pair it with
    the raw data for segmenter tuning (16-06). Mirrored locally by fetch_annotations.py.
    """
    sb_admin = _get_supabase_admin()
    if not sb_admin:
        raise HTTPException(status_code=503, detail="Storage not configured")

    coach_resp = (
        sb_admin.table("coaches")
        .select("id")
        .eq("user_id", request.state.user_id)
        .limit(1)
        .execute()
    )
    coach_row_id = coach_resp.data[0]["id"] if coach_resp.data else None
    if not coach_row_id:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    sess_resp = (
        sb_admin.table("sessions")
        .select("id, stroke_type, created_at, raw_csv_path, metrics_json")
        .eq("coach_id", coach_row_id)
        .execute()
    )
    sess_by_id = {s["id"]: s for s in (sess_resp.data or [])}
    if not sess_by_id:
        return {"sessions": []}

    ann_resp = (
        sb_admin.table("session_annotations")
        .select("session_id, phases, stroke_marks_s, source, updated_at")
        .in_("session_id", list(sess_by_id.keys()))
        .execute()
    )

    out = []
    for a in ann_resp.data or []:
        s = sess_by_id.get(a["session_id"])
        if not s:
            continue  # defensive — .in_ already scoped to this coach's sessions
        lap = ((s.get("metrics_json") or {}).get("session") or {}).get("lap_time_s")
        out.append({
            "session_id":   a["session_id"],
            "stroke_type":  s.get("stroke_type"),
            "created_at":   s.get("created_at"),
            "duration_s":   lap,
            "raw_csv_path": s.get("raw_csv_path"),
            "annotation": {
                "phases":         a.get("phases"),
                "stroke_marks_s": a.get("stroke_marks_s"),
                "source":         a.get("source"),
                "updated_at":     a.get("updated_at"),
            },
        })
    return {"sessions": out}


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

    team_id    = coach["team_id"]
    limit      = coach.get("athlete_limit")
    if ENFORCE_TIER_LIMITS and limit is not None:
        try:
            r = (
                sb_admin.table("athletes")
                .select("id", count="exact")
                .eq("team_id", team_id)
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
                "name":         name,
                "stroke_type":  stroke_type,
                "head_waist_m": hw,
            })
            .select("id, name, stroke_type, head_waist_m")
            .execute()
        )
        # .insert() returns a mutation builder (SyncQueryRequestBuilder) which has no
        # .single() — chaining it raises AttributeError. Take the first returned row instead.
        row = (resp.data or [None])[0]
        if row is None:
            raise HTTPException(status_code=500, detail="Athlete insert returned no row")
        return row
    except HTTPException:
        raise
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
    coach_team_id = None
    try:
        coach_resp = (
            sb_admin.table("coaches")
            .select("id, team_id")
            .eq("user_id", request.state.user_id)
            .single()
            .execute()
        )
        coach_row_id = coach_resp.data["id"] if coach_resp.data else None
        coach_team_id = coach_resp.data.get("team_id") if coach_resp.data else None
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
                  + coach._DRILL_HINT + "\n" + coach._GUARDRAILS + "\n\nSESSION DATA:\n" + data_block)
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

    # ── Team executors — scoped to the coach's whole roster (team_id), NOT one athlete.
    # One athletes query + one sessions query per turn, cached for the request; aggregation
    # is pure (roster_metrics) so the model only ever sees compact tables, never raw cycles.
    _roster_cache = {}

    def _load_roster_rows():
        if "rows" in _roster_cache:
            return _roster_cache["rows"]
        # Let query failures propagate — a backend outage must surface as a tool error,
        # not masquerade as an empty roster ("you have no athletes").
        # athletes has no coach_id column — the roster is team-scoped. sessions stays on
        # coach_id below; that column exists there and that scoping is correct.
        arows = (sb_admin.table("athletes").select("id, name")
                 .eq("team_id", coach_team_id).execute()).data or []
        names = {a.get("id"): a.get("name") for a in arows}
        srows = (sb_admin.table("sessions")
                 .select("athlete_id, created_at, metrics_json")
                 .eq("coach_id", coach_row_id)
                 .order("created_at", desc=True)
                 .execute()).data or []
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
        try:
            rows = _load_roster_rows()
        except Exception:
            return {"error": "Could not load the team roster."}
        ranking = roster_metrics.rank_athletes(
            roster_metrics.latest_per_athlete(rows),
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
        min_sessions = max(min_sessions, 2)   # progress needs ≥2 points; also blocks 0/negative
        try:
            rows = _load_roster_rows()
        except Exception:
            return {"error": "Could not load the team roster."}
        return {"metric": metric,
                **roster_metrics.rank_progress(rows, metric, min_sessions=min_sessions)}

    def _exec_team_summary(args):
        try:
            rows = _load_roster_rows()
        except Exception:
            return {"error": "Could not load the team roster."}
        return roster_metrics.team_summary(rows, _SESSION_SUMMARY_KEYS)

    def _exec_recommend_drills(args):
        # Grounds the call-to-action in the curated library, matched to THIS session's metrics.
        flags = drills.flags_from_session(session)
        matched = drills.match_drills(flags)
        out = {"flags": sorted(flags),
               "drills": [{k: d[k] for k in ("id", "name", "how_to", "why", "targets")}
                          for d in matched]}
        if not matched:
            out["note"] = "no metric problems flagged — the swim looks solid"
        return out

    _EXECUTORS = {
        "list_athlete_sessions": _exec_list_athlete_sessions,
        "get_session_metrics": _exec_get_session_metrics,
        "rank_athletes": _exec_rank_athletes,
        "rank_progress": _exec_rank_progress,
        "team_summary": _exec_team_summary,
        "recommend_drills": _exec_recommend_drills,
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
                tools=coach.COACH_TOOLS + coach.TEAM_TOOLS + coach.DRILL_TOOLS,
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
        "id, team_id, subscription_tier, subscription_status, athlete_limit, device_limit, monthly_session_limit"
    )
    if not coach:
        raise HTTPException(status_code=403, detail="Coach profile not found")

    coach_id = coach["id"]
    team_id = coach.get("team_id")
    now = datetime.datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    athlete_count, device_count, session_count = 0, 0, 0
    try:
        r = sb_admin.table("athletes").select("id", count="exact").eq("team_id", team_id).execute()
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
