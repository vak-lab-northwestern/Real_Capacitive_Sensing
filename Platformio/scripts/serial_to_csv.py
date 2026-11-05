#!/usr/bin/env python3
"""
Log capacitance readings from the serial port to a CSV file.

SERIAL INPUT (one reading per line, newline terminated), either form works:
    row,col,value      e.g.  0,0,39472
    value              e.g.  39472
    value = INTEGER in milli-pF  ->  39472 means 39.472 pF
    Lines that don't match (debug prints, blank lines, '#' comments) are ignored.

CSV OUTPUT columns:
    time_s   seconds since logging started (PC clock)
    row,col  as sent by the firmware (blank if the line had only a value)
    pF       capacitance in pF
    label    whatever you passed with --label (handy for tagging conditions)

    python serial_to_csv.py --port COM5
    python serial_to_csv.py --port COM5 --out touch_test.csv --label touch --seconds 30

Stop with Ctrl+C (or it stops by itself after --seconds).
Close the PlatformIO serial monitor first, or the port will be busy.
"""
import argparse
import csv
import re
import time
from datetime import datetime

import serial

BAUD = 115200            # must match Serial.begin() in the firmware
UNIT = 1000.0            # serial integers are counts of 1/1000 pF (milli-pF)

# "row,col,value" or just "value"
LINE = re.compile(r"^\s*(?:(\d+)\s*,\s*(\d+)\s*,\s*)?(-?\d+)\s*$")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="serial port, e.g. COM5")
    p.add_argument("--out", default=None,
                   help="CSV file to write (default: cap_log_<date>_<time>.csv)")
    p.add_argument("--label", default="", help="text written in every row's label column")
    p.add_argument("--seconds", type=float, default=None, help="stop after this many seconds")
    args = p.parse_args()

    out = args.out or datetime.now().strftime("cap_log_%Y%m%d_%H%M%S.csv")

    ser = serial.Serial(args.port, BAUD, timeout=0.5)
    ser.reset_input_buffer()
    print(f"Logging {args.port} -> {out}  (Ctrl+C to stop)")

    n = 0
    t0 = time.perf_counter()
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "row", "col", "pF", "label"])
        try:
            while args.seconds is None or time.perf_counter() - t0 < args.seconds:
                text = ser.readline().decode(errors="ignore").strip()
                m = LINE.match(text)
                if not m:
                    continue                         # debug print, '#' line, or partial line
                t = time.perf_counter() - t0
                w.writerow([f"{t:.4f}", m[1] or "", m[2] or "", int(m[3]) / UNIT, args.label])
                n += 1
                if n % 100 == 0:
                    f.flush()                        # keep the file current if it crashes
                    print(f"\r{n} readings, last {int(m[3]) / UNIT:.3f} pF", end="")
        except KeyboardInterrupt:
            pass
        finally:
            ser.close()

    print(f"\nSaved {n} readings to {out}")


if __name__ == "__main__":
    main()
