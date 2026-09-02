import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


# ====== CONFIG ======
PORT = "/dev/cu.usbserial-0001"        # <-- change this
BAUD = 115200
ROWS = 4
COLS = 4
BASELINE_FRAMES = 30              # number of frames to average
AUTO_SCALE = False                # True = dynamic color scale
FIXED_RANGE = 200             # a   djust based on your signal
TOTAL = ROWS * COLS
# ====================

ser = serial.Serial(PORT, BAUD, timeout=1)

plt.ion()
fig, ax = plt.subplots()

data = np.zeros((ROWS, COLS))
colors = [
    (0, 0, 1),       
    (1, 0.5, 0), # gray for zero
    (1, 0, 0)        # red for positive
]
cmap = mcolors.LinearSegmentedColormap.from_list("custom_cmap", colors)
norm = mcolors.TwoSlopeNorm(vcenter=0, vmax=FIXED_RANGE)
heatmap = ax.imshow(data, cmap=cmap, interpolation='nearest')
cbar = plt.colorbar(heatmap)


edge_adjust = np.array([
    [0,-25,-25,0],
    [-25,-40,-40,-25],
    [-25,-40,-40,-25],
    [0,-25,-25,0]
])

ax.set_title("Delta Capacitance Heatmap")


ax.set_xlabel("Columns")
ax.set_ylabel("Rows")

plt.show()

baseline = None
baseline_accum = np.zeros((ROWS, COLS))
baseline_count = 0

print("Collecting baseline... Do NOT touch the sensor.")

while True:
    try:
        line = ser.readline().decode().strip()
        if not line:
            continue

        values = line.split(",")
        if len(values) != TOTAL:
            continue
        
        nums = np.array([float(v) for v in values])

        frame = nums.reshape((ROWS, COLS)).T
        #print(frame)
        
        if not np.all(np.isfinite(frame)):
            continue

        # ===== BASELINE COLLECTION =====
        if baseline is None:
            baseline_accum += frame
            baseline_count += 1

            if baseline_count >= BASELINE_FRAMES:
                baseline = baseline_accum / BASELINE_FRAMES
                print("Baseline captured.")
            continue

        # ===== DELTA COMPUTATION =====
        #delta = frame - baseline
        delta = baseline - frame + edge_adjust
        
        heatmap.set_data(delta)

        if AUTO_SCALE:
            heatmap.set_clim( vmax=np.max(delta))
        else:
            heatmap.set_clim(vmax=FIXED_RANGE)
        
        plt.draw()
        plt.pause(0.01)

    except KeyboardInterrupt:
        print("Stopped")
        break
    except Exception as e:
        print("Error:", e)
        continue

ser.close()