import serial
import time
from collections import deque
import math

# ----- CONFIG -----
PORT = "/dev/tty.usbmodem21101"
BAUD = 115200

ALPHA_BASELINE = 0.05  # slow drift when untouched
PRESS_DIP = 6000    # 6000      # detect touch start if value falls by this much compared to prev sample
RELEASE_BAND = 60000   # 3000   # consider released if val is within this of baseline (absolute hysteresis)
WINDOW = 5              # small buffer for recent window stats if needed later
DELTA_DECAY = 0.75      # how fast delta decays back to zero when untouched
# -----------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # let board reset

baseline = None
delta = 0.0
isTouched = False
press_buf = deque(maxlen=WINDOW)

print("🔥 Serial connected. Tracking adaptive baseline only when untouched...\n")

try:
    while True:
        raw_line = ser.readline().decode().strip()
        if not raw_line:
            continue

        # print everything for debug
        print("RX:", raw_line)

        try:
            val = int(raw_line)
        except:
            continue  # skip anything that's not a number

        # push into detection buffer
        press_buf.append(val)

        # initialize baseline on first valid read
        if baseline is None:
            baseline = float(val)
            print("✅ baseline initialized =", baseline)

        # ---- TOUCH DETECTION (on DIP START) ----
        if len(press_buf) > 1:
            prev_val = press_buf[-2]
        else:
            prev_val = val

        if not isTouched and (prev_val - val) > PRESS_DIP:
            isTouched = True
            print("👇 TOUCHED (freeze baseline)")

        # # ---- RELEASE DETECTION (absolute hysteresis) ----
        # if isTouched and abs(baseline - val) < RELEASE_BAND:
        #     isTouched = False
        #     print("☝️ RELEASED (baseline resumes drift)")

        # Only release if we have collected a full WINDOW of samples AND all of them are inside the band
        if isTouched and len(press_buf) == WINDOW and all(abs(baseline - v) < RELEASE_BAND for v in press_buf):
            isTouched = False
            print("☝️ RELEASED (baseline resumes drift)")


        # ---- BASELINE UPDATE (only when UNTOUCHED) ----
        if not isTouched:
            baseline = (1 - ALPHA_BASELINE) * baseline + ALPHA_BASELINE * val

            # sanity reset to avoid collapse
            if baseline < val/20 or baseline > val*20:
                print("⚠️ baseline got wild, resetting to current val")
                baseline = float(val)

        # ---- DELTA UPDATE ----
        if not isTouched:
            # decay back toward 0 when untouched
            delta *= (1 - DELTA_DECAY)
            if abs(delta) < 1:  # clamp tiny noise
                delta = 0.0
        else:
            # real signal when touched
            delta = baseline - val

        # print state
        print(f"val={val}, baseline={baseline:.1f}, delta={int(delta)}, touched={isTouched}")

        time.sleep(0.002)

except KeyboardInterrupt:
    print("\n🛑 Stopped reader.")
finally:
    ser.close()
