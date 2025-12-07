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
ROWS = 8   
COLS = 8   
CALIB_FILE = "max_deltas/cell_peaks.json"

HISTORY_LEN = 200
PLOT_EVERY_N_SAMPLES = 4
LERP_ALPHA = 1
# ------------------------

# Example line: "Row 0, Col 2 : 123456"
# ✅ We now allow ANY row/col 0–3 without regex rewrite
# line_re = re.compile(r"Row\s+(\d+),\s*Col\s+(\d+)\s*:\s*(\d+)")
# line_re = re.compile(r"([\d:.]+),\s*(\d+),\s*(\d+),\s*(\d+)")
line_re = re.compile(r"\s*(\d+)\s*,\s*Row\s+(\d+)\s*,\s*Col\s+(\d+)\s*:\s*(\d+)")


# def parse_line(line: str):
#     m = line_re.match(line)
#     if not m:
#         return None
#     row = int(m.group(1))
#     col = int(m.group(2))
#     val = int(m.group(3))
#     return row, col, val

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


# def parse_line(line: str):
#     m = line_re.match(line)
#     if not m:
#         return None

#     # NEW CAPTURE GROUPS:
#     # 1 = timestamp
#     # 2 = row
#     # 3 = col
#     # 4 = val
#     row = int(m.group(2))
#     col = int(m.group(3))
#     val = int(m.group(4))
    
#     return row, col, val


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

    # ---- Visualization setup: 4×4 heatmap ----
    plt.ion()
    fig, ax = plt.subplots(figsize=(COLS, ROWS))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, COLS)
    ax.set_ylim(0, ROWS)
    ax.set_title("8x8 Node Pressure Map Live Demo")

    # ✅ We now create a 4×4 grid of squares
    squares = [[None]*COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            sq = plt.Rectangle((c, ROWS-1-r), 1, 1)
            ax.add_patch(sq)
            squares[r][c] = sq

    # ✅ 4×4 independent histories
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

            # ✅ Ensure we now allow all rows 0–3, cols 0–3
            if not (0 <= row < ROWS and 0 <= col < COLS):
                continue

            # process reading through per-cell pipeline
            d, _ = grid._cells[(row,col)].feed(val)

            # normalize per cell
            md = get_max_delta(row, col)
            intensity = d / md
            if intensity < 0.0:
                intensity = 0.0
            elif intensity > 1.0:
                intensity = 1.0

            # ✅ Independent storage for 16 nodes
            hist[(row,col)].append(intensity)
            sample_count += 1

            # ---- refresh visualization ----
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

                        # ✅ Set grayscale color just like before but now 2D
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
        plt.show()

if __name__ == "__main__":
    main()
