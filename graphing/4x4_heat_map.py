import serial
import numpy as np
import matplotlib.pyplot as plt

# ====== CONFIG ======
PORT = "/dev/tty.usbserial-110"   # <-- change this
BAUD = 115200
ROWS = 4
COLS = 4
BASELINE_FRAMES = 10              # number of frames to average
AUTO_SCALE = False                # True = dynamic color scale
FIXED_RANGE = 5                   # adjust based on your signal
# ====================

ser = serial.Serial(PORT, BAUD, timeout=1)

plt.ion()
fig, ax = plt.subplots()

data = np.zeros((ROWS, COLS))
heatmap = ax.imshow(data, cmap='coolwarm', interpolation='nearest')
cbar = plt.colorbar(heatmap)

ax.set_title("Delta Capacitance Heatmap")
ax.set_xlabel("MUX2 (Col)")
ax.set_ylabel("MUX1 (Row)")

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
        if len(values) != 16:
            continue
        
        nums = np.array([float(v) for v in values])
        frame = nums.reshape((ROWS, COLS))
        
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
        delta = frame - baseline
        
        heatmap.set_data(delta)

        if AUTO_SCALE:
            heatmap.set_clim(vmin=np.min(delta), vmax=np.max(delta))
        else:
            heatmap.set_clim(vmin=-FIXED_RANGE, vmax=FIXED_RANGE)

        plt.draw()
        plt.pause(0.01)

    except KeyboardInterrupt:
        print("Stopped")
        break
    except Exception as e:
        print("Error:", e)
        continue

ser.close()
