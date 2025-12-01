# main_loop2.py

import re
import time
from collections import deque

import serial
import matplotlib.pyplot as plt

from grid_manager import GridManager
from calibration_store import load_max_deltas

# -------- CONFIG --------
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200
ROWS = 1
COLS = 4
CALIB_FILE = "max_deltas/cell_peaks.json"

HISTORY_LEN = 200          # how many recent samples we remember per channel
PLOT_EVERY_N_SAMPLES = 4   # refresh viz every N processed samples
LERP_ALPHA = 0.6           # interpolation factor (0–1), higher = snappier
# ------------------------


# Example line: "Row 0, Col 2 : 123456"
line_re = re.compile(r"Row\s+(\d+),\s*Col\s+(\d+)\s*:\s*(\d+)")


def parse_line(line: str):
    m = line_re.match(line)
    if not m:
        return None
    row = int(m.group(1))
    col = int(m.group(2))
    val = int(m.group(3))
    return row, col, val


def main():
    print("🔥 Opening serial...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)  # let board reset

    grid = GridManager(rows=ROWS, cols=COLS)
    max_deltas = load_max_deltas(CALIB_FILE)

    def get_max_delta(r, c):
        v = max_deltas.get((r, c), 1.0)
        return 1.0 if v <= 0.0 else v

    print("✅ Loaded max deltas:", max_deltas)

    # ---- Visualization setup: 1×4 heatmap ----
    plt.ion()
    fig, ax = plt.subplots(figsize=(4, 1))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, COLS)
    ax.set_ylim(0, 1)
    ax.set_title("1×4 Node Intensity (LERP smoothed)")

    squares = []
    for i in range(COLS):
        sq = plt.Rectangle((i, 0), 1, 1)
        ax.add_patch(sq)
        squares.append(sq)

    # histories store the *target* normalized intensities
    histories = [deque(maxlen=HISTORY_LEN) for _ in range(COLS)]
    # display_intensities are what we actually draw (smoothed toward target)
    display_intensities = [0.0 for _ in range(COLS)]

    sample_count = 0

    try:
        print("🧠 Live loop running. Touch nodes to see smoothed intensity.\n(CTRL+C to exit)\n")
        while True:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue

            parsed = parse_line(raw_line)
            if parsed is None:
                continue

            row, col, val = parsed

            # process reading through the per-cell pipeline
            delta, _ = grid.feed(row, col, val)

            # normalize per cell with calibration max
            max_delta = get_max_delta(row, col)
            intensity = delta / max_delta
            if intensity < 0.0:
                intensity = 0.0
            elif intensity > 1.0:
                intensity = 1.0

            # only use row 0, cols 0..3 for now
            if row == 0 and 0 <= col < COLS:
                histories[col].append(intensity)

            sample_count += 1

            # ---- LERP + heatmap refresh ----
            if sample_count % PLOT_EVERY_N_SAMPLES == 0:
                for i in range(COLS):
                    # target = latest normalized reading for this channel
                    target = histories[i][-1] if histories[i] else 0.0
                    current = display_intensities[i]

                    # linear interpolation toward target
                    new_val = current + (target - current) * LERP_ALPHA

                    # clamp to [0, 1] just in case
                    if new_val < 0.0:
                        new_val = 0.0
                    elif new_val > 1.0:
                        new_val = 1.0

                    display_intensities[i] = new_val

                    # grayscale RGBA: same in R,G,B, alpha=1
                    squares[i].set_facecolor((new_val, new_val, new_val, 1.0))

                fig.canvas.draw()
                fig.canvas.flush_events()

            # tiny sleep to keep CPU from pegging at 100%
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n🛑 Stopping live loop...")
    finally:
        ser.close()
        print("✅ Serial closed.")
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()
