import serial
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for better macOS button responsiveness
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from collections import deque
import math
import csv
import time
import threading
import os
from datetime import datetime

# FDC2214 constants
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)
inductance = 18e-6  # H
channel_num = 8

def raw_to_capacitance(raw):
    freq = raw * scale_factor
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # picofarads

# Serial setup (adjust port as needed)
try:
    ser = serial.Serial("/dev/cu.usbserial-210", 9600,timeout=1)
    print("[INFO] Serial connection established")
except Exception as e:
    print(f"[ERROR] Could not connect to serial port: {e}")
    print("Please check the port and try again")
    exit(1)

buffer_len = 100
start_time = time.time()
time_buffer = deque([start_time - (buffer_len - i) * 0.1 for i in range(buffer_len)], maxlen=buffer_len)
ch = [deque([0.0] * buffer_len) for _ in range(channel_num)]

# Plot setup
plt.ion()
fig, ax = plt.subplots()
lines = [ax.plot(list(ch[i]), label=f"CH{i}")[0] for i in range(channel_num)]
ax.legend()
ax.set_xlabel("Time (s)")
ax.set_ylabel("Capacitance (pF)")
ax.set_title("Live Capacitance from FDC2214 Channels")
ax.grid(True)

# Logging state 
logging_enabled = False
csv_file = None
csv_writer = None
log_lock = threading.Lock()

# Initialize logging state
print("[INFO] Logging system initialized. Click 'Start Logging' to begin data collection.")

def generate_filename():
    """Generate automatic filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"../data/11042025_yarncross_4ply_company_singleconfig8_pressure_cap.csv"

def start_logging(event):
    global logging_enabled, csv_file, csv_writer
    print("[DEBUG] Start button clicked")

    if logging_enabled:
        print("[DEBUG] Logging already enabled, ignoring click")
        return

    # Generate automatic filename to avoid tkinter conflicts
    fname = generate_filename()
    print(f"[INFO] Using filename: {fname}")

    try:
        csv_file = open(fname, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        # Write header for all 8 channels
        csv_writer.writerow(["timestamp"] + [f"CH{i}_pF" for i in range(channel_num)])
        csv_file.flush()
        print(f"[INFO] Logging started to {fname}")
        
        # Update button state
        logging_enabled = True
        btn_start.label.set_text("Logging: ON")
        btn_start.color = "lightgreen"
        fig.canvas.draw()  # Immediate update for button state
        fig.canvas.flush_events()  # Process GUI events
        
    except Exception as e:
        print(f"[ERROR] Could not open file: {e}")
        csv_file = None
        csv_writer = None
        return

def stop_logging(event):
    global logging_enabled, csv_file, csv_writer
    print("[DEBUG] Stop button clicked")
    
    # Always stop logging when button is pressed
    logging_enabled = False
    
    # Reset button states
    btn_start.label.set_text("Start Logging")
    btn_start.color = "0.85"
    fig.canvas.draw()  # Immediate update for button state
    fig.canvas.flush_events()  # Process GUI events
    
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

# Bring figure to front and ensure it's ready for interactions
try:
    manager = plt.get_current_fig_manager()
    if hasattr(manager, 'window'):
        manager.window.wm_attributes('-topmost', 1)  # Bring to front
        manager.window.wm_attributes('-topmost', 0)  # Allow it to go back
except:
    pass

# Small delay to ensure GUI is fully initialized
time.sleep(0.1)
fig.canvas.draw()
plt.pause(0.1)  # Give GUI time to process initial draw

def serial_worker():
    global logging_enabled, csv_writer, csv_file
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue
            parts = raw_line.split(",")
            if len(parts) != channel_num:
                continue

            raw_vals = list(map(int, parts))
            caps = [raw_to_capacitance(r) for r in raw_vals]

            # update buffers (only once)
            now = time.time()
            for i in range(channel_num):
                ch[i].append(caps[i])
                ch[i].popleft()
            time_buffer.append(now)

            # logging with improved error handling
            if logging_enabled and csv_writer and csv_file:
                timestamp = now - start_time
                with log_lock:
                    try:
                        csv_writer.writerow([timestamp] + caps)
                        csv_file.flush()
                        # Reduce debug output frequency
                        if int(timestamp) % 10 == 0:  # Print every 10 seconds
                            print(f"[DEBUG] Wrote data: {timestamp:.2f}s, CH0: {caps[0]:.2f}pF")
                    except Exception as e:
                        print(f"[ERROR] Failed to write data: {e}")
                        logging_enabled = False
                        # Reset button state on error
                        btn_start.label.set_text("Start Logging")
                        btn_start.color = "0.85"
                        fig.canvas.draw()  # Update button state immediately
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
        for i in range(channel_num):
            lines[i].set_data(t_vals, list(ch[i]))
        ax.relim()
        ax.autoscale_view()
        fig.canvas.flush_events()
        plt.pause(0.05)  # gives control back to GUI event loop
except KeyboardInterrupt:
    print("\n[INFO] Interrupted by user")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
finally:
    # Cleanup
    if csv_file:
        with log_lock:
            try:
                csv_file.close()
                print("[INFO] CSV file closed during cleanup")
            except Exception:
                pass
    try:
        ser.close()
        print("[INFO] Serial connection closed")
    except Exception:
        pass
    print("Exiting.")
