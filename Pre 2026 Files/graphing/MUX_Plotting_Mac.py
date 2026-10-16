"""
MUX_Plotting_Mac.py - macOS-optimized version
Live capacitance plotting from Dual FDC2214 + 4:1 MUX with data logging
Optimized for macOS systems with improved GUI and serial handling
"""

import serial
import matplotlib
# Use macOS-compatible backend
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from collections import deque
import math
import csv
import time
import threading
import os
import glob
import platform

# Verify we're on macOS
if platform.system() != 'Darwin':
    print("[WARNING] This script is optimized for macOS. Proceed with caution.")

# -------------------------------
# FDC2214 constants & parameters
# -------------------------------
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)
inductance = 18e-6  # H
channel_num = 8      # 2 FDCs × 4 mux channels

def raw_to_capacitance(raw):
    """Convert raw frequency data to capacitance in pF"""
    freq = raw * scale_factor
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # pF

# -------------------------------
# Serial setup with macOS auto-detection
# -------------------------------
def find_serial_port():
    """Auto-detect serial port on macOS"""
    # Common macOS serial port patterns
    patterns = [
        "/dev/cu.usbserial-*",
        "/dev/cu.usbmodem*",
        "/dev/cu.usbmodem*",
        "/dev/cu.SLAB_USBtoUART*"
    ]
    
    for pattern in patterns:
        ports = glob.glob(pattern)
        if ports:
            return sorted(ports)[0]  # Return the first match
    
    return None

port = None
baudrate = 9600

# Try to auto-detect port
auto_port = find_serial_port()
if auto_port:
    port = auto_port
    print(f"[INFO] Auto-detected serial port: {port}")
else:
    port = "/dev/cu.usbserial-210"  # Fallback
    print(f"[INFO] Using default port: {port}")

try:
    ser = serial.Serial(port, baudrate, timeout=1)
    print(f"[INFO] Serial connection established on {port} at {baudrate} baud")
except serial.SerialException as e:
    print(f"[ERROR] Failed to open serial port {port}: {e}")
    print("[INFO] Please check:")
    print("  1. Device is connected")
    print("  2. No other programs are using the port")
    print("  3. Port name is correct")
    print("[INFO] Available ports:")
    ports = glob.glob("/dev/cu.*")
    for p in ports:
        print(f"  - {p}")
    exit(1)

buffer_len = 100
start_time = time.time()
time_buffer = deque([start_time - (buffer_len - i) * 0.1 for i in range(buffer_len)], maxlen=buffer_len)
ch = [deque([0.0] * buffer_len) for _ in range(channel_num)]

# -------------------------------
# Matplotlib setup with macOS optimizations
# -------------------------------
plt.ion()
# Set macOS-friendly figure settings
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['figure.dpi'] = 100

fig, ax = plt.subplots()
lines = [ax.plot(list(ch[i]), label=f"CH{i}")[0] for i in range(channel_num)]
ax.legend(ncol=2)
ax.set_xlabel("Time (s)", fontsize=12)
ax.set_ylabel("Capacitance (pF)", fontsize=12)
ax.set_title("Live Capacitance from Dual FDC2214 + 4:1 MUX", fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
fig.subplots_adjust(bottom=0.18)

# -------------------------------
# Logging setup
# -------------------------------
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

print("[INFO] Logging system initialized. Click 'Start Logging' to begin data collection.")
print("[INFO] Platform: macOS (Darwin)")
print(f"[INFO] Python version: {platform.python_version()}")

def choose_output_file():
    """
    Choose output file using macOS-native file dialog
    Falls back to default location if dialog fails
    """
    from datetime import datetime
    
    # Generate default filename with timestamp
    default_name = f"capacitance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Use tkinter for macOS-native file dialog
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Bring to front on macOS
        
        # macOS-specific dialog options
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            initialdir=os.path.expanduser("~/Desktop"),  # Start at Desktop
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save capacitance data log"
        )
        
        root.update()  # Process events
        root.destroy()
        
        # Handle macOS cancel (empty string)
        if not file_path or file_path == "":
            return None
            
    except Exception as e:
        print(f"[WARNING] Could not open file dialog: {e}")
        # Fallback: use default filename in data directory
        default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(default_dir, exist_ok=True)
        file_path = os.path.join(default_dir, default_name)
        print(f"[INFO] Using default filename: {file_path}")
    
    return file_path

