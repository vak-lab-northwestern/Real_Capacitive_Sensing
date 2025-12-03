# main_loop.py (16 MACRO-pipelines, minimal diffs)

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
ROWS = 2
COLS = 2
CALIB_FILE = "max_deltas/cell_peaks.json"

HISTORY_LEN = 300
PLOT_EVERY_N_SAMPLES = 4
# ------------------------

# line_re = re.compile(r"Row\s+(\d+),\s*Col\s+(\d+)\s*:\s*(\d+)")
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

def main():
    print("Opening serial...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)

    grid = GridManager(rows=ROWS, cols=COLS)
    max_deltas = load_max_deltas(CALIB_FILE)

    def get_max_delta(r, c):
        val = max_deltas.get((r, c), 1.0)
        if val <= 0.0:
            return 1.0
        return val

    print("Loaded max deltas:", max_deltas)

    # --- setup plotting ---
    plt.ion()
    fig, ax = plt.subplots()
    ax.set_xlabel("Sample index")
    ax.set_ylabel("Normalized Δ")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("4-channel normalized touch strength")

    # CHANGE -> 16 lines instead of 4 (row-major flattening)
    lines = []
    histories = []
    for i in range(ROWS * COLS):  # 16 pipelines total
        line, = ax.plot([], [], label=f"Cell {i}")
        lines.append(line)
        histories.append(deque(maxlen=HISTORY_LEN))

    ax.legend(loc="upper right", ncol=4, fontsize=6)

    sample_count = 0

    try:
        print("Entering main loop. Ctrl+C to exit.\n")
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

            # process through per-cell pipeline
            cell = grid._cells[(row, col)]
            delta, touched = cell.feed(val)

            # SAME normalization, no change
            max_delta = get_max_delta(row, col)
            normalized = delta / max_delta
            if normalized < 0.0:
                normalized = 0.0
            elif normalized > 1.0:
                normalized = 1.0

            # CHANGE -> store in 16-channel array, not col-only
            flat_index = row * COLS + col
            histories[flat_index].append(normalized)

            sample_count += 1

            # SAME redraw cadence, no destruction
            if sample_count % PLOT_EVERY_N_SAMPLES == 0:
                for i in range(ROWS * COLS):
                    if not histories[i]:
                        continue
                    y = list(histories[i])
                    x = list(range(len(y)))
                    lines[i].set_data(x, y)

                max_len = max(len(h) for h in histories)
                ax.set_xlim(0, max_len)

                fig.canvas.draw()
                fig.canvas.flush_events()

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nStopping main loop...")
    finally:
        ser.close()
        print("Serial closed.")
        plt.ioff()
        plt.show()

if __name__ == "__main__":
    main()
