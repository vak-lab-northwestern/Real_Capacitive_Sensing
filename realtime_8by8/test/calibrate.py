# calibrate.py (patched for live delta printing)

import re
import time
import serial

from grid_manager import GridManager
from calibration_store import load_max_deltas, save_max_deltas

# -------- CONFIG --------
PORT = "/dev/tty.usbserial-210"
BAUD = 115200
ROWS = 2
COLS = 2
CALIB_FILE = "max_deltas/cell_peaks.json"
CALIB_WINDOW_SEC = 10
# ------------------------

line_re = re.compile(r"\s*(\d+)\s*,\s*Row\s+(\d+)\s*,\s*Col\s+(\d+)\s*:\s*(\d+)")


def parse_line(line: str):
    m = line_re.match(line)
    if not m:
        return None

    # 1 = timestamp
    # 2 = Row
    # 3 = Col
    # 4 = Value
    timestamp = int(m.group(1))  # store in case you want it later
    row = int(m.group(2))
    col = int(m.group(3))
    val = int(m.group(4))

    return row, col, val


def main():
    print("🔥 Opening serial for calibration (with live delta display)...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)

    grid = GridManager(rows=ROWS, cols=COLS)
    existing = load_max_deltas(CALIB_FILE)

    # We're only saving per-node peaks, so we overwrite these
    new_max_deltas = {}

    try:
        for r in range(ROWS):
            for c in range(COLS):
                print("\n===================================")
                print(f"Calibrating cell ({r},{c})")
                print("Press only this node, max will be recorded.")
                print("Hit Enter when ready.")
                input(">> ")

                # reset that cell's state
                grid.reset_cell(r, c)

                print("📡 Streaming... press + hold this node HARD")
                print("(delta values shown live)\n")

                peak = 0.0
                t0 = time.time()

                while time.time() - t0 < CALIB_WINDOW_SEC:
                    raw_line = ser.readline().decode(errors="ignore").strip()
                    if not raw_line:
                        continue

                    parsed = parse_line(raw_line)
                    if parsed is None:
                        continue

                    row, col, val = parsed

                    # Only observe THIS cell for calibration
                    d, touched = grid.feed(row, col, val)

                    # Live delta print when the microcontroller reports this exact cell
                    if row == r and col == c:
                        print(f"🔺 Live Δ = {d:.1f}")

                    if row == r and col == c and d > peak:
                        peak = d

                print(f"\n✅ Peak Δ for cell ({r},{c}) = {peak:.1f}")
                new_max_deltas[(r, c)] = peak

        # save peaks
        save_max_deltas(CALIB_FILE, new_max_deltas)
        print("💾 Saved peaks:", new_max_deltas)

    finally:
        ser.close()
        print("✅ Calibration complete, serial closed.")


if __name__ == "__main__":
    main()
