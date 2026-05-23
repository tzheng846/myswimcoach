import math
import os
import tempfile
import time
from typing import Optional

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from supabase import Client, create_client

SUPABASE_URL             = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY        = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

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
    _auth=Depends(require_auth),
):
    raw_path = None
    raw_bytes = None
    try:
        # Save upload to temp file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            raw_bytes = await file.read()
            tmp.write(raw_bytes)
            raw_path = tmp.name

        # ── Signal processing ─────────────────────────────────────────────
        df = vae.load_data(raw_path)
        _, angle_unwrapped = vae.unwrap_angle(df)
        dist_m = vae.counts_to_distance(angle_unwrapped, vae.METERS_PER_COUNT)
        t = df["time_s"].values

        pos_diffs = np.diff(t)
        pos_diffs = pos_diffs[pos_diffs > 0]
        if len(pos_diffs) == 0:
            raise ValueError("No valid timestamps — file may be corrupt")
        native_fs = 1.0 / np.median(pos_diffs)

        dist_native, _ = vae.interpolate_to_uniform(dist_m, t, native_fs)
        dist_dec, t_dec, actual_fs = vae.decimate_signal(dist_native, native_fs, 100.0)
        t_dec = t_dec + t[0]

        vel = np.gradient(dist_dec, 1.0 / actual_fs)

        # Coarse acceleration (5 Hz), interpolated back to full rate
        vel_coarse, t_coarse, fs_coarse = vae.decimate_signal(vel, actual_fs, 5.0)
        t_coarse = t_coarse + t[0]
        accel_coarse = np.gradient(vel_coarse, 1.0 / fs_coarse)
        accel = np.interp(t_dec, t_coarse, accel_coarse)  # noqa: F841

        # ── Metrics ──────────────────────────────────────────────────────
        result = m.compute_session_metrics(t_dec, vel, dist_dec, head_waist_m=head_waist_m)

        # ── Supabase storage + session save ───────────────────────────────
        storage_path = None
        sb_admin = _get_supabase_admin()

        if sb_admin and athlete_id:
            timestamp = int(time.time())
            storage_path = f"{athlete_id}/{timestamp}.csv"

            # Upload raw CSV to Supabase Storage
            try:
                sb_admin.storage.from_("raw-csvs").upload(
                    path=storage_path,
                    file=raw_bytes,
                    file_options={"content-type": "text/csv"},
                )
            except Exception:
                storage_path = None  # non-fatal — proceed without storage

            # Look up coaches.id from auth.users.id
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

            # Insert full session row
            try:
                session_row = {
                    "athlete_id":       athlete_id,
                    "coach_id":         coach_row_id,
                    "metrics_json":     _clean({"session": result["session"], "cycles": result["cycles"], "initial_phase": result.get("initial_phase", {})}),
                    "velocity_profile": _clean(vel.tolist()),
                    "distance_profile": _clean(dist_dec.tolist()),
                    "raw_csv_path":     storage_path,
                    "upload_status":    "complete",
                }
                sb_admin.table("sessions").insert(session_row).execute()
            except Exception:
                pass  # non-fatal — results still returned to client

        return {
            "session":       _clean(result["session"]),
            "cycles":        _clean(result["cycles"]),
            "initial_phase": _clean(result.get("initial_phase", {})),
            "time":          _clean(t_dec.tolist()),
            "velocity":      _clean(vel.tolist()),
            "distance":      _clean(dist_dec.tolist()),
            "raw_csv_path":  storage_path,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if raw_path and os.path.exists(raw_path):
            os.unlink(raw_path)
