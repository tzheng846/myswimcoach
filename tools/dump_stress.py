#!/usr/bin/env python3
"""
dump_stress.py — measure the BLE dump-disconnect rate WITHOUT the phone.

WHY THIS EXISTS
---------------
Reported symptom: "the device often disconnects during the data dumping time."
"Often" is not a repro. This harness turns it into a NUMBER, and — more importantly —
answers the one question that halves the hypothesis space:

    Does the dump also drop when the central is a laptop instead of the iPhone?

    drops here too  -> firmware / link layer.  The phone is innocent.
    clean here      -> phone side (react-native-ble-plx, iOS, the JS re-render storm).

It reuses the exact protocol logger_ble.py speaks (META -> DUMP -> 0xEE), so it exercises
the real firmware path in ESP_32_V5.ino: dumpBuffer() streaming 24-sample indications.

WHAT IT PROVES / DOES NOT PROVE
-------------------------------
Proves: whether the link survives a full dump, how far it got when it didn't, and whether
        failures cluster at a repeatable offset (deterministic) or scatter (timing/link).
Does NOT prove: anything about the phone's BLE stack, and it cannot see an ESP32 reboot.
        Capture the serial log at the same time (115200) — the firmware already prints
        "[DUMP] Aborted at N/M — disconnected (buffer retained)", and a reboot shows a
        boot banner. Those two lines tell crash-vs-clean-drop apart.

SAFE TO RUN REPEATEDLY
----------------------
Phase 74 made the device retain its buffer until an explicit CLEAR. This harness NEVER
sends CLEAR, so one recorded session can be dumped many times over. Record once, stress
many. (It also never sends START/STOP, so it cannot disturb a recording.)

USAGE
    python tools/dump_stress.py                 # 10 dump cycles
    python tools/dump_stress.py -n 25           # 25 cycles
    python tools/dump_stress.py --reconnect     # disconnect + reconnect between cycles
    python tools/dump_stress.py --csv out.csv   # per-run rows for later analysis

Requires: pip install bleak   (already a dependency of logger_ble.py)
"""

import argparse
import asyncio
import csv
import statistics
import sys
import time
from pathlib import Path

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    sys.exit("ERROR: bleak is not installed.  pip install bleak")

# ── Protocol (must match ESP_32_V5.ino) ───────────────────────────────────────
DEVICE_PREFIX = "SwimLogger"
RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # laptop -> ESP32 (write)
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # ESP32 -> laptop (indicate)

SAMPLE_SIZE = 7           # <IHB — timestamp_us, angle_counts, magnet_ok
META_SIZE = 8
END_OF_DUMP_MARKER = 0xEE

# Same 8 s window the phone uses (RecordScreen.js RETRIEVAL_STALL_MS), so a STALL here
# means the phone would also have given up.
STALL_S = 8.0
DUMP_TIMEOUT_S = 180.0     # hard ceiling; a 60 s buffer dumps in ~20 s


class Outcome:
    OK = "OK"                   # 0xEE arrived
    DISCONNECTED = "DISCONNECT"  # link dropped mid-dump — the reported symptom
    STALL = "STALL"             # link up, packets stopped (the Phase 74 symptom)
    ERROR = "ERROR"             # something else threw


async def find_device(timeout: float):
    devices = await BleakScanner.discover(timeout=timeout)
    for d in devices:
        if d.name and d.name.startswith(DEVICE_PREFIX):
            return d
    return None


