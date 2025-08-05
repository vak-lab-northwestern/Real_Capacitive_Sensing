import serial
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from collections import deque
import math
import csv
import time
import threading
import tkinter as tk
import re
from tkinter import filedialog

# FDC2214 constants
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)
inductance = 180e-9  # H

def raw_to_capacitance(raw):
    freq = raw * scale_factor
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # picofarads

# Serial setup (adjust port as needed)
ser = serial.Serial("COM8", 115200, timeout=1)

buffer_len = 100
ch = [deque([0.0] * buffer_len) for _ in range(4)]
start_time = time.time()
time_buffer = deque([start_time - (buffer_len - i) * 0.1 for i in range(buffer_len)], maxlen=buffer_len)

# Plot setup
plt.ion()
fig, ax = plt.subplots()
lines = [ax.plot(list(ch[i]), label=f"CH{i}")[0] for i in range(4)]
ax.legend()
ax.set_xlabel("Time (s)")
ax.set_ylabel("Capacitance (pF)")
ax.set_title("Live Capacitance from FDC2214 Channels")
ax.grid(True)

# Logging state (shared)
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

# Initialize logging state
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
        print("[DEBUG] Logging already enabled, ignoring click")
        return

    # Set filename (use a fixed one or prompt user)
    fname = None  # Replace with your fixed path if needed, e.g., "log.csv"
    if not fname:
        fname = choose_output_file()
        if not fname:
            print("[INFO] Logging cancelled (no file selected).")
            return

    try:
        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp", "CH0_pF", "CH1_pF", "CH2_pF", "CH3_pF"])
        csv_file.flush()
        print(f"[INFO] Logging started to {fname}")
    except Exception as e:
        print(f"[ERROR] Could not open file: {e}")
        csv_file = None
        csv_writer = None
        return

    logging_enabled = True
    btn_start.label.set_text("Logging: ON")
    btn_start.color = "lightgreen"
    fig.canvas.draw_idle()
    
def stop_logging(event):
    global logging_enabled, csv_file, csv_writer
    print("[DEBUG] Stop button clicked")
    
    # Always stop logging when button is pressed
    logging_enabled = False
    
    # Reset button states
    btn_start.label.set_text("Start Logging")
    btn_start.color = "0.85"
    fig.canvas.draw_idle()
    
    # Close and cleanup CSV file
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
ax_start = plt.axes([0.7, 0.02, 0.1, 0.05])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.05])
btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")
btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

# Ensure the plot shows up
fig.subplots_adjust(bottom=0.18)
plt.show(block=False)

def serial_worker():
    global logging_enabled, csv_writer, csv_file
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue
            parts = raw_line.split(",")
            if len(parts) != 4:
                continue
            raw_vals = list(map(int, parts))
            caps = [raw_to_capacitance(r) for r in raw_vals]

            # update buffers (only once)
            now = time.time()
            for i in range(4):
                ch[i].append(caps[i])
                ch[i].popleft()
            time_buffer.append(now)

            # logging
            if logging_enabled and csv_writer and csv_file:
                timestamp = now - start_time
                with log_lock:
                    try:
                        csv_writer.writerow([timestamp] + caps)
                        csv_file.flush()
                        print(f"[DEBUG] Wrote data: {timestamp:.2f}s, {caps[0]:.2f}pF")
                    except Exception as e:
                        print(f"[ERROR] Failed to write data: {e}")
                        logging_enabled = False
        except Exception as e:
            print(f"Serial error: {e}")
            continue

# Start serial thread
t = threading.Thread(target=serial_worker, daemon=True)
t.start()

try:
    while True:
        # update plot data
        t_vals = [t - start_time for t in time_buffer]  # seconds since start
        for i in range(4):
            lines[i].set_data(t_vals, list(ch[i]))
        ax.relim()
        ax.autoscale_view()
        fig.canvas.flush_events()
        plt.pause(0.05)  # gives control back to GUI event loop
except KeyboardInterrupt:
    pass
finally:
    if csv_file:
        with log_lock:
            try:
                csv_file.close()
            except Exception:
                pass
    try:
        ser.close()
    except Exception:
        pass
    print("Exiting.")
