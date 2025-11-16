import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import sys

# Configuration
SERIAL_PORT = 'COM9'  # Change this to your Arduino port
BAUD_RATE = 115200
NUM_ROWS = 8
NUM_COLS = 8
TOTAL_CHANNELS = NUM_ROWS + NUM_COLS
HISTORY_LENGTH = 100

# Initialize history storage
row_history = [deque(maxlen=HISTORY_LENGTH) for _ in range(NUM_ROWS)]
col_history = [deque(maxlen=HISTORY_LENGTH) for _ in range(NUM_COLS)]
frame_count = 0

# Open serial
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {SERIAL_PORT}")
except Exception as e:
    print(f"Error opening serial port: {e}")
    sys.exit(1)

# Wait for the Arduino header
while True:
    line = ser.readline().decode('utf-8').strip()
    if line.startswith("FDC"):
        print(line)
    if "ROW0" in line:  # header line
        print("Detected header. Starting data stream...")
        break

# --- FIGURE SETUP ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
fig.suptitle("Real-time Capacitance Monitoring", fontsize=16)

# Row plot setup
ax1.set_title("Rows (8 Channels)")
ax1.set_xlabel("Frame")
ax1.set_ylabel("Value")
ax1.grid(True, alpha=0.3)
ax1.set_xlim(0, HISTORY_LENGTH)

# Column plot setup
ax2.set_title("Columns (8 Channels)")
ax2.set_xlabel("Frame")
ax2.set_ylabel("Value")
ax2.grid(True, alpha=0.3)
ax2.set_xlim(0, HISTORY_LENGTH)

# Create colored line objects
colors = plt.cm.tab20(np.linspace(0, 1, 16))
lines_row = []
lines_col = []

for i in range(NUM_ROWS):
    ln, = ax1.plot([], [], label=f"Row {i}", color=colors[i], linewidth=2)
    lines_row.append(ln)

for i in range(NUM_COLS):
    ln, = ax2.plot([], [], label=f"Col {i}", color=colors[i+8], linewidth=2)
    lines_col.append(ln)

ax1.legend(loc='upper right', fontsize=8)
ax2.legend(loc='upper right', fontsize=8)

plt.tight_layout()


# --- ANIMATION UPDATE FUNCTION ---
def update(frame):
    global frame_count

    try:
        line = ser.readline().decode('utf-8').strip()

        if not line or "FDC" in line:
            return lines_row + lines_col

        parts = line.split(',')
        if len(parts) != TOTAL_CHANNELS:
            return lines_row + lines_col

        values = [int(x) for x in parts]

        # Split rows and columns
        row_vals = values[:NUM_ROWS]
        col_vals = values[NUM_ROWS:]

        for i in range(NUM_ROWS):
            row_history[i].append(row_vals[i])

        for i in range(NUM_COLS):
            col_history[i].append(col_vals[i])

        frame_count += 1

    except Exception as e:
        print(f"Read error: {e}")
        return lines_row + lines_col

    # Update row plots
    for i in range(NUM_ROWS):
        x = list(range(len(row_history[i])))
        lines_row[i].set_data(x, list(row_history[i]))

    # Update column plots
    for i in range(NUM_COLS):
        x = list(range(len(col_history[i])))
        lines_col[i].set_data(x, list(col_history[i]))

    # Autoscale Y
    ax1.relim()
    ax1.autoscale_view(scalex=False, scaley=True)
    ax2.relim()
    ax2.autoscale_view(scalex=False, scaley=True)

    # Scroll X if needed
    if frame_count > HISTORY_LENGTH:
        ax1.set_xlim(frame_count - HISTORY_LENGTH, frame_count)
        ax2.set_xlim(frame_count - HISTORY_LENGTH, frame_count)

    # Update title
    fig.suptitle(f"Real-time Capacitance Monitoring — Frame {frame_count}", fontsize=16)

    return lines_row + lines_col


# Start animation
ani = FuncAnimation(fig, update, interval=20, blit=False, cache_frame_data=False)

print("Plotting... close the window to stop.")
plt.show()

ser.close()
print("Serial closed.")
