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
HISTORY_LENGTH = 100  # Number of frames to display

# Initialize data storage (keep history of readings)
row_history = [deque(maxlen=HISTORY_LENGTH) for _ in range(NUM_ROWS * NUM_COLS)]
col_history = [deque(maxlen=HISTORY_LENGTH) for _ in range(NUM_ROWS * NUM_COLS)]
frame_count = 0

# Setup serial connection
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {SERIAL_PORT}")
except Exception as e:
    print(f"Error opening serial port: {e}")
    sys.exit(1)

# Skip initial messages until we get to the header
while True:
    line = ser.readline().decode('utf-8').strip()
    if line == "Row_index,Column_index,Raw_Cap_Row,Raw_Cap_Column":
        print("Found header, starting data collection...")
        break
    if "FDC" in line:
        print(line)

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
fig.suptitle('Real-time Capacitance Monitoring', fontsize=16)

# Setup row capacitance plot
ax1.set_title('Row Capacitance Over Time')
ax1.set_xlabel('Frame')
ax1.set_ylabel('Capacitance (Raw)')
ax1.grid(True, alpha=0.3)
ax1.set_xlim(0, HISTORY_LENGTH)

# Setup column capacitance plot
ax2.set_title('Column Capacitance Over Time')
ax2.set_xlabel('Frame')
ax2.set_ylabel('Capacitance (Raw)')
ax2.grid(True, alpha=0.3)
ax2.set_xlim(0, HISTORY_LENGTH)

# Create line objects for each sensor position
lines_row = []
lines_col = []
colors = plt.cm.tab20(np.linspace(0, 1, NUM_ROWS * NUM_COLS))

for i in range(NUM_ROWS * NUM_COLS):
    row_idx = i // NUM_COLS
    col_idx = i % NUM_COLS
    label = f'R{row_idx}C{col_idx}'
    
    line_r, = ax1.plot([], [], label=label, color=colors[i], alpha=0.7, linewidth=1)
    line_c, = ax2.plot([], [], label=label, color=colors[i], alpha=0.7, linewidth=1)
    
    lines_row.append(line_r)
    lines_col.append(line_c)

# Add legends (initially, can be toggled off if too crowded)
# ax1.legend(loc='upper left', fontsize=6, ncol=4)
# ax2.legend(loc='upper left', fontsize=6, ncol=4)

plt.tight_layout()

def update(frame):
    """Update function for animation"""
    global frame_count
    
    # Read one complete frame (all rows and columns)
    for i in range(NUM_ROWS * NUM_COLS):
        try:
            line = ser.readline().decode('utf-8').strip()
            
            if not line or line.startswith("Row_index"):
                continue
                
            # Parse CSV line: Row_index, Column_index, Raw_Cap_Row, Raw_Cap_Column
            parts = line.split(',')
            if len(parts) == 4:
                row_idx = int(parts[0])
                col_idx = int(parts[1])
                raw_cap_row = int(parts[2])
                raw_cap_col = int(parts[3])
                
                # Calculate linear index
                idx = row_idx * NUM_COLS + col_idx
                
                # Append new data to history
                row_history[idx].append(raw_cap_row)
                col_history[idx].append(raw_cap_col)
                
        except Exception as e:
            print(f"Error parsing line: {line} - {e}")
            continue
    
    frame_count += 1
    
    # Update all line plots
    for i in range(NUM_ROWS * NUM_COLS):
        if len(row_history[i]) > 0:
            x_data = list(range(len(row_history[i])))
            lines_row[i].set_data(x_data, list(row_history[i]))
            lines_col[i].set_data(x_data, list(col_history[i]))
    
    # Auto-scale y-axis
    ax1.relim()
    ax1.autoscale_view(scalex=False, scaley=True)
    ax2.relim()
    ax2.autoscale_view(scalex=False, scaley=True)
    
    # Update x-axis limits for scrolling effect
    if frame_count > HISTORY_LENGTH:
        ax1.set_xlim(frame_count - HISTORY_LENGTH, frame_count)
        ax2.set_xlim(frame_count - HISTORY_LENGTH, frame_count)
    
    # Update title with frame info
    fig.suptitle(f'Real-time Capacitance Monitoring - Frame {frame_count}', fontsize=16)
    
    return lines_row + lines_col

# Create animation
ani = FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)

print("Starting real-time plot. Close the window to exit.")
plt.show()

# Cleanup
ser.close()
print("Serial port closed.")