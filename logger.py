"""
logger.py
─────────
Captures serial output from as5600_logger.ino and saves to a timestamped CSV.

Usage:
    pip install pyserial
    python logger.py                        # auto-detects port
    python logger.py --port COM3            # Windows
    python logger.py --port /dev/ttyUSB0   # Linux
    python logger.py --port /dev/tty.usbmodem14101  # Mac

Press Ctrl+C to stop recording.
Press 's' during recording to stamp a sync marker (for camera alignment).
  → writes raw/sync_<label>_<datetime>.txt  (one line per marker: index,timestamp_us)
"""

import serial
import serial.tools.list_ports
import csv
import argparse
import msvcrt
from datetime import datetime
from pathlib import Path


def find_arduino_port():
    """Auto-detect the first Arduino-like serial port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if any(kw in (p.description or "").lower() for kw in ["arduino", "ch340", "cp210", "ftdi", "usb serial"]):
            return p.device
    # Fallback: return first available port
    if ports:
        return ports[0].device
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=None, help="Serial port (auto-detect if omitted)")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    port = args.port or find_arduino_port()
    if not port:
        print("ERROR: no serial port found. Plug in Arduino or pass --port.")
        return

    session_label = input("Enter session label (e.g. tony_warmup): ").strip()
    if not session_label:
        session_label = "session"

    stem = f"{session_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_path = Path("raw") / f"swim_{stem}.csv"
    sync_path = Path("raw") / f"sync_{stem}.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Port:   {port} @ {args.baud} baud")
    print(f"Output: {out_path}")
    print("Press 's' to stamp a sync marker. Press Ctrl+C to stop.\n")

    with serial.Serial(port, args.baud, timeout=1) as ser, \
         open(out_path, "w", newline="") as f:

        writer = csv.writer(f)
        writer.writerow(["timestamp_us", "angle_counts", "magnet_ok"])

        row_count = 0
        sync_count = 0
        last_timestamp_us = None
        sync_file = None

        try:
            while True:
                # Non-blocking sync keypress check
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b's':
                        if last_timestamp_us is not None:
                            if sync_file is None:
                                sync_file = open(sync_path, "w")
                            sync_file.write(f"{sync_count},{last_timestamp_us}\n")
                            sync_file.flush()
                            print(f"\n[SYNC #{sync_count} @ {last_timestamp_us} us]")
                            sync_count += 1
                        else:
                            print("\n[SYNC ignored — no data yet]")

                line = ser.readline().decode("utf-8", errors="replace").strip()
                if not line or line.startswith("#"):
                    print(line)          # pass comments through to terminal
                    continue

                parts = line.split(",")
                if len(parts) == 3:
                    writer.writerow(parts)
                    last_timestamp_us = parts[0]
                    row_count += 1
                    if row_count % 50 == 0:
                        print(f"  {row_count} samples logged...", end="\r")

        except KeyboardInterrupt:
            if sync_file:
                sync_file.close()
            print(f"\nStopped. {row_count} rows saved to {out_path}")
            if sync_count:
                print(f"Sync markers: {sync_count} → {sync_path}")


if __name__ == "__main__":
    main()
