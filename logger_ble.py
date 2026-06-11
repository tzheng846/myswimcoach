"""
logger_ble.py
─────────────
Receives AS5600 data from the SwimLogger ESP32 over BLE (Nordic UART Service)
and saves it to a timestamped CSV in raw/.

Supports both live-streaming firmware (START/STOP) and buffer-and-dump
firmware (ESP_32_V5: META/DUMP).

Requires: conda install -n mySwimCoach -c conda-forge bleak

Usage:
    python logger_ble.py                        # connect and receive data
    python logger_ble.py --name MyDevice        # custom BLE device name
    python logger_ble.py --command START        # send START then receive data
    python logger_ble.py --command STOP         # send STOP and exit
    python logger_ble.py --command META         # print buffered-session metadata and exit
    python logger_ble.py --command DUMP         # retrieve buffered session, exit at end marker

Press Ctrl+C to stop recording (live mode; DUMP exits on its own).

Output CSV columns match logger.py exactly: timestamp_us, angle_counts, magnet_ok
"""

import asyncio
import argparse
import csv
import struct
from datetime import datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "SwimLogger"
# Nordic UART Service characteristics
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # ESP32 → laptop (notify)
RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # laptop → ESP32 (write)

# Per sample: uint32 timestamp_us (LE) | uint16 angle_counts (LE) | uint8 magnet_ok
# Firmware sends a variable number of samples per notify — any multiple of 7 is valid.
SAMPLE_SIZE = 7
# META response: [session_start_us: uint32 LE][device_now_us: uint32 LE]
META_SIZE = 8
# Single-byte end-of-dump marker (1 byte ≠ multiple of 7 → never a sample packet)
END_OF_DUMP_MARKER = 0xEE


def parse_packet(data: bytes) -> list[tuple]:
    """Parse a notify payload of N samples (length must be a multiple of 7)."""
    samples = []
    for offset in range(0, len(data), SAMPLE_SIZE):
        samples.append(struct.unpack_from("<IHB", data, offset))
    return samples


async def fetch_meta(client: BleakClient) -> None:
    """Send META and print the decoded 8-byte response."""
    meta_event = asyncio.Event()
    meta: dict[str, int] = {}

    def on_meta(_, data: bytearray) -> None:
        if len(data) == META_SIZE and not meta_event.is_set():
            meta["start_us"], meta["now_us"] = struct.unpack("<II", bytes(data))
            meta_event.set()

    await client.start_notify(TX_UUID, on_meta)
    await client.write_gatt_char(RX_UUID, b"META\n")
    print("Sent command: META")
    try:
        await asyncio.wait_for(meta_event.wait(), timeout=10)
    except asyncio.TimeoutError:
        print("ERROR: no META response within 10 s")
        return
    finally:
        try:
            await client.stop_notify(TX_UUID)
        except OSError:
            pass

    start_us, now_us = meta["start_us"], meta["now_us"]
    if start_us == 0:
        print("No buffered session on device.")
        return
    age_s = ((now_us - start_us) % 2**32) / 1e6
    print(f"session_start_us = {start_us}")
    print(f"device_now_us    = {now_us}")
    print(f"session started  {age_s:.2f} s ago (device clock)")


async def run(device_name: str, out_path: Path | None, command: str | None) -> None:
    print(f"Scanning for '{device_name}*'...")
    # Prefix match — firmware advertises as "SwimLogger-<chipID>"
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: bool(d.name and d.name.startswith(device_name)), timeout=15)
    if device is None:
        print(f"ERROR: no device named '{device_name}*' found. "
              "Is the ESP32 powered on and advertising?")
        return
    print(f"Found: {device.name}")

    row_count = 0

    async with BleakClient(device) as client:
        print(f"Connected to {device.address}")

        if command == "STOP":
            await client.write_gatt_char(RX_UUID, b"STOP\n")
            print("Sent command: STOP")
            return

        if command == "META":
            await fetch_meta(client)
            return

        # START / DUMP / no command → receive samples to CSV
        dump_done = asyncio.Event()

        with open(out_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_us", "angle_counts", "magnet_ok"])

            def on_data(_, data: bytearray) -> None:
                nonlocal row_count
                if len(data) == 1 and data[0] == END_OF_DUMP_MARKER:
                    dump_done.set()
                    return
                if len(data) == 0 or len(data) % SAMPLE_SIZE != 0:
                    return  # META response or other non-sample packet — ignore
                for ts, angle, mag in parse_packet(bytes(data)):
                    writer.writerow([ts, angle, mag])
                    row_count += 1
                if row_count % 50 == 0:
                    print(f"  {row_count} samples logged...", end="\r")

            await client.start_notify(TX_UUID, on_data)

            if command:  # START or DUMP
                await client.write_gatt_char(RX_UUID, (command + "\n").encode())
                print(f"Sent command: {command}")

            print(f"Output: {out_path}")

            if command == "DUMP":
                try:
                    await asyncio.wait_for(dump_done.wait(), timeout=120)
                    print(f"\nEnd-of-dump marker received.")
                except asyncio.TimeoutError:
                    print("\nWARNING: end-of-dump marker not received within 120 s "
                          "— CSV contains whatever arrived.")
            else:
                print("Press Ctrl+C to stop.\n")
                try:
                    await asyncio.Future()   # run until cancelled
                except (asyncio.CancelledError, KeyboardInterrupt):
                    pass

            try:
                await client.stop_notify(TX_UUID)
            except OSError:
                pass  # connection already dropped before cleanup

    print(f"\nStopped. {row_count} rows saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default=DEVICE_NAME,
                        help=f"BLE device name to connect to (default: {DEVICE_NAME})")
    parser.add_argument("--command", choices=["START", "STOP", "META", "DUMP"], default=None,
                        help="Send a command to the ESP32 over BLE. "
                             "START: trigger recording then receive data. "
                             "STOP: stop recording and exit. "
                             "META: print buffered-session metadata and exit. "
                             "DUMP: retrieve the buffered session, exit at end marker.")
    args = parser.parse_args()

    out_path = None
    if args.command not in ("STOP", "META"):
        session_label = input("Enter session label (e.g. tony_warmup): ").strip()
        if not session_label:
            session_label = "session"

        filename = f"swim_{session_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        out_path = Path("raw") / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(run(args.name, out_path, args.command))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