def start_logging(event):
    """Start logging data to CSV file"""
    global logging_enabled, csv_file, csv_writer
    if logging_enabled:
        print("[DEBUG] Logging already enabled.")
        return

    try:
        fname = choose_output_file()
        if not fname:
            print("[INFO] Logging cancelled (no file selected).")
            return

        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        header = ["timestamp"] + [f"CH{i}_pF" for i in range(channel_num)]
        csv_writer.writerow(header)
        csv_file.flush()
        logging_enabled = True
        print(f"[INFO] Logging started → {fname}")
        btn_start.label.set_text("Logging: ON")
        btn_start.color = "lightgreen"
        fig.canvas.draw_idle()
    except Exception as e:
        print(f"[ERROR] Could not start logging: {e}")
        import traceback
        traceback.print_exc()
        csv_file = None
        csv_writer = None
        logging_enabled = False

def stop_logging(event):
    """Stop logging data to CSV file"""
    global logging_enabled, csv_file, csv_writer
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
        print("[INFO] Logging stopped (no open file)")

# Buttons with macOS-friendly placement
ax_start = plt.axes([0.7, 0.02, 0.1, 0.05])
ax_stop = plt.axes([0.81, 0.02, 0.1, 0.05])
btn_start = Button(ax_start, "Start Logging")
btn_stop = Button(ax_stop, "Stop Logging")
btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

# -------------------------------
# Serial reading thread with macOS optimizations
# -------------------------------
def serial_worker():
    """Background thread to read serial data continuously"""
    global logging_enabled, csv_writer, csv_file
    error_count = 0
    max_silent_errors = 10
    
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                error_count += 1
                if error_count <= max_silent_errors:
                    time.sleep(0.01)  # Brief pause on empty reads
                    continue
                else:
                    if error_count == max_silent_errors + 1:
                        print("[WARNING] Multiple serial read failures. Is device sending data?")
                    time.sleep(0.1)
                continue

            # Reset error counter on successful read
            error_count = 0

            parts = raw_line.split(",")
            if len(parts) != channel_num:
                # skip malformed or incomplete lines
                continue

            try:
                raw_vals = [int(p) for p in parts]
            except ValueError:
                continue

            caps = [raw_to_capacitance(r) for r in raw_vals]
            now = time.time()

            for i in range(channel_num):
                ch[i].append(caps[i])
                ch[i].popleft()
            time_buffer.append(now)

            # Logging
            if logging_enabled and csv_writer and csv_file:
                timestamp = now - start_time
                with log_lock:
                    try:
                        csv_writer.writerow([timestamp] + caps)
                        csv_file.flush()
                    except Exception as e:
                        print(f"[ERROR] Failed to write data: {e}")
                        logging_enabled = False

        except serial.SerialException as e:
            print(f"[ERROR] Serial port error: {e}")
            print("[INFO] Attempting to recover...")
            time.sleep(1)
            try:
                ser.close()
                time.sleep(0.5)
                ser.open()
                print("[INFO] Serial port reconnected")
            except Exception as recovery_error:
                print(f"[ERROR] Failed to recover: {recovery_error}")
                time.sleep(2)
        except Exception as e:
            error_count += 1
            if error_count <= max_silent_errors:
                continue
            else:
                if error_count == max_silent_errors + 1:
                    print(f"[WARNING] Repeated serial errors: {e}")
                time.sleep(0.1)

# Start thread
t = threading.Thread(target=serial_worker, daemon=True)
t.start()

# -------------------------------
# Live plotting loop
# -------------------------------
print("[INFO] Starting live plotting. Press Ctrl+C to exit.")
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
    print("\n[INFO] Interrupted by user")
    pass
finally:
    print("[INFO] Cleaning up...")
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
    print("[INFO] Exit complete.")


