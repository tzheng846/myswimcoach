import math
import os
import tempfile

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import metrics as m
import vel_acc_extraction as vae

app = FastAPI()

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
async def process_session(file: UploadFile = File(...)):
    raw_path = None
    try:
        # Save upload to temp file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(await file.read())
            raw_path = tmp.name

        # ── Signal processing (bypass process_file to skip HTML generation) ──
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
        accel = np.interp(t_dec, t_coarse, accel_coarse)  # noqa: F841 (reserved for future use)

        # ── Metrics ──────────────────────────────────────────────────────────
        result = m.compute_session_metrics(t_dec, vel, dist_dec)

        return {
            "session":  _clean(result["session"]),
            "cycles":   _clean(result["cycles"]),
            "time":     _clean(t_dec.tolist()),
            "velocity": _clean(vel.tolist()),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if raw_path and os.path.exists(raw_path):
            os.unlink(raw_path)
