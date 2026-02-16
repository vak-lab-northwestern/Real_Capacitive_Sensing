import serial
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from collections import deque
import csv
import time
import threading
import tkinter as tk
from tkinter import filedialog

#  Settings 
serialPort = "/dev/tty.usbserial-110"
baudrate = 115200
channel_num = 16
buffer_len = 10

#  State Variables 
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

#  Serial Setup 
try:
    ser = serial.Serial(serialPort, baudrate=baudrate, timeout=1)
except Exception as e:
    print(f"[ERROR] Could not open serial port: {e}")
    exit()

#  Data Buffers 
start_time = time.time()
time_buffer = deque([start_time - (buffer_len - i) * 0.1 for i in range(buffer_len)], maxlen=buffer_len)
ch = [deque([0.0] * buffer_len, maxlen=buffer_len) for _ in range(channel_num)]

#  Plot Setup 
plt.ion()
# Create a 4x4 grid. sharey=True keeps scales consistent across all nodes.
fig, axes = plt.subplots(4, 4, figsize=(12, 8), sharex=True, sharey=True)
fig.suptitle("4x4 Capacitance Sensor Grid (pF)")

axes_flat = axes.flatten()
lines = []

for i in range(channel_num):
    ax_sub = axes_flat[i]
    line, = ax_sub.plot([], [], label=f"CH{i}", color='tab:blue')
    lines.append(line)
    ax_sub.set_title(f"Node {i}", fontsize=9)
    ax_sub.grid(True, alpha=0.3)

# Adjust layout to make room for buttons at the bottom
plt.tight_layout(rect=[0, 0.1, 1, 0.95])

#  Logging & UI Functions 
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
    if logging_enabled: return
    fname = choose_output_file()
    if not fname: return
    try:
        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp"] + [f"CH{i}_pF" for i in range(channel_num)])
        logging_enabled = True
        btn_start.label.set_text("Logging: ON")
        btn_start.color = "lightgreen"
        print(f"[INFO] Logging to {fname}")
    except Exception as e:
        print(f"[ERROR] {e}")

def stop_logging(event):
    global logging_enabled, csv_file
    logging_enabled = False
    btn_start.label.set_text("Start Logging")
    btn_start.color = "0.85"
    if csv_file:
        with log_lock:
            csv_file.close()
            csv_file = None
        print("[INFO] Logging stopped.")

# --- UI Buttons ---
ax_start = plt.axes([0.35, 0.02, 0.15, 0.05])
ax_stop = plt.axes([0.51, 0.02, 0.15, 0.05])

btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")

btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

# --- Serial Worker ---
def serial_worker():
    global logging_enabled, csv_writer, csv_file
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line: continue
            
            # Expects "val0,val1,val2...val15"
            parts = raw_line.split(",")
            if len(parts) != channel_num: continue

            caps = [float(p) for p in parts]
            now = time.time()

            for i in range(channel_num):
                ch[i].append(caps[i])
            time_buffer.append(now)

            if logging_enabled and csv_file:
                timestamp = now - start_time
                with log_lock:
                    csv_writer.writerow([f"{timestamp:.3f}"] + [f"{c:.4f}" for c in caps])
        except Exception as e:
            print(f"[ERROR] Serial read error: {e}")

# Start Serial Thread
t = threading.Thread(target=serial_worker, daemon=True)
t.start()

# --- Main Plot Loop ---
try:
    while True:
        t_vals = [t - start_time for t in time_buffer]
        for i in range(channel_num):
            lines[i].set_data(t_vals, list(ch[i]))
            
        # Update limits to fit data dynamically
        for ax_sub in axes_flat:
            ax_sub.relim()
            ax_sub.autoscale_view()
        
        fig.canvas.flush_events()
        plt.pause(0.01)
except KeyboardInterrupt:
    pass
finally:
    if csv_file: 
        with log_lock:
            csv_file.close()
    ser.close()
    print("Exiting.")


# output:
# nodes:
# 0 1 2 3
# 4 5 6 7
# 8 9 10 11
# 12 13 14 15