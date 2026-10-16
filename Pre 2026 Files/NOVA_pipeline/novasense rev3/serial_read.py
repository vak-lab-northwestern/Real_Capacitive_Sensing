import serial
import time
import matplotlib.pyplot as plt
import re

# ----- CONFIG -----
TARGET_ROW = 0
TARGET_COL = 0
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200
WINDOW = 80
AUTOSCALE_RATE = 10  # how many updates between Y rescale
# ------------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(1)

pattern = re.compile(r"Row\s*(\d+),\s*Col\s*(\d+)\s*:\s*(\d+)")

buf = [0]*WINDOW
x = list(range(WINDOW))

plt.ion()  # interactive mode ON
fig, ax = plt.subplots()
line, = ax.plot(x, buf)
ax.set_title(f"Tracking (Row {TARGET_ROW}, Col {TARGET_COL})")
ax.set_xlim(0, WINDOW)

counter = 0

while True:
    try:
        ln = ser.readline().decode().strip()
        m = pattern.search(ln)
        if m:
            row = int(m.group(1))
            col = int(m.group(2))
            val = int(m.group(3))

            if row == TARGET_ROW and col == TARGET_COL:
                buf.append(val)
                del buf[0]

                # update plot data
                line.set_ydata(buf)
                fig.canvas.draw()
                fig.canvas.flush_events()

                counter += 1
                # autoscale Y only every N updates
                if counter % AUTOSCALE_RATE == 0:
                    ymin, ymax = min(buf), max(buf)
                    pad = (ymax - ymin) * 0.1 if ymin != ymax else 1
                    ax.set_ylim(ymin - pad, ymax + pad)

        # sleep a tiny bit when nothing comes in, avoids 100% CPU spin
        time.sleep(0.005)

    except KeyboardInterrupt:
        print("Stopping plotter.")
        ser.close()
        break
