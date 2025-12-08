import serial
import time
from collections import deque
import math
import matplotlib.pyplot as plt
import re

# ----- CONFIG -----
PORT = "/dev/tty.usbserial-210"
BAUD = 115200

PLOT_WINDOW = 200

# SELECT THE NODE YOU WANT TO PLOT
SELECTED_ROW = 0
SELECTED_COL = 0

myWINDOW = 10.0

# Regex matching: "12345 , Row 3, Col 5 : 9876543"
line_re = re.compile(r"\s*(\d+)\s*,\s*Row\s+(\d+)\s*,\s*Col\s+(\d+)\s*:\s*(\d+)")

# -----------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

# ----- RAW ADC BUFFER -----
adc_buf  = deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW)
time_buf = deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW)
start_time = time.time()

plt.ion()
fig, ax = plt.subplots()
line_plot, = ax.plot(list(time_buf), list(adc_buf))
ax.set_title(f"Real-Time RAW ADC for Node ({SELECTED_ROW},{SELECTED_COL})")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Raw ADC Value")

print("🔥 Serial connected. Plotting RAW ADC only...\n")

try:
    while True:
        raw_line = ser.readline().decode().strip()
        if not raw_line:
            continue

        # Parse row/col/value
        m = line_re.match(raw_line)
        if not m:
            continue

        timestamp = int(m.group(1))
        row = int(m.group(2))
        col = int(m.group(3))
        val = int(m.group(4))

        # Skip if it's not the selected node
        if row != SELECTED_ROW or col != SELECTED_COL:
            continue

        # ----------------------------------------------------
        # ORIGINAL PROCESSING LOGIC — NOW DISABLED
        # baseline, delta, touched logic removed by comment:
        #
        # press_buf.append(val)
        # if baseline is None: baseline = float(val)
        # if not isTouched: baseline = ...
        # delta update ...
        #
        # We now strictly use `val` raw.
        # ----------------------------------------------------

        # ----- UPDATE PLOT BUFFERS (RAW ONLY) -----
        now = time.time() - start_time
        time_buf.append(now)
        adc_buf.append(val)

        # redraw line
        line_plot.set_xdata(list(time_buf))
        line_plot.set_ydata(list(adc_buf))

        # sliding 5-second window
        ax.set_xlim(max(0, now - myWINDOW), now)

        # autoscale Y around raw ADC
        # ymin = min(adc_buf)
        # ymax = max(adc_buf)
        # if ymin == ymax:
        #     ymin -= 1; ymax += 1
        # pad = 0.1 * (ymax - ymin)
        # ax.set_ylim(ymin - pad, ymax + pad)

        # ----- autoscale Y based ONLY on visible window -----
        visible_vals = [v for (t, v) in zip(time_buf, adc_buf) if t >= now - myWINDOW]

        if visible_vals:
            ymin = min(visible_vals)
            ymax = max(visible_vals)
        else:
            ymin = min(adc_buf)
            ymax = max(adc_buf)

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
