# main_loop.py

import re
import time
from collections import deque

import serial
import matplotlib.pyplot as plt

from grid_manager import GridManager
from calibration_store import load_max_deltas

# -------- CONFIG --------
PORT = "/dev/tty.usbmodem21301"
BAUD = 115200
ROWS = 4
COLS = 4
CALIB_FILE = "max_deltas/cell_peaks.json"

# history length per channel
HISTORY_LEN = 300
# how often to refresh plot (in processed samples)
PLOT_EVERY_N_SAMPLES = 4  # e.g. update after each full row scan
# ------------------------


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
    print("Opening serial...")
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2.0)

    grid = GridManager(rows=ROWS, cols=COLS)
    max_deltas = load_max_deltas(CALIB_FILE)

    # fallback: if a cell has no calibration, avoid div-by-zero
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

    # one line per column (assuming single row)
    lines = []
    histories = []
    for ch in range(COLS):
        line, = ax.plot([], [], label=f"Col {ch}")
        lines.append(line)
        histories.append(deque(maxlen=HISTORY_LEN))
    ax.legend(loc="upper right")

    sample_count = 0

    try:
        print("Entering main loop. Ctrl+C to exit.\n")
        while True:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue

            parsed = parse_line(raw_line)
            if parsed is None:
                # print("⛔ Unparsed:", raw_line)
                continue

            row, col, val = parsed

            # process through per-cell pipeline
            delta, touched = grid.feed(row, col, val)

            # normalize using calibration
            max_delta = get_max_delta(row, col)
            normalized = delta / max_delta
            # clamp to [0, 1]
            if normalized < 0.0:
                normalized = 0.0
            elif normalized > 1.0:
                normalized = 1.0

            # For now we assume rows=1 and row==0;
            # map col→channel index
            if row == 0 and 0 <= col < COLS:
                histories[col].append(normalized)

            sample_count += 1

            # --- plot refresh ---
            if sample_count % PLOT_EVERY_N_SAMPLES == 0:
                for ch in range(COLS):
                    y = list(histories[ch])
                    x = list(range(len(y)))
                    lines[ch].set_data(x, y)

                # keep x-limits tight to current history
                max_len = max(len(h) for h in histories)
                ax.set_xlim(0, max(max_len, 1))

                fig.canvas.draw()
                fig.canvas.flush_events()

    except KeyboardInterrupt:
        print("\nStopping main loop...")
    finally:
        ser.close()
        print("Serial closed.")
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()
