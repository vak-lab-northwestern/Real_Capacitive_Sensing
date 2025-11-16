import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from collections import deque
import threading
import time
import csv
import math
import tkinter as tk
from tkinter import filedialog
import sys

# CONFIGURATION
SERIAL_PORT = "COM3"
BAUD_RATE = 115200
NUM_ROWS = 8
NUM_COLS = 8
TOTAL_CHANNELS = NUM_ROWS + NUM_COLS

HISTORY_LENGTH = 200   # number of frames visible

# FDC2214 conversion constants
REF_CLOCK = 40e6
SCALE_FACTOR = REF_CLOCK / (2 ** 28)
INDUCTANCE = 18e-6  # H


def raw_to_cap(raw):
    """Convert 28-bit reading → capacitance in pF."""
    freq = raw * SCALE_FACTOR
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * INDUCTANCE)
    return cap_F * 1e12  # pF


# DATA BUFFERS
row_hist = [deque(maxlen=HISTORY_LENGTH) for _ in range(NUM_ROWS)]
col_hist = [deque(maxlen=HISTORY_LENGTH) for _ in range(NUM_COLS)]
time_hist = deque(maxlen=HISTORY_LENGTH)

start_time = time.time()
frame_count = 0

# SERIAL PORT
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"[INFO] Connected to {SERIAL_PORT}")
except Exception as e:
    print(f"[ERROR] Could not open serial port: {e}")
    sys.exit(1)


# Wait for Arduino header
while True:
    line = ser.readline().decode('utf-8').strip()
    if "ROW0" in line:
        print("[INFO] Header detected, streaming begins")
        break
    if line.startswith("FDC"):
        print(line)

# FIGURE SETUP
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
fig.suptitle("Real-time Capacitance (Rows + Columns)")

# Row subplot
ax1.set_title("Rows (8 channels)")
ax1.set_xlabel("Frame")
ax1.set_ylabel("pF")
ax1.grid(True)

# Column subplot
ax2.set_title("Columns (8 channels)")
ax2.set_xlabel("Frame")
ax2.set_ylabel("pF")
ax2.grid(True)

colors = plt.cm.tab20(np.linspace(0, 1, TOTAL_CHANNELS))
row_lines = []
col_lines = []

for i in range(NUM_ROWS):
    ln, = ax1.plot([], [], color=colors[i], label=f"Row {i}", linewidth=2)
    row_lines.append(ln)

for i in range(NUM_COLS):
    ln, = ax2.plot([], [], color=colors[i + NUM_ROWS], label=f"Col {i}", linewidth=2)
    col_lines.append(ln)

ax1.legend(loc="upper right")
ax2.legend(loc="upper right")

plt.tight_layout()


# CSV LOGGING SYSTEM
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()


def choose_file():
    root = tk.Tk()
    root.withdraw()
    fname = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")]
    )
    root.destroy()
    return fname


def start_logging(event):
    global logging_enabled, csv_file, csv_writer

    if logging_enabled:
        print("[INFO] Logging already running.")
        return

    fname = choose_file()
    if not fname:
        print("[INFO] Logging canceled.")
        return

    try:
        csv_file = open(fname, "w", newline="")
        csv_writer = csv.writer(csv_file)
        header = ["timestamp"] + \
                 [f"ROW{i}_pF" for i in range(NUM_ROWS)] + \
                 [f"COL{i}_pF" for i in range(NUM_COLS)]
        csv_writer.writerow(header)
        csv_file.flush()

        logging_enabled = True
        print(f"[INFO] Logging started → {fname}")
        btn_start.label.set_text("Logging: ON")
        btn_start.color = "lightgreen"
        fig.canvas.draw_idle()
    except Exception as e:
        print(f"[ERROR] Could not open CSV file: {e}")


def stop_logging(event):
    global logging_enabled, csv_file

    logging_enabled = False
    btn_start.label.set_text("Start Logging")
    btn_start.color = "0.85"
    fig.canvas.draw_idle()

    if csv_file:
        with log_lock:
            try:
                csv_file.flush()
                csv_file.close()
                print("[INFO] Logging stopped & file closed.")
            except:
                pass
        csv_file = None


# Buttons
ax_start = plt.axes([0.7, 0.02, 0.1, 0.05])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.05])

btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")

btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)


# SERIAL READER THREAD (NON-BLOCKING)
def serial_thread():
    global frame_count

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            parts = line.split(",")
            if len(parts) != TOTAL_CHANNELS:
                continue

            # Convert all 16 to integers
            raw_vals = []
            try:
                raw_vals = [int(x) for x in parts]
            except:
                continue

            # raw → pF
            pf_vals = [raw_to_cap(v) for v in raw_vals]

            row_vals = pf_vals[:NUM_ROWS]
            col_vals = pf_vals[NUM_ROWS:]

            now = time.time() - start_time
            time_hist.append(now)

            for i in range(NUM_ROWS):
                row_hist[i].append(row_vals[i])

            for i in range(NUM_COLS):
                col_hist[i].append(col_vals[i])

            frame_count += 1

            # CSV LOGGING
            if logging_enabled and csv_writer:
                with log_lock:
                    csv_writer.writerow(
                        [now] +
                        row_vals +
                        col_vals
                    )
                    csv_file.flush()

        except Exception as e:
            print(f"[ERROR] serial thread: {e}")


reader = threading.Thread(target=serial_thread, daemon=True)
reader.start()


# MATPLOTLIB UPDATE FUNCTION
def update(frame):
    # Update rows
    for i in range(NUM_ROWS):
        if len(row_hist[i]) > 0:
            x = range(len(row_hist[i]))
            row_lines[i].set_data(x, list(row_hist[i]))

    # Update columns
    for i in range(NUM_COLS):
        if len(col_hist[i]) > 0:
            x = range(len(col_hist[i]))
            col_lines[i].set_data(x, list(col_hist[i]))

    # Autoscale Y
    ax1.relim(); ax1.autoscale_view()
    ax2.relim(); ax2.autoscale_view()

    # Scroll X
    max_len = max(len(time_hist), 1)
    ax1.set_xlim(max(0, max_len - HISTORY_LENGTH), max_len)
    ax2.set_xlim(max(0, max_len - HISTORY_LENGTH), max_len)

    fig.suptitle(f"Real-time Capacitance — Frame {frame_count}")

    return row_lines + col_lines


ani = FuncAnimation(fig, update, interval=50, blit=False)

print("[INFO] Live plotting started.")
plt.show()

ser.close()
print("[INFO] Serial closed.")