async def one_dump(device, run_idx: int, verbose: bool) -> dict:
    """Run a single META -> DUMP cycle. Returns a result row. Never sends CLEAR."""
    state = {
        "run": run_idx,
        "outcome": Outcome.ERROR,
        "samples": 0,
        "packets": 0,
        "elapsed_s": 0.0,
        "meta_ok": False,
        "detail": "",
    }

    done = asyncio.Event()
    dropped = asyncio.Event()
    last_pkt = time.monotonic()

    def on_disconnect(_client):
        # Fires when the peripheral goes away mid-operation — the reported symptom.
        dropped.set()
        done.set()

    def on_data(_char, data: bytearray):
        nonlocal last_pkt
        last_pkt = time.monotonic()
        if len(data) == META_SIZE and not state["meta_ok"]:
            state["meta_ok"] = True
            return
        if len(data) == 1 and data[0] == END_OF_DUMP_MARKER:
            state["outcome"] = Outcome.OK
            done.set()
            return
        if len(data) and len(data) % SAMPLE_SIZE == 0:
            state["packets"] += 1
            state["samples"] += len(data) // SAMPLE_SIZE

    t0 = time.monotonic()
    try:
        async with BleakClient(device, disconnected_callback=on_disconnect) as client:
            await client.start_notify(TX_UUID, on_data)

            await client.write_gatt_char(RX_UUID, b"META\n", response=True)
            # Firmware replies to META, then the dump is a separate command (same as the app).
            await asyncio.sleep(0.4)
            await client.write_gatt_char(RX_UUID, b"DUMP\n", response=True)

            # Wait for the marker, a drop, a stall, or the hard ceiling.
            while not done.is_set():
                if time.monotonic() - t0 > DUMP_TIMEOUT_S:
                    state["outcome"] = Outcome.STALL
                    state["detail"] = "hard timeout"
                    break
                if time.monotonic() - last_pkt > STALL_S:
                    state["outcome"] = Outcome.STALL
                    state["detail"] = f"no packet for {STALL_S:.0f}s"
                    break
                await asyncio.sleep(0.05)

            if dropped.is_set():
                state["outcome"] = Outcome.DISCONNECTED
                state["detail"] = "link dropped mid-dump"

            if state["outcome"] == Outcome.OK:
                try:
                    await client.stop_notify(TX_UUID)
                except Exception:
                    pass
    except Exception as e:  # includes a drop during connect/teardown
        if dropped.is_set() or "disconnect" in str(e).lower():
            state["outcome"] = Outcome.DISCONNECTED
        state["detail"] = f"{type(e).__name__}: {e}"

    state["elapsed_s"] = round(time.monotonic() - t0, 2)

    if verbose:
        print(f"  run {run_idx:>3}  {state['outcome']:<11} "
              f"{state['samples']:>7} samples  {state['packets']:>5} pkts  "
              f"{state['elapsed_s']:>6.2f}s  {state['detail']}")
    return state


async def main_async(args) -> int:
    print(f"Scanning for '{DEVICE_PREFIX}*' ...")
    device = await find_device(args.scan_timeout)
    if device is None:
        print(f"ERROR: no '{DEVICE_PREFIX}*' found. Is the encoder powered on and advertising?")
        return 2
    print(f"Found: {device.name}  [{device.address}]")
    print(f"Running {args.n} dump cycles. CLEAR is never sent, so the session survives.\n")

    rows = []
    for i in range(1, args.n + 1):
        rows.append(await one_dump(device, i, verbose=True))
        if i < args.n:
            await asyncio.sleep(args.gap)

    # ── Report ────────────────────────────────────────────────────────────────
    counts = {}
    for r in rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1

    ok = counts.get(Outcome.OK, 0)
    drops = counts.get(Outcome.DISCONNECTED, 0)
    stalls = counts.get(Outcome.STALL, 0)

    print("\n" + "=" * 62)
    print(f"{len(rows)} cycles:  {ok} OK  ·  {drops} DISCONNECT  ·  "
          f"{stalls} STALL  ·  {counts.get(Outcome.ERROR, 0)} ERROR")
    print(f"failure rate: {100 * (len(rows) - ok) / len(rows):.0f}%")

    good = [r["samples"] for r in rows if r["outcome"] == Outcome.OK]
    if good:
        print(f"complete dump = {statistics.mode(good)} samples "
              f"(range {min(good)}-{max(good)}), "
              f"{statistics.mean(r['elapsed_s'] for r in rows if r['outcome'] == Outcome.OK):.1f}s avg")

    bad = [r["samples"] for r in rows if r["outcome"] != Outcome.OK]
    if bad:
        print(f"\nsamples received when it FAILED: {sorted(bad)}")
        spread = max(bad) - min(bad)
        if len(bad) > 1 and good and spread < 0.02 * max(good):
            print("  -> tightly clustered. Suggests a DETERMINISTIC boundary "
                  "(heap/buffer/packet-count), not a timing flake.")
        elif len(bad) > 1:
            print("  -> scattered. Suggests a TIMING / link-layer cause "
                  "(supervision timeout, contention), not a fixed boundary.")

    print("\nNow compare against the phone on the SAME buffered session.")
    print("Cross-check the serial log (115200) for:")
    print("  '[DUMP] Aborted at N/M — disconnected'  -> firmware saw a clean link drop")
    print("  a boot banner / garbage                 -> the ESP32 RESET (crash, WDT, brownout)")
    print("=" * 62)

    if args.csv:
        out = Path(args.csv)
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nper-run rows -> {out}")

    return 0 if drops == 0 and stalls == 0 else 1


def main() -> None:
    p = argparse.ArgumentParser(description="Measure the BLE dump-disconnect rate without the phone.")
    p.add_argument("-n", type=int, default=10, help="number of dump cycles (default 10)")
    p.add_argument("--gap", type=float, default=1.5, help="seconds between cycles (default 1.5)")
    p.add_argument("--scan-timeout", type=float, default=15.0, help="scan timeout (default 15)")
    p.add_argument("--csv", help="write per-run rows to this CSV")
    args = p.parse_args()
    try:
        sys.exit(asyncio.run(main_async(args)))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
