# main_loop2.py (16 MACRO-pipelines, minimal diffs)

import re
import time
from collections import deque

import serial
import matplotlib.pyplot as plt

from grid_manager import GridManager
from calibration_store import load_max_deltas

# -------- CONFIG --------
PORT = "/dev/tty.usbserial-10"
BAUD = 115200
ROWS = 2   # ✅ 2 rows
COLS = 2   # ✅ 2 cols
CALIB_FILE = "max_deltas/cell_peaks.json"

HISTORY_LEN = 200
PLOT_EVERY_N_SAMPLES = 4
LERP_ALPHA = 1
# ------------------------

# ❗ Old regex not needed, but we keep it for reference
# line_re = re.compile(r"Row\s+(\d+),\s*Col\s+(\d+)\s*:\s*(\d+)")

def parse_line(line: str):
    # ✅ NEW FORMAT: timestamp,row,col,val
    parts = line.split(",")
    if len(parts) != 4:
        return None
    
    try:
        ts = parts[0].strip()  # keep timestamp if you want it later
        row = int(parts[1])
        col = int(parts[2])
        val = int(parts[3])
        return row, col, val
    except:
        return None

def main():
    print("🔥 Opening serial...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)

    grid = GridManager(rows=ROWS, cols=COLS)
    max_peaks = load_max_deltas(CALIB_FILE)

    def get_max_delta(r, c):
        v = max_peaks.get((r, c), 1.0)
        return 1.0 if v <= 0.0 else v

    print("✅ Loaded max deltas:", max_peaks)

    # ---- Visualization setup: 2×2 heatmap (LERP smoothed) ----
    plt.ion()
    fig, ax = plt.subplots(figsize=(COLS, ROWS))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, COLS)
    ax.set_ylim(0, ROWS)
    ax.set_title("2×2 Node Intensity (LERP smoothed)")

    # ✅ Create 2×2 grid of squares just like before
    squares = [[None]*COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            sq = plt.Rectangle((c, ROWS-1-r), 1, 1)
            ax.add_patch(sq)
            squares[r][c] = sq

    # ✅ 4 independent histories for the 2×2 grid
    hist = {}
    display = {}
    for r in range(ROWS):
        for c in range(COLS):
            hist[(r,c)] = deque(maxlen=HISTORY_LEN)
            display[(r,c)] = 0.0

    sample_count = 0

    try:
        print("🧠 Live loop running. Touch nodes to see smoothed intensity...\n(CTRL+C to exit)\n")
        while True:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue

            parsed = parse_line(raw_line)
            if parsed is None:
                continue

            row, col, val = parsed

            # ✅ Bounds check unchanged
            if not (0 <= row < ROWS and 0 <= col < COLS):
                continue

            # ✅ Feed into existing per-cell pipeline
            d, _ = grid._cells[(row,col)].feed(val)

            # ✅ Normalize per cell peak delta
            md = get_max_delta(row, col)
            intensity = d / md
            if intensity < 0.0:
                intensity = 0.0
            elif intensity > 1.0:
                intensity = 1.0

            # ✅ Store intensity history (unchanged)
            hist[(row,col)].append(intensity)
            sample_count += 1

            # ✅ Refresh viz using LERP exactly like before
            if sample_count % PLOT_EVERY_N_SAMPLES == 0:
                for r in range(ROWS):
                    for c in range(COLS):
                        if not hist[(r,c)]:
                            continue
                        target = hist[(r,c)][-1]
                        cur = display[(r,c)]
                        nv = cur + (target - cur) * LERP_ALPHA
                        if nv < 0.0:
                            nv = 0.0
                        elif nv > 1.0:
                            nv = 1.0
                        display[(r,c)] = nv

                        # ✅ Set grayscale color exactly like before
                        squares[r][c].set_facecolor((nv, nv, nv, 1.0))

                fig.canvas.draw()
                fig.canvas.flush_events()

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n🛑 Stopping reader...")
    finally:
        ser.close()
        print("✅ Serial closed.")
        plt.ioff()
        plt.ioff()
        plt.show()

if __name__ == "__main__":
    main()

