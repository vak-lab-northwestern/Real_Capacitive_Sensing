#!/usr/bin/env python3
import serial
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from collections import deque
import csv
import time
import threading
import tkinter as tk
from tkinter import filedialog

# ===== Configuration =====
serialPort = "/dev/cu.usbserial-0001"  
baudrate = 115200                     
channel_num = 4                       
buffer_len = 100                      
visible_channels = 4

# ===== State Variables =====
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

# ===== Serial Setup =====
try:
    ser = serial.Serial(serialPort, baudrate=baudrate, timeout=1)
    print(f"[INFO] Connected to {serialPort} at {baudrate} baud")
except Exception as e:
    print(f"[ERROR] Could not open serial port: {e}")
    exit()

# ===== Data Buffers (Fixed: Start completely empty) =====
start_time = time.time()
time_buffer = deque(maxlen=buffer_len)
ch = [deque(maxlen=buffer_len) for _ in range(channel_num)]

# ===== Plot Setup (Forced 2x2) =====
fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True, sharey=False)
fig.suptitle("2x2 Capacitance Sensor Grid", fontsize=14, fontweight='bold')

axes_flat = axes.flatten()
lines = []

for i in range(visible_channels):
    ax_sub = axes_flat[i]
    line, = ax_sub.plot([], [], label=f"CH{i}", color='tab:blue', linewidth=2)
    lines.append(line)
    ax_sub.set_title(f"Node {i}", fontsize=11, fontweight='bold')
    ax_sub.grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0.1, 1, 0.93])

# ===== Logging & UI Functions =====
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
        csv_writer.writerow(["timestamp"] + [f"CH{i}_Count" for i in range(channel_num)])
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
ax_start = plt.axes([0.35, 0.02, 0.15, 0.04])
ax_stop = plt.axes([0.52, 0.02, 0.15, 0.04])

btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")

btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

# --- Serial Worker ---
def serial_worker():
    global logging_enabled, csv_writer, csv_file
    ser.reset_input_buffer()
    
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line: continue
            
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
            pass

# Start Serial Thread
t = threading.Thread(target=serial_worker, daemon=True)
t.start()

# --- Main Plot Loop ---
try:
    while plt.fignum_exists(fig.number):
        if len(time_buffer) > 0:
            t_vals = [t - start_time for t in time_buffer]
            
            for i in range(channel_num):
                if len(ch[i]) == len(t_vals):
                    lines[i].set_data(t_vals, list(ch[i]))
            
            # Dynamic scaling fix based on actual values
            for i, ax_sub in enumerate(axes_flat):
                if len(ch[i]) > 0:
                    ax_sub.relim()
                    ax_sub.autoscale_view()
                    
                    # Force vertical padding so data isn't trapped on edges
                    current_data = list(ch[i])
                    ymin, ymax = min(current_data), max(current_data)
                    margin = max(5, (ymax - ymin) * 0.1)
                    ax_sub.set_ylim(ymin - margin, ymax + margin)
                    
                if t_vals:
                    ax_sub.set_xlim(max(0, t_vals[-1] - 8), t_vals[-1] + 0.2)
        
        fig.canvas.flush_events()
        plt.pause(0.02)
except KeyboardInterrupt:
    pass
finally:
    if csv_file: 
        with log_lock:
            csv_file.close()
    ser.close()
    print("\n[INFO] Disconnected successfully.")