"""Shared test fixtures for Swimnetics backend tests."""
import csv
import io
import math
import os
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

# Ensure myswimcoach/ is on sys.path so `import metrics` and `import api` work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Supabase mock ─────────────────────────────────────────────────────────────
# The local myswimcoach/supabase/ directory (SQL migrations) is a namespace
# package that shadows the real supabase Python package.  Inject a mock before
# api.py is imported so `from supabase import Client, create_client` succeeds.
# api.py never actually calls create_client in tests because SUPABASE_URL is
# empty and require_auth is overridden in the api_client fixture.
if not (
    "supabase" in sys.modules
    and hasattr(sys.modules["supabase"], "create_client")
):
    _mock_sb = MagicMock()
    _mock_sb.Client = type("Client", (), {})  # plain class satisfies type annotation
    _mock_sb.create_client = MagicMock(return_value=MagicMock())
    sys.modules["supabase"] = _mock_sb

# ── Constants (mirror vel_acc_extraction.py) ──────────────────────────────────
WHEEL_DIAMETER_M = 0.06
METERS_PER_COUNT = math.pi * WHEEL_DIAMETER_M / 4096  # ≈ 4.598e-5 m/count
SYNTHETIC_FS_HZ = 270
SYNTHETIC_DURATION_S = 30


def _make_csv(duration_s=SYNTHETIC_DURATION_S, fs_hz=SYNTHETIC_FS_HZ, dropout_fraction=0.0) -> bytes:
    """
    Generate a realistic encoder CSV as bytes.
    Simulates breaststroke: ~0.5 Hz cycle, mean velocity ~0.8 m/s.
    dropout_fraction: fraction of rows to set magnet_ok=0.
    """
    n = int(duration_s * fs_hz)
    dt = 1.0 / fs_hz
    t_s = np.arange(n) * dt

    # Sinusoidal velocity: 0.4–1.2 m/s at 0.5 Hz (≈ 30 SPM breaststroke)
    vel = 0.8 + 0.4 * np.sin(2 * np.pi * 0.5 * t_s)
    vel = np.maximum(vel, 0.05)  # no backwards motion

    # Cumulative distance → counts → wrap to 0–4095 (device behaviour)
    dist = np.concatenate([[0.0], np.cumsum(vel[:-1] * dt)])
    cum_counts = np.round(dist / METERS_PER_COUNT).astype(int)
    angle_counts = cum_counts % 4096

    timestamp_us = (t_s * 1e6).astype(int)

    # Decide which rows get magnet_ok=0
    rng = np.random.default_rng(42)
    dropout_mask = rng.random(n) < dropout_fraction

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["timestamp_us", "angle_counts", "magnet_ok"])
    for i in range(n):
        w.writerow([int(timestamp_us[i]), int(angle_counts[i]), 0 if dropout_mask[i] else 1])
    return buf.getvalue().encode("utf-8")


@pytest.fixture
def synthetic_csv_bytes() -> bytes:
    """30-second synthetic encoder CSV, all magnet_ok=1."""
    return _make_csv()


@pytest.fixture
def synthetic_csv_with_dropout() -> bytes:
    """30-second synthetic encoder CSV, 10% rows have magnet_ok=0."""
    return _make_csv(dropout_fraction=0.10)


@pytest.fixture
def real_session():
    """
    Real breaststroke session loaded from processed/breaststroke_sample.csv.
    Returns (t, vel, dist) numpy arrays ready for compute_session_metrics.
    """
    import csv as _csv_mod
    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "processed", "breaststroke_sample.csv",
    )
    t, vel, dist = [], [], []
    with open(fixture_path, newline="") as f:
        reader = _csv_mod.DictReader(f)
        for row in reader:
            t.append(float(row["time_s"]))
            vel.append(float(row["vel_ms"]))
            dist.append(float(row["dist_m"]))
    return np.array(t), np.array(vel), np.array(dist)


@pytest.fixture
def api_client():
    """
    FastAPI TestClient with require_auth replaced by a no-op mock.
    Avoids any Supabase network call during tests.
    """
    from fastapi.testclient import TestClient
    from starlette.requests import Request
    from api import app, require_auth

    def mock_auth(request: Request):
        request.state.user_id = "test-user-id"

    app.dependency_overrides[require_auth] = mock_auth
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()
