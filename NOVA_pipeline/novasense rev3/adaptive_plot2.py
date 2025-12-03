import serial
import time
from collections import deque
import matplotlib.pyplot as plt   # <-- added for plotting

# ----- CONFIG -----
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200

ALPHA_BASELINE = 0.001  # very slow baseline drift tracking
PRESS_THRESH = 10000    # bigger value for press
RELEASE_THRESH = 100  # smaller value for release (hysteresis)
DELTA_DECAY = 0.75      # delta feedback to 0 when untouched
WINDOW = 5              # fast spike decision window
PLOT_WINDOW = 200       # how many samples to show on plot
# ------------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # let board reset

baseline = None
delta = 0.0
isTouched = False
press_buf = deque(maxlen=WINDOW)

# ---- NEW: plotting state ----
delta_buf = deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW)
time_buf = deque([0.0]*PLOT_WINDOW, maxlen=PLOT_WINDOW)
start_time = time.time()

plt.ion()
fig, ax = plt.subplots()
line_plot, = ax.plot(list(time_buf), list(delta_buf))
ax.set_title("Delta vs Time")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Delta (baseline - val)")
ax.set_xlim(0, 5)
ax.set_ylim(-5000, 50000)   # will auto-adjust later
# ------------------------------

print("🔥 Serial connected. Listening RAW integers only...\n")

try:
    while True:
        line = ser.readline().decode().strip()
        if line:
            print("RX:", line)  # debug

        try:
            val = int(line)
        except:
            continue  # skip non-integers, but won't be silent thanks to print above

        press_buf.append(val)

        if baseline is None:
            baseline = float(val)
            print("✅ baseline initialized =", baseline)

        # Touch detect using *recent max band*, not global constant compare
        recent_max = max(press_buf)
        drop = recent_max - val

        if not isTouched and drop > PRESS_THRESH:
            isTouched = True
            print("👇 TOUCHED (freeze baseline)")
        elif isTouched and drop < RELEASE_THRESH:
            isTouched = False
            print("☝️ RELEASED (baseline resumes drift tracking)")

        # baseline only updates when NOT touched
        if not isTouched:
            baseline = baseline + ALPHA_BASELINE * (val - baseline)

        # delta feedback loop toward zero when not touched
        if not isTouched:
            delta = delta - DELTA_DECAY * delta  # feedback decay
            if abs(delta) < 1:
                delta = 0.0
        else:
            delta = baseline - val  # true signal when touched

        print(f"val={val}, baseline={baseline:.1f}, delta={int(delta)}, touched={isTouched}")
        print("drop:", drop)

        # ---- NEW: update plotting buffers ----
        now = time.time() - start_time
        time_buf.append(now)
        delta_buf.append(delta)

        line_plot.set_xdata(list(time_buf))
        line_plot.set_ydata(list(delta_buf))

        # keep a rolling 5-second window on x
        ax.set_xlim(max(0, now - 5), now)

        # auto-scale y around current data
        ymin = min(delta_buf)
        ymax = max(delta_buf)
        if ymin == ymax:
            ymin -= 1
            ymax += 1
        pad = 0.1 * (ymax - ymin)
        ax.set_ylim(ymin - pad, ymax + pad)

        fig.canvas.draw()
        fig.canvas.flush_events()
        # --------------------------

        time.sleep(0.002)

except KeyboardInterrupt:
    print("\n🛑 Stopped reader.")
finally:
    ser.close()
