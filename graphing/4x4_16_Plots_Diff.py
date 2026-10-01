import serial
import matplotlib.pyplot as plt
from collections import deque
import csv
import time
import math
import threading
import queue
from datetime import datetime

#  Settings 
serialPort = "/dev/cu.usbserial-10"
baudrate = 250000
channel_num = 4
buffer_len = 10
visible_channels = 4

# Auto-generate filename with timestamp so you never overwrite old data
log_filename = f"capacitance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

#  Log Queue (thread-safe) 
log_queue = queue.Queue()
log_stop_event = threading.Event()

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

visible_channels = min(visible_channels, channel_num)
ncols = math.ceil(math.sqrt(visible_channels))
nrows = math.ceil(visible_channels / ncols)

fig, axes = plt.subplots(nrows, ncols, figsize=(14, 12), sharex=True, sharey=True)
fig.suptitle(f"{visible_channels} Capacitance Sensor Grid (pF) — Logging: {log_filename}")

if isinstance(axes, plt.Axes):
    axes_flat = [axes]
else:
    axes_flat = axes.flatten()

lines = []
for i in range(visible_channels):
    ax_sub = axes_flat[i]
    line, = ax_sub.plot([], [], label=f"CH{i}", color='tab:blue')
    lines.append(line)
    ax_sub.set_title(f"Node {i}", fontsize=9)
    ax_sub.grid(True, alpha=0.3)

for j in range(visible_channels, len(axes_flat)):
    axes_flat[j].axis('off')

plt.tight_layout()

#  CSV Writer Thread — owns the file exclusively 
def csv_writer_thread():
    try:
        with open(log_filename, mode="w", newline="", buffering=1) as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_s"] + [f"CH{i}_pF" for i in range(channel_num)])
            print(f"[INFO] Logging started → {log_filename}")
            while not log_stop_event.is_set() or not log_queue.empty():
                try:
                    row = log_queue.get(timeout=0.1)
                    writer.writerow(row)
                    log_queue.task_done()
                except queue.Empty:
                    continue
        print(f"[INFO] CSV closed cleanly → {log_filename}")
    except Exception as e:
        print(f"[ERROR] CSV writer: {e}")

csv_thread = threading.Thread(target=csv_writer_thread, daemon=True)
csv_thread.start()

#  Serial Worker Thread 
def serial_worker():
    while True:
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                continue

            parts = raw_line.split(",")
            if len(parts) != channel_num:
                continue

            caps = [float(p) for p in parts]
            now = time.time()

            for i in range(channel_num):
                ch[i].append(caps[i])
            time_buffer.append(now)

            # Always log — queue it, writer thread handles the rest
            timestamp = now - start_time
            row = [f"{timestamp:.3f}"] + [f"{c:.4f}" for c in caps]
            log_queue.put(row)

        except Exception as e:
            print(f"[ERROR] Serial read: {e}")

serial_thread = threading.Thread(target=serial_worker, daemon=True)
serial_thread.start()

#  Main Plot Loop 
try:
    while True:
        t_vals = [t - start_time for t in time_buffer]
        for i in range(visible_channels):
            lines[i].set_data(t_vals, list(ch[i]))

        for ax_sub in axes_flat[:visible_channels]:
            ax_sub.relim()
            ax_sub.autoscale_view()

        fig.canvas.flush_events()
        plt.pause(0.01)

except KeyboardInterrupt:
    pass

finally:
    log_stop_event.set()
    csv_thread.join(timeout=5)  # flush remaining rows before exit
    ser.close()
    print("Exiting.")

# output node layout:
# 0  1  2  3
# 4  5  6  7
# 8  9  10 11
# 12 13 14 15