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
from cmcrameri import cm


# Settings
serialPort = "/dev/cu.usbserial-210"
baudrate = 115200
channel_num = 8
channel_title = "Live Capacitance from 8 Channels" 

#  Calibration constants 
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)   
inductance = 18e-6  # H (your actual coil)
C_FIXED = 14.63e-12      # Short the two wires to find C_Fixed

#  Conversion functions 
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

for i in range(channel_num):
    if channel_num == 1:
        channel_title = f"Live Capacitance from {i+1} Channel"
    else:
        channel_title = f"Live Capacitance from {i+1} Channels"


# Serial setup
ser = serial.Serial(serialPort, baudrate=baudrate, timeout=1)


buffer_len = 100
start_time = time.time()
time_buffer = deque([start_time - (buffer_len - i) * 0.1 for i in range(buffer_len)], maxlen=buffer_len)
ch = [deque([0.0] * buffer_len, maxlen=buffer_len) for _ in range(channel_num)]

# Plot setup
plt.ion()
fig, ax = plt.subplots()
lines = [ax.plot(list(ch[i]), label=f"CH{i+1}")[0] for i in range(channel_num)]
ax.legend()
ax.set_xlabel("Time (s)")
ax.set_ylabel("Δ Capacitance (pF)")
ax.set_title(channel_title) 
ax.grid(True)

# Logging state 
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

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
    if logging_enabled:
        print("[DEBUG] Logging already enabled.")
        return

    fname = choose_output_file()
    if not fname:
        print("[INFO] Logging cancelled.")
        return

    try:
        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp"] + [f"CH{i}_pF" for i in range(channel_num)])
        csv_file.flush()
        logging_enabled = True
        btn_start.label.set_text("Logging: ON")
        btn_start.color = "lightgreen"
        btn_start.hovercolor = "lightgreen"
        fig.canvas.draw_idle()
        print(f"[INFO] Logging started to {fname}")
    except Exception as e:
        print(f"[ERROR] Could not open file: {e}")

def stop_logging(event):
    global logging_enabled, csv_file, csv_writer
    if not logging_enabled:
        print("[DEBUG] Logging is not enabled, ignoring stop.")
        return
    logging_enabled = False
    btn_start.label.set_text("Start Logging")
    btn_start.color = "0.85"
    btn_start.hovercolor = "0.85"
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

# Buttons
ax_start = plt.axes([0.7, 0.02, 0.1, 0.05])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.05])
btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")
btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

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
            # if len(parts) != channel_num:
            #     print(f"[DEBUG] Skipping line: expecting {channel_num} parts, got {len(parts)}")
            #     continue

            raw_vals = list(map(int, parts))
            caps = [raw_to_sensor_capacitance(r) for r in raw_vals]
            now = time.time()

            # update buffers once per reading
            for i in range(channel_num):
                ch[i].append(caps[i])
            time_buffer.append(now)

            # logging
            if logging_enabled and csv_writer and csv_file:
                timestamp = now - start_time
                with log_lock:
                    try:
                        csv_writer.writerow([f"{timestamp:.3f}"] + [f"{c:.6f}" for c in caps])
                        csv_file.flush()
                        print(f"[DEBUG] Logged: {timestamp:.3f}s, {caps}")
                    except Exception as e:
                        print(f"[ERROR] Failed to write data: {e}")
                        logging_enabled = False
        except Exception as e:
            print(f"[ERROR] Serial read error: {e}")
            continue

# Start serial thread
t = threading.Thread(target=serial_worker, daemon=True)
t.start()

try:
    while True:
        t_vals = [t - start_time for t in time_buffer]
        for i in range(channel_num):
            lines[i].set_data(t_vals, list(ch[i]))
        ax.relim()
        ax.autoscale_view()
        fig.canvas.flush_events()
        plt.pause(0.05)
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
