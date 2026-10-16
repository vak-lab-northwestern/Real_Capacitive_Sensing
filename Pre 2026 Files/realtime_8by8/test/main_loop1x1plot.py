# main_loop2.py (16 MACRO-pipelines, minimal diffs)

import re
import time
from collections import deque

import serial
import matplotlib.pyplot as plt

from grid_manager import GridManager
from calibration_store import load_max_deltas

# -------- CONFIG --------
PORT = "/dev/tty.usbserial-210"
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
    counter = 0
    print("🔥 Opening serial...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)

    grid = GridManager(rows=ROWS, cols=COLS)
    max_peaks = load_max_deltas(CALIB_FILE)

    def get_max_delta(r, c):
        v = max_peaks.get((r, c), 1.0)
        return 1.0 if v <= 0.0 else v

    print("✅ Loaded max deltas:", max_peaks)

    # -------- SELECT WHICH NODE TO PLOT --------
    SELECTED_ROW = 0
    SELECTED_COL = 0

    # ---- Visualization setup: single node live delta plot ----
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(f"Live Delta Plot for Node ({SELECTED_ROW}, {SELECTED_COL})")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Delta Value")

    line, = ax.plot([], [], lw=2)
    ax.set_xlim(0, HISTORY_LEN)
    ax.set_ylim(0, 30000)   # adjust depending on your signal magnitude

    # history for selected node
    selected_history = deque(maxlen=HISTORY_LEN)

    sample_count = 0
    last_plot_time = time.time()
    PLOT_INTERVAL = 0.05   # seconds between redraws (20 FPS)

    try:
        print("🧠 Live loop running. Showing delta value for selected node...\n(CTRL+C to exit)\n")

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

            # process reading through per-cell pipeline
            d, _ = grid._cells[(row,col)].feed(val)

            # ✔ If this is the selected node, store its raw delta
            if row == SELECTED_ROW and col == SELECTED_COL:
                selected_history.append(d)

            # ---- refresh visualization ----
            now = time.time()
            if now - last_plot_time >= PLOT_INTERVAL:
                last_plot_time = now

                y = list(selected_history)
                x = list(range(len(y)))

                line.set_data(x, y)

                # autoscale Y range to fit signal
                if y:
                    ax.set_ylim(min(y) - 100, max(y) + 100)

                ax.set_xlim(0, HISTORY_LEN)
                fig.canvas.draw()
                fig.canvas.flush_events()

            time.sleep(0.0005)

    except KeyboardInterrupt:
        print("\n🛑 Stopping reader...")

    finally:
        ser.close()
        print("✅ Serial closed.")
        plt.ioff()
        plt.show()

if __name__ == "__main__":
    main()


