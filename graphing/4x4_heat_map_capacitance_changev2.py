import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


# ====== CONFIG ======
PORT = "/dev/cu.usbserial-0001"        # <-- change this
BAUD = 115200
ROWS = 4
COLS = 4
BASELINE_FRAMES = 50              # number of frames to average
AUTO_SCALE = False                # True = dynamic color scale
FIXED_RANGE = 30          # adjust based on your signal
TOTAL = ROWS * COLS
GAIN = 100 #conversion_gain parameter (set-up in CapTIvate)
ALPHA = 0.01 # (ratio between 0 and 1) that deterimens how fast LTA changes, smaller is slower
TOUCH_THRESHOLD = 10.0 # how much difference before freezing LTA so touches don't influence average
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
ax.set_title("Percent Change in Capacitance Heatmap")
ax.set_xlabel("Columns")
ax.set_ylabel("Rows")
plt.show()

'''
# matrix of resting base electrode capacitances, not used in this script
base_caps = np.array([
    [2.15,2.44,2.40, 1.91],
    [2.17,2.17,2.46, 2.06],
    [2.08,2.29,2.28, 1.93],
    [1.94,2.02, 2.05,1.69]
])
base_caps = np.array([
    [1.76,1.89,1.78,2.15],
    [2.08,2.15,2.44,2.40],
    [2.03,2.17,2.17,2.46],
    [1.93,2.08,2.29,2.28]
])
'''

percent_change_in_cap = np.zeros((ROWS,COLS))

ltas = None
lta_accum = np.zeros((ROWS, COLS))
lta_count = 0

print(f"Collecting initial lta values over {BASELINE_FRAMES}... Do NOT touch the sensor.")

def print_matrix(matrix):
    for row in matrix:
        for val in row:
            print(f"{val:.2f}", end="\t")
        print()

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
        # str_ltas = values[16:]

        counts = np.array([float(count) for count in str_counts])
        counts = counts.reshape((ROWS, COLS)).T
        # ltas = np.array([float(lta) for lta in str_ltas])
        # ltas = ltas.reshape((ROWS, COLS)).T
        

        # ===== BASELINE COLLECTION =====
        if ltas is None:
            lta_accum += counts
            lta_count += 1

            if lta_count >= BASELINE_FRAMES:
                ltas = lta_accum / BASELINE_FRAMES
                print("Baseline captured.")
            continue

        # ===== LTA CALCULATION =====
        # Use Exponential Moving Average Equation
        for i in range(ROWS):
            for j in range(COLS):
                #deviation percentage
                dev_percent = abs(counts[i][j] - ltas[i][j])/ltas[i][j] * 100
                #only change lta values if touch is not happening
                if dev_percent < TOUCH_THRESHOLD:
                    ltas[i][j] = (ALPHA * counts[i][j]) + ((1-ALPHA) * ltas[i][j])


        # ===== DELTA COMPUTATION =====
        for i in range(ROWS):
            for j in range(COLS):
                percent_change_in_cap[i][j] = GAIN * (1/counts[i][j] - 1/ltas[i][j]) * 100


        heatmap.set_data(percent_change_in_cap)

        print_matrix(percent_change_in_cap)


        if AUTO_SCALE:
            heatmap.set_clim( vmax=np.max(percent_change_in_cap))
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