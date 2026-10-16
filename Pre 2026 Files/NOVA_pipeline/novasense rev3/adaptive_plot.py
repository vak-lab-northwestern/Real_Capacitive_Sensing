import serial
import time
from collections import deque
import matplotlib.pyplot as plt  # new line, required for plot

# ----- CONFIG -----
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200

ALPHA_BASELINE = 0.001
PRESS_THRESH = 10000
RELEASE_THRESH = 100
DELTA_DECAY = 0.25
WINDOW = 5
# ------------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

baseline = None
delta = 0.0
isTouched = False
press_buf = deque(maxlen=WINDOW)

# ==== new block for plotting state ====
delta_buf = deque([0.0]*WINDOW, maxlen=WINDOW)
time_buf = deque([0.0]*WINDOW, maxlen=WINDOW)

plt.ion()
fig, ax = plt.subplots()
line_plot, = ax.plot(list(time_buf), list(delta_buf))  # live line
ax.set_title("Live Δ (baseline - reading)")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Delta")
ax.set_xlim(0, 5)
ax.set_ylim(-50000, 50000)
# ========================================

print("🔥 Serial connected. Listening RAW integers only...\n")

try:
    while True:
        line = ser.readline().decode().strip()
        if line:
            print("RX:", line)

        try:
            val = int(line)
        except:
            continue

        press_buf.append(val)

        if baseline is None:
            baseline = float(val)
            print("✅ baseline initialized =", baseline)

        recent_max = max(press_buf)
        drop = recent_max - val

        if not isTouched and drop > PRESS_THRESH:
            isTouched = True
            print("👇 TOUCHED (freeze baseline)")
        elif isTouched and drop < RELEASE_THRESH:
            isTouched = False
            print("☝️ RELEASED (baseline resumes)")

        if not isTouched:
            baseline = baseline + ALPHA_BASELINE * (val - baseline)

        if not isTouched:
            delta = delta - DELTA_DECAY * delta
            if abs(delta) < 1:
                delta = 0.0
        else:
            delta = baseline - val

        # ==== minimal new code for plotting, no other logic touched ====
        now = time.time() - time_buf[0] if time_buf[0] != 0 else 0
        time_buf.append(now)
        delta_buf.append(delta)

        # update plot range to rolling 5s window
        ax.set_xlim(now - 5, now)
        ymin, ymax = min(delta_buf), max(delta_buf)
        ax.set_ylim(ymin - 1000, ymax + 1000)

        line_plot.set_xdata(list(time_buf))
        line_plot.set_ydata(list(delta_buf))
        fig.canvas.draw()
        fig.canvas.flush_events()
        # ===========================================================

        print(f"val={val}, baseline={baseline:.1f}, delta={int(delta)}, touched={isTouched}")

        time.sleep(0.002)

except KeyboardInterrupt:
    print("\n🛑 Stopped reader.")
finally:
    ser.close()
