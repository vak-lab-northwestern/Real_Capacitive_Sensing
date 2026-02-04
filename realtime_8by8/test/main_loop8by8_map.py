# main_loop8by8_map.py
import time
from collections import deque

import serial
import matplotlib.pyplot as plt

from cell_pipeline import CellPipeline
from calibration_store import load_max_deltas

# -------- CONFIG --------
PORT = "/dev/tty.usbserial-110"
BAUD = 115200
ROWS = 4
COLS = 4
CALIB_FILE = "max_deltas/cell_peaks.json"

HISTORY_LEN = 200
PLOT_INTERVAL = 0.01  # seconds
LERP_ALPHA = 1.0  # smooth lerp for plot

# Example line: "timestamp, Row X, Col Y : VALUE"
import re
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

    # ---- Initialize grid of CellPipeline ----
    grid = [[CellPipeline() for _ in range(COLS)] for _ in range(ROWS)]

    max_peaks = load_max_deltas(CALIB_FILE)

    def get_max_delta(r, c):
        v = max_peaks.get((r, c), 1.0)
        return 1.0 if v <= 0 else v

    # ---- Visualization setup: 8x8 heatmap ----
    plt.ion()
    fig, ax = plt.subplots(figsize=(COLS, ROWS))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, COLS)
    ax.set_ylim(0, ROWS)
    ax.set_title("8x8 Node Pressure Map Live Demo")

    squares = [[None] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            sq = plt.Rectangle((c, ROWS - 1 - r), 1, 1)
            ax.add_patch(sq)
            squares[r][c] = sq

    # ---- Histories and display ----
    hist = {}
    display = {}
    for r in range(ROWS):
        for c in range(COLS):
            hist[(r, c)] = deque(maxlen=HISTORY_LEN)
            display[(r, c)] = 0.0

    last_plot_time = time.time()

    try:
        print("🧠 Live loop running. Touch nodes to see intensity...\n(CTRL+C to exit)\n")

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

            cell = grid[row][col]
            delta, touched = cell.feed(val)

            if touched:
                # normalize intensity
                print("Row:", row, "Col:", col, "Diff:", delta, "\n")
                md = get_max_delta(row, col)
                intensity = max(0.0, min(delta / md, 1.0))
                hist[(row, col)].append(intensity)
            else:
                hist[(row, col)].append(0.0)  # not touched → fade out

            now = time.time()
            if now - last_plot_time >= PLOT_INTERVAL:
                last_plot_time = now

                for r in range(ROWS):
                    for c in range(COLS):
                        target = hist[(r, c)][-1] if hist[(r, c)] else 0.0
                        cur = display[(r, c)]
                        nv = cur + (target - cur) * LERP_ALPHA
                        nv = max(0.0, min(nv, 1.0))
                        display[(r, c)] = nv
                        squares[r][c].set_facecolor((nv, nv, nv, 1.0))

                fig.canvas.draw()
                fig.canvas.flush_events()

    except KeyboardInterrupt:
        print("\n🛑 Stopping reader...")
    finally:
        ser.close()
        print("✅ Serial closed.")
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()
