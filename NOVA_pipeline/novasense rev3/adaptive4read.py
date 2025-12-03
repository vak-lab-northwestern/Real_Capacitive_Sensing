import serial
import time
from collections import deque
import matplotlib.pyplot as plt
import re

# ----- CONFIG -----
TARGET_ROW = 1
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200

ALPHA_BASELINE = 0.0005
PRESS_DIP = 6000
RELEASE_BAND = 3000
WINDOW = 5
DELTA_DECAY = 0.75
PLOT_WINDOW = 200
# ------------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

baseline = None
delta = 0.0
isTouched = False
press_buf = deque(maxlen=WINDOW)

pattern = re.compile(r"Row\s*(\d+),\s*Col\s*(\d+)\s*:\s*(\d+)")

# ----- plotting buffers for 4 columns -----
delta_bufs = [deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW) for _ in range(4)]
time_buf   = deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW)
start_time = time.time()

plt.ion()
fig, axes = plt.subplots(4, 1)  # 4 plots down the page
lines = []

for i, ax in enumerate(axes):
    line, = ax.plot(list(time_buf), list(delta_bufs[i]))
    ax.set_title(f"Column {i} Δ vs Time")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Δ (baseline - val)")
    lines.append(line)

# also track overlap-safe baseline when untouched
sanity_min = 1e3
sanity_max = 1e9

print("🔥 Serial connected. 4-column real-time delta plotting engaged...\n")

latest_vals = [None]*4

try:
    while True:
        line = ser.readline().decode().strip()
        if not line:
            continue

        m = pattern.search(line)
        if not m:
            continue

        row = int(m.group(1))
        col = int(m.group(2))
        val = int(m.group(3))

        if col >= 4:
            continue

        latest_vals[col] = val

        if baseline is None:
            baseline = float(val)
            print("✅ baseline init =", baseline)

        if col == 0:
            prev_val = press_buf[-1] if press_buf else val
            press_buf.append(val)
            if not isTouched and (prev_val - val) > PRESS_DIP:
                isTouched = True
                print("👇 TOUCH START")

            if isTouched and abs(baseline - val) < RELEASE_BAND:
                isTouched = False
                print("☝️ RELEASED")

            if not isTouched:
                baseline = (1 - ALPHA_BASELINE) * baseline + ALPHA_BASELINE * val
                if baseline < val/20 or baseline > val*20:
                    baseline = float(val)

            if not isTouched:
                delta = delta * (1 - DELTA_DECAY)
                if abs(delta) < 1:
                    delta = 0.0
            else:
                delta = baseline - val

        if isTouched:
            d = baseline - val
        else:
            d = 0.0
            if baseline is not None and latest_vals[col] is not None:
                d = baseline - val
                d = d * 0.0 if not isTouched else d

        t = time.time() - start_time
        time_buf.append(t)
        delta_bufs[col].append(d)
        latest_vals[col] = val
        print(f"col={col}, val={val}, base={baseline:.1f}, Δ={d}, touch={isTouched}")

        ax = axes[col]
        lines[col].set_xdata(list(time_buf))
        lines[col].set_ydata(list(delta_bufs[col]))
        ax.set_xlim(max(0, t - 5), t)
        ymin = min(delta_bufs[col]) if delta_bufs[col] else -1
        ymax = max(delta_bufs[col]) if delta_bufs[col] else 1
        if ymin == ymax:
            ymin -= 1; ymax += 1
        pad = 0.1 * (ymax - ymin)
        ax.set_ylim(ymin - pad, ymax + pad)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.002)

except KeyboardInterrupt:
    print("\n🛑 reader terminated. baseline crown retained.")
finally:
    ser.close()
