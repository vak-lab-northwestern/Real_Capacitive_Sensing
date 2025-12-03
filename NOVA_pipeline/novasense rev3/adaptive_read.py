import serial
import time
from collections import deque

# ----- CONFIG -----
PORT = "/dev/tty.usbmodem21101"
BAUD = 115200

ALPHA_BASELINE = 0.001  # very slow baseline drift tracking
PRESS_THRESH = 40000    # tune for your sensor
RELEASE_THRESH = 40000
DELTA_DECAY = 0.25      # delta feedback to 0 when untouched
WINDOW = 5              # fast spike decision window
# ------------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # let board reset

baseline = None
delta = 0.0
isTouched = False
press_buf = deque(maxlen=WINDOW)

print("🔥 Serial connected. Listening RAW integers only...\n")

try:
    while True:
        line = ser.readline().decode().strip()
        if line:
            print("RX:", line)  # THIS ensures you see data instantly

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

        time.sleep(0.002)

except KeyboardInterrupt:
    print("\n🛑 Stopped reader.")
finally:
    ser.close()
