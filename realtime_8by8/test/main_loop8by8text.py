import re
import time
from collections import deque

import serial

from grid_manager import GridManager
from calibration_store import load_max_deltas

# -------- CONFIG --------
PORT = "/dev/tty.usbserial-210"
BAUD = 115200
ROWS = 8
COLS = 8
CALIB_FILE = "max_deltas/cell_peaks.json"

OUTPUT_FILE = "delta_matrices.txt"
# ------------------------

line_re = re.compile(r"\s*(\d+)\s*,\s*Row\s+(\d+)\s*,\s*Col\s+(\d+)\s*:\s*(\d+)")


def parse_line(line: str):
    m = line_re.match(line)
    if not m:
        return None
    timestamp = int(m.group(1))
    row = int(m.group(2))
    col = int(m.group(3))
    val = int(m.group(4))
    return row, col, val


def main():
    print("🔥 Opening serial...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)

    grid = GridManager(rows=ROWS, cols=COLS)
    max_peaks = load_max_deltas(CALIB_FILE)

    def get_max_delta(r, c):
        v = max_peaks.get((r, c), 1.0)
        return 1.0 if v <= 0.0 else v

    print("✅ Loaded max deltas")

    # -----------------------------------------
    # NEW: Initialize an empty 8×8 delta matrix
    # -----------------------------------------
    delta_matrix = [[0.0 for _ in range(COLS)] for _ in range(ROWS)]

    try:
        print("🧠 Running... saving delta matrices to file.\n")

        while True:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue

            parsed = parse_line(raw_line)
            if parsed is None:
                continue

            row, col, val = parsed

            if not (0 <= row < ROWS and 0 <= col < COLS):
                continue

            # Compute delta for this cell
            d, _ = grid._cells[(row, col)].feed(val)

            # Store raw delta in matrix
            delta_matrix[row][col] = d

            # Detect end of full frame
            if row == ROWS - 1 and col == COLS - 1:
                # ------------------------------
                # Write delta matrix to file
                # ------------------------------
                with open(OUTPUT_FILE, "a") as f:
                    for r in range(ROWS):
                        line = " ".join(f"{delta_matrix[r][c]:.2f}" for c in range(COLS))
                        f.write(line + "\n")
                    f.write("\n")  # blank line between frames

                print("📁 Saved one delta matrix.")

                # Optionally reset matrix here (not required)
                # delta_matrix = [[0.0 for _ in range(COLS)] for _ in range(ROWS)]

            time.sleep(0.0005)

    except KeyboardInterrupt:
        print("\n🛑 Stopping reader...")

    finally:
        ser.close()
        print("✅ Serial closed.")


if __name__ == "__main__":
    main()
