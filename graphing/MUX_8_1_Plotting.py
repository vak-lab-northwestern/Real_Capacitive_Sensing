import serial
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from collections import deque
import math
import csv
import time
import threading
import tkinter as tk
from tkinter import filedialog

# FDC2214 constants
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)
inductance = 18e-6  # H
SERIAL_PORT = "COM13"
BAUD_RATE = 115200

# Number of channels: MUX1_0-7 + MUX2_0-7
channel_num = 8

# Channel labels matching Arduino output
channel_labels = [
    "MUX1_0", "MUX1_1", "MUX1_2", "MUX1_3", "MUX1_4", "MUX1_5", "MUX1_6", "MUX1_7",
    "MUX2_0", "MUX2_1", "MUX2_2", "MUX2_3", "MUX2_4", "MUX2_5", "MUX2_6", "MUX2_7"
]

def raw_to_capacitance(raw):
    freq = raw * scale_factor
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # picofarads

# Serial setup
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

buffer_len = 100
start_time = time.time()
time_buffer = deque(maxlen=buffer_len)
ch = [deque(maxlen=buffer_len) for _ in range(channel_num)]

# Plot setup - split into 2 subplots for better visibility
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))   
fig.subplots_adjust(bottom=0.1, hspace=0.3)

# Create lines for MUX1 (top plot) and MUX2 (bottom plot)
lines1 = [ax1.plot([], [], label=channel_labels[i])[0] for i in range(8)]
lines2 = [ax2.plot([], [], label=channel_labels[i+8])[0] for i in range(8)]
lines = lines1 + lines2

ax1.legend(loc='upper right', ncol=4, fontsize=8)
ax1.set_xlabel("Time (s)")
ax1.set_ylabel("Capacitance (pF)")
ax1.set_title("MUX1 Channels (FDC CH0: 8:1 multiplexer)")
ax1.grid(True)

ax2.legend(loc='upper right', ncol=4, fontsize=8)
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("Capacitance (pF)")
ax2.set_title("MUX2 Channels (FDC CH1: 8:1 multiplexer)")
ax2.grid(True)

# Logging state
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

print("[INFO] Logging system initialized. Click 'Start Logging' to begin data collection.")

def choose_output_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Select CSV file to log to"
    )
    root.destroy()
    return file_path

def start_logging(event):
    global logging_enabled, csv_file, csv_writer
    print("[DEBUG] Start button clicked")

    if logging_enabled:
        print("[DEBUG] Logging already enabled")
        return

    fname = choose_output_file()
    if not fname:
        print("[INFO] Logging cancelled (no file selected).")
        return

    try:
        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        # Write header with proper channel names
        csv_writer.writerow(["timestamp"] + [f"{label}_pF" for label in channel_labels])
        csv_file.flush()
        print(f"[INFO] Logging started to {fname}")
    except Exception as e:
        print(f"[ERROR] Could not open file: {e}")
        return

    logging_enabled = True
    btn_start.label.set_text("Logging: ON")
    btn_start.color = "lightgreen"
    fig.canvas.draw_idle()

def stop_logging(event):
    global logging_enabled, csv_file, csv_writer
    print("[DEBUG] Stop button clicked")

    logging_enabled = False
    btn_start.label.set_text("Start Logging")
    btn_start.color = "0.85"
    fig.canvas.draw_idle()

    if csv_file:
        with log_lock:
            try:
                csv_file.flush()
                csv_file.close()
                print("[INFO] Logging stopped and file closed.")
            except Exception as e:
                print(f"[ERROR] Error closing file: {e}")
        csv_file = None
        csv_writer = None
    else:
        print("[INFO] Logging stopped (no file was open)")

# Buttons
ax_start = plt.axes([0.7, 0.02, 0.1, 0.04])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.04])
btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")
btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

plt.show(block=False)
plt.draw()

# Serial reading thread
def serial_worker():
    global logging_enabled, csv_writer, csv_file, start_time

    print("[INFO] Serial worker started, waiting for data...")

    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue

            # Skip Arduino info/header lines
            if any(word in raw_line for word in ["Starting", "Format:", "Scan rate", "FDC", "OK"]):
                print(f"[INFO] Arduino message: {raw_line}")
                continue

            # Remove trailing comma and split
            parts = [p.strip() for p in raw_line.rstrip(',').split(",")]
            parts = [p for p in parts if p]

            if len(parts) != channel_num:
                print(f"[WARNING] Expected {channel_num} values, got {len(parts)}: {raw_line[:100]}")
                continue

            try:
                raw_vals = [int(p) for p in parts]
            except ValueError as e:
                print(f"[ERROR] Non-numeric data encountered: {raw_line[:100]}")
                continue

            # Convert raw values to capacitance
            caps = [raw_to_capacitance(r) for r in raw_vals]

            # Update buffers
            now = time.time()
            elapsed = now - start_time
            time_buffer.append(elapsed)

            for i in range(channel_num):
                ch[i].append(caps[i])

            # Logging
            if logging_enabled and csv_writer and csv_file:
                with log_lock:
                    try:
                        csv_writer.writerow([elapsed] + caps)
                        csv_file.flush()
                    except Exception as e:
                        print(f"[ERROR] Failed to write data: {e}")
                        logging_enabled = False

        except Exception as e:
            print(f"[ERROR] Serial error: {e}")
            continue

# Start serial thread
t = threading.Thread(target=serial_worker, daemon=True)
t.start()

print("[INFO] Starting plot loop...")

# Live plot update loop
try:
    while True:
        t_vals = list(time_buffer)

        # Update MUX1 channels (0-7) on top plot
        for i in range(8):
            lines1[i].set_data(t_vals, list(ch[i]))

        # Update MUX2 channels (8-15) on bottom plot
        for i in range(8):
            lines2[i].set_data(t_vals, list(ch[i+8]))

        # Auto-scale both axes
        if len(t_vals) > 0:
            ax1.relim()
            ax1.autoscale_view()
            ax2.relim()
            ax2.autoscale_view()

        fig.canvas.draw_idle()
        fig.canvas.flush_events()
        plt.pause(0.1)

except KeyboardInterrupt:
    print("\n[INFO] Interrupted by user")

finally:
    if csv_file:
        with log_lock:
            try:
                csv_file.close()
                print("[INFO] CSV file closed")
            except Exception:
                pass

    try:
        ser.close()
        print("[INFO] Serial port closed")
    except:
        pass

    print("[INFO] Exiting.")