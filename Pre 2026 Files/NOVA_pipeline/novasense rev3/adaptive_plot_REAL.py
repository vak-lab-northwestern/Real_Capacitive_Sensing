import serial
import time
from collections import deque
import math
import matplotlib.pyplot as plt  # <-- plotting added

# ----- CONFIG -----
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200

ALPHA_BASELINE = 0.05
PRESS_DIP = 3000 # 6000
RELEASE_BAND = 1200 # 3000
WINDOW = 5
DELTA_DECAY = 0.75
PLOT_WINDOW = 200  # buffer for last 200 samples
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
ax.set_title("Real-Time Δ (baseline - val)")
ax.set_xlabel("Time (s)")
ax.set_ylabel("ΔC/C proxy (baseline - val)")
# ----------------------------------

print("🔥 Serial connected. Tracking adaptive baseline + frozen on touch...\n")

try:
    while True:
        raw_line = ser.readline().decode().strip()
        if not raw_line:
            continue

        print("RX:", raw_line)

        try:
            val = int(raw_line)
        except:
            continue

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

        # adaptive y autoscale (like before)
        ymin = min(delta_buf)
        ymax = max(delta_buf)
        if ymin == ymax:
            ymin -= 1; ymax += 1
        pad = 0.1 * (ymax - ymin)
        ax.set_ylim(ymin - pad, ymax + pad)

        fig.canvas.draw()
        fig.canvas.flush_events()
        # ------------------------------

        time.sleep(0.002)

except KeyboardInterrupt:
    print("\n🛑 Stopping reader.")
finally:
    ser.close()
