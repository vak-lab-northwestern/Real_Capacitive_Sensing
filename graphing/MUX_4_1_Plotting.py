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
channel_num = 8  # Changed from 4 to 8
  
def raw_to_capacitance(raw):
    freq = raw * scale_factor
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # picofarads

# Serial setup (adjust port as needed)
ser = serial.Serial("COM13", 115200, timeout=1)

buffer_len = 100
start_time = time.time()
time_buffer = deque(maxlen=buffer_len)
ch = [deque(maxlen=buffer_len) for _ in range(channel_num)]
    
# Plot setup
plt.ion()
fig, ax = plt.subplots(figsize=(10, 6))
fig.subplots_adjust(bottom=0.15)

# Create lines with labels matching your mux configuration
mux_labels = [
    "MUX1_0", "MUX1_1", "MUX1_2", "MUX1_3",
    "MUX2_0", "MUX2_1", "MUX2_2", "MUX2_3"
]
lines = [ax.plot([], [], label=mux_labels[i])[0] for i in range(channel_num)]
ax.legend(loc='upper right')
ax.set_xlabel("Time (s)")
ax.set_ylabel("Capacitance (pF)")
ax.set_title("Live Capacitance from FDC2214 Channels (2x 4:1 MUX)")
ax.grid(True)

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
        print("[DEBUG] Logging already enabled, ignoring click")
        return

    fname = choose_output_file()
    if not fname:
        print("[INFO] Logging cancelled (no file selected).")
        return

    try:
        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        # Updated header for 8 channels
        csv_writer.writerow(["timestamp"] + [f"{mux_labels[i]}_pF" for i in range(channel_num)])
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
ax_start = plt.axes([0.7, 0.02, 0.1, 0.05])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.05])
btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")
btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

plt.show(block=False)
plt.draw()

def serial_worker():
    global logging_enabled, csv_writer, csv_file, start_time
    
    print("[INFO] Serial worker started, waiting for data...")
    
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue
            
            # Print raw line for debugging
            # print(f"[DEBUG] Raw line: {raw_line}")
            
            # Remove trailing comma and split
            parts = [p.strip() for p in raw_line.rstrip(',').split(",")]
            
            # Filter out empty strings
            parts = [p for p in parts if p]
            
            if len(parts) != channel_num:
                print(f"[WARNING] Expected {channel_num} values, got {len(parts)}: {parts}")
                continue

            raw_vals = [int(p) for p in parts]
            caps = [raw_to_capacitance(r) for r in raw_vals]
            
            # print(f"[DEBUG] Capacitances: {[f'{c:.2f}' for c in caps]} pF")

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
                        
        except ValueError as e:
            print(f"[ERROR] Parse error: {e} - Line: {raw_line}")
            continue
        except Exception as e:
            print(f"[ERROR] Serial error: {e}")
            continue

# Start serial thread
t = threading.Thread(target=serial_worker, daemon=True)
t.start()

print("[INFO] Starting plot loop...")

try:
    while True:
        # Update plot data
        t_vals = list(time_buffer)
        
        for i in range(channel_num):
            lines[i].set_data(t_vals, list(ch[i]))
        
        # Auto-scale axes
        if len(t_vals) > 0 and any(len(ch[i]) > 0 for i in range(channel_num)):
            ax.relim()
            ax.autoscale_view()
        
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
    except Exception:
        pass
    print("[INFO] Exiting.")