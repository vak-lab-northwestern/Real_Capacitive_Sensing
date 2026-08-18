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
FIXED_RANGE = 20             # a   djust based on your signal
TOTAL = ROWS * COLS
GAIN = 100 #conversion_gain parameter (set-up in CapTIvate)
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

ax.set_xticks(range(COLS))
ax.set_yticks(range(ROWS))
# matrix of resting base electrode capacitances
base_caps = np.array([
    [1.76,1.89,1.78,2.15],
    [2.08,2.15,2.44,2.40],
    [2.03,2.17,2.17,2.46],
    [1.93,2.08,2.29,2.28]
])


percent_change_in_cap = np.zeros((ROWS,COLS))

ax.set_title("Percent Change in Capacitance Heatmap")


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

        #get csv data from captivate, first 16 values "counts", next 16 values "LTA"
        values = line.split(",")
        # if len(values) != TOTAL:
        #     continue
        
        str_counts = values[:16]
        str_ltas = values[16:]

        counts = np.array([float(count) for count in str_counts])
        counts = counts.reshape((ROWS, COLS)).T
        
        ltas = np.array([float(lta) for lta in str_ltas])
        ltas = ltas.reshape((ROWS, COLS)).T
        
        
        # if not np.all(np.isfinite(frame)):
        #     continue

        # # ===== BASELINE COLLECTION =====
        # if baseline is None:
        #     baseline_accum += frame
        #     baseline_count += 1

        #     if baseline_count >= BASELINE_FRAMES:
        #         baseline = baseline_accum / BASELINE_FRAMES
        #         print("Baseline captured.")
        #     continue

        # ===== DELTA COMPUTATION =====
        for i in range(ROWS):
            for j in range(COLS):
                percent_change_in_cap[i][j] = GAIN * (1/counts[i][j] - 1/ltas[i][j]) * 100
        #delta = frame - baseline
        #delta = baseline - frame + edge_adjust
        
        heatmap.set_data(percent_change_in_cap)

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