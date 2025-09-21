import serial
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from collections import deque
import math
import csv
import time
import threading
import os

# Settings
serialPort = "/dev/cu.usbmodem2101"
baudrate = 115200
channel_num = 4

# Calibration constants 
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)
inductance = 18e-6  # H (your actual coil)
C_FIXED = 14.63e-12      # Short the two wires to find C_Fixed

# Conversion functions 
def raw_to_frequency(raw):
    return raw * scale_factor

def frequency_to_total_capacitance(freq_hz):
    return 1.0 / ((2 * math.pi * freq_hz) ** 2 * inductance)

def calibrate_c_fixed(raw_short):
    """Compute fixed parallel capacitance from shorted-plate reading."""
    freq_short = raw_to_frequency(raw_short)
    return frequency_to_total_capacitance(freq_short)

def raw_to_sensor_capacitance(raw):
    """Convert raw data to sensor capacitance (pF) using calibrated C_FIXED."""
    global C_FIXED
    freq = raw_to_frequency(raw)
    if freq <= 0:
        return 0.0
    c_total = frequency_to_total_capacitance(freq)
    c_sense = c_total - C_FIXED
    return c_sense * 1e12  # pF

# Serial setup
print("[INFO] Connecting to Arduino...")
try:
    ser = serial.Serial(serialPort, baudrate=baudrate, timeout=1)
    print(f"[INFO] Connected to {ser.name}")
except Exception as e:
    print(f"[ERROR] Failed to connect: {e}")
    exit(1)

# Data buffers
buffer_len = 100
start_time = time.time()
time_buffer = deque([start_time - (buffer_len - i) * 0.1 for i in range(buffer_len)], maxlen=buffer_len)
ch = [deque([0.0] * buffer_len, maxlen=buffer_len) for _ in range(channel_num)]

# Plot setup
plt.ion()
fig, ax = plt.subplots(figsize=(15, 8))
lines = [ax.plot(list(ch[i]), label=f"CH{i}")[0] for i in range(channel_num)]
ax.legend()
ax.set_xlabel("Time (s)")
ax.set_ylabel("Δ Capacitance (pF)")
ax.set_title("Live Δ Capacitance from 4 Channel")
ax.grid(True)

# Logging state
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

print("[INFO] GUI initialized. Click 'Start Logging' to begin data collection.")

def start_logging(event):
    global logging_enabled, csv_file, csv_writer
    print("[DEBUG] Start button clicked")
    
    if logging_enabled:
        print("[DEBUG] Already logging")
        return
    
    # Use fixed filename to avoid Tkinter conflicts
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    fname = f"differential_capacitance_{timestamp}_dipcoated_nozzle_node7.csv"
    
    try:
        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        header = ["timestamp"] + [f"CH{i}_pF" for i in range(channel_num)]
        csv_writer.writerow(header)
        csv_file.flush()
        
        logging_enabled = True
        btn_start.label.set_text("Logging: ON")
        btn_start.color = "lightgreen"
        fig.canvas.draw_idle()
        
        print(f"[INFO] Logging started to {fname}")
        
    except Exception as e:
        print(f"[ERROR] Could not open file: {e}")
        csv_file = None
        csv_writer = None
        logging_enabled = False

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

# Create buttons
ax_start = plt.axes([0.7, 0.02, 0.1, 0.05])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.05])
btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")
btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

fig.subplots_adjust(bottom=0.18)
plt.show(block=False)

# Data collection thread
def serial_worker():
    global logging_enabled, csv_writer, csv_file
    print("[INFO] Serial worker started")
    
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue
                
            parts = raw_line.split(",")
            if len(parts) != channel_num:
                print(f"[DEBUG] Skipping line: expecting {channel_num} parts, got {len(parts)}")
                continue

            raw_vals = list(map(int, parts))
            caps = [raw_to_sensor_capacitance(r) for r in raw_vals]
            now = time.time()

            # Update buffers
            for i in range(channel_num):
                ch[i].append(caps[i])
            time_buffer.append(now)
            
            # Log data
            if logging_enabled and csv_writer and csv_file:
                timestamp = now - start_time
                with log_lock:
                    try:
                        csv_writer.writerow([f"{timestamp:.3f}"] + [f"{c:.6f}" for c in caps])
                        csv_file.flush()
                        print(f"[DEBUG] Logged: {timestamp:.3f}s, CH0: {caps[0]:.2f}pF")
                    except Exception as e:
                        print(f"[ERROR] Failed to write data: {e}")
                        logging_enabled = False
                        
        except Exception as e:
            print(f"[ERROR] Serial read error: {e}")
            continue

# Start worker thread
worker_thread = threading.Thread(target=serial_worker, daemon=True)
worker_thread.start()

# Main GUI loop
try:
    while True:
        # Update plot
        t_vals = [t - start_time for t in time_buffer]
        for i in range(channel_num):
            lines[i].set_data(t_vals, list(ch[i]))
        ax.relim()
        ax.autoscale_view()
        fig.canvas.flush_events()
        plt.pause(0.05)
        
except KeyboardInterrupt:
    print("\n[INFO] Shutting down...")
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
    print("[INFO] Cleanup complete.")
