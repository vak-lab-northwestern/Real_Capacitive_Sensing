import serial
import time
from collections import deque
import math
import matplotlib.pyplot as plt
import re    # <-- added for parsing Row/Col lines

# ----- CONFIG -----
PORT = "/dev/tty.usbserial-210"
BAUD = 115200

ALPHA_BASELINE = 0.05
PRESS_DIP = 5000
RELEASE_BAND = 9000
WINDOW = 5
DELTA_DECAY = 0.75
PLOT_WINDOW = 200

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# ONLY CHANGE: choose which node to plot
SELECTED_ROW = 7
SELECTED_COL = 7
# Regex for parsing your incoming lines
line_re = re.compile(r"\s*(\d+)\s*,\s*Row\s+(\d+)\s*,\s*Col\s+(\d+)\s*:\s*(\d+)")
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# -----------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

baseline = None
delta = 0.0
isTouched = False
press_buf = deque(maxlen=WINDOW)

# ----- plotting state -----
delta_buf = deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW)
time_buf  = deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW)
start_time = time.time()

plt.ion()
fig, ax = plt.subplots()
line_plot, = ax.plot(list(time_buf), list(delta_buf))
ax.set_title(f"Real-Time Δ for Node ({SELECTED_ROW},{SELECTED_COL})")
ax.set_xlabel("Time (s)")
ax.set_ylabel("ΔC/C proxy (baseline - val)")
# ----------------------------------

print("🔥 Serial connected. Tracking adaptive baseline for selected node...\n")

try:
    while True:
        raw_line = ser.readline().decode().strip()
        if not raw_line:
            continue

        # print("RX:", raw_line)  # optional

        # -----------------------------------------------------------
        # ORIGINAL CODE expected a simple integer:
        # try:
        #     val = int(raw_line)
        # except:
        #     continue
        #
        # NEW CODE: parse Row/Col format but ONLY process selected node
        # -----------------------------------------------------------
        m = line_re.match(raw_line)
        if not m:
            continue

        timestamp = int(m.group(1))
        row = int(m.group(2))
        col = int(m.group(3))
        val = int(m.group(4))


        # If this is NOT the selected node, skip
        if row != SELECTED_ROW or col != SELECTED_COL:
            continue
        # -----------------------------------------------------------
        print(val)
        press_buf.append(val)

        if baseline is None:
            baseline = float(val)
            print("✅ baseline initialized =", baseline)

        # ----- TOUCH/RELEASE LOGIC (unchanged) -----
        if len(press_buf) > 1:
            prev_val = press_buf[-2]
        else:
            prev_val = val

        if not isTouched and (prev_val - val) > PRESS_DIP:
            isTouched = True
            print("👇 TOUCHED (freeze baseline)")

        if isTouched and abs(baseline - val) < RELEASE_BAND:
            isTouched = False
            print("☝️ RELEASED (baseline resumes drift)")
        # -----------------------------------------

        # baseline update when untouched
        if not isTouched:
            baseline = (1 - ALPHA_BASELINE) * baseline + ALPHA_BASELINE * val
            if baseline < val/20 or baseline > val*20:
                print("⚠️ baseline wild, resetting")
                baseline = float(val)

        # delta update
        if not isTouched:
            delta *= (1 - DELTA_DECAY)
            if abs(delta) < 1:
                delta = 0.0
        else:
            delta = baseline - val

        print(f"val={val}, baseline={baseline:.1f}, delta={int(delta)}, touched={isTouched}")

        # ----- UPDATE PLOT BUFFERS -----
        now = time.time() - start_time
        time_buf.append(now)
        delta_buf.append(delta)

        # redraw real-time line
        line_plot.set_xdata(list(time_buf))
        line_plot.set_ydata(list(delta_buf))

        # sliding 5-second x window
        ax.set_xlim(max(0, now - 5), now)

        # adaptive y autoscale
        ymin = min(delta_buf)
        ymax = max(delta_buf)
        if ymin == ymax:
            ymin -= 1; ymax += 1
        pad = 0.1 * (ymax - ymin)
        ax.set_ylim(ymin - pad, ymax + pad)

        fig.canvas.draw()
        fig.canvas.flush_events()

        time.sleep(0.002)

except KeyboardInterrupt:
    print("\n🛑 Stopping reader.")
finally:
    ser.close()
