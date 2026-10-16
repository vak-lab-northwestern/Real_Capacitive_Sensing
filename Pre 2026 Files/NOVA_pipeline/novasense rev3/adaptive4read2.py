import serial
import time
from collections import deque
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import re

matplotlib.use("macosx")  # ensures real window spawn

# ----- CONFIG -----
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200
BASE_SAMPLES = 200      # how long to sample for idle baseline calibration
PRESS_SAMPLES = 50      # how many samples per column when pressing hard
RELEASE_SAMPLES = 100    # idle sampling after press
# -----------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

regex = re.compile(r"Row\s*(\d+),\s*Col\s*(\d+)\s*:\s*(\d+)")

print("\n📍 Step 1: Do NOT touch the sensor for a while. Hit ENTER when ready.")
input()

idle_vals = []
print("⏳ Sampling idle baseline drift...")
while len(idle_vals) < BASE_SAMPLES:
    ln = ser.readline().decode().strip()
    m = regex.search(ln)
    if m:
        idle_vals.append(int(m.group(3)))

global_idle_baseline = float(np.median(idle_vals))
print("✅ Idle baseline (stable median) =", global_idle_baseline)

# Per column idle baseline + min/max storage
col_idle = [None]*4
col_min = [1e9]*4
col_max = [0]*4

print("\n📍 Step 2: We will now calibrate each column. Press each *one by one*, hard AF.\n")

# Calibrate each column
for col in range(4):
    print(f"➡️  Press ENTER to collect idle baseline for column {col}...")
    input()

    idle = []
    while len(idle) < PRESS_SAMPLES:
        ln = ser.readline().decode().strip()
        m = regex.search(ln)
        if m and int(m.group(2)) == col:
            idle.append(int(m.group(3)))

    col_idle[col] = float(np.median(idle))
    print(f"col {col} idle baseline =", col_idle[col])

    print(f"💪 Press ENTER then HOLD col {col} with max pressure for 1 second...")
    input()
    
    press = []
    t = time.time()
    while time.time() - t < 1.0:
        ln = ser.readline().decode().strip()
        m = regex.search(ln)
        if m and int(m.group(2)) == col:
            press.append(int(m.group(3)))
    
    if press:
        Δ = col_idle[col] - min(press)
        col_max[col] = Δ
        col_min[col] = 0  # untouched delta floor basically zero
        print(f"Captured Δ_max[{col}] =", Δ)
    else:
        print("⚠️ No press samples grabbed, increase contact area maybe.")

# Rendering 1x4 Heatmap forever
print("\n🎨 Calibration done. Now reading deltas into 1×4 heatmap...\n")

plt.ion()
fig, ax = plt.subplots(figsize=(4,1))

while True:
    ln = ser.readline().decode().strip()
    m = regex.search(ln)
    if not m:
        continue
    
    row = int(m.group(1))
    col = int(m.group(2))
    val = int(m.group(3))

    if col >= 4:
        continue

    # compute delta relative to its own idle baseline
    Δ = col_idle[col] - val

    # normalize based on that column's range
    Δ_norm = (Δ - col_min[col]) / (col_max[col] - col_min[col])
    Δ_norm = np.clip(Δ_norm, 0, 1)

    # update column history
    print(f"col={col}, val={val}, Δ_norm={Δ_norm:.3f}")

    # draw 1×4 heatmap (4 squares in a row)
    heat_vals = [np.clip((col_idle[c] - val if c==col else 0)/col_max[c]*10, 0, 10) for c in range(4)]
    img = np.array([heat_vals])
    ax.imshow(img, interpolation='nearest')
    ax.set_xticks([]); ax.set_yticks([])
    fig.canvas.draw()
    fig.canvas.flush_events()

    time.sleep(1/60)
