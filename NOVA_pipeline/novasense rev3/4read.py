import serial
import time
import matplotlib.pyplot as plt
import re

# 4 grid cells you want to track
TARGETS = [
    (0, 0),  # → plot 1
    (0, 1),  # → plot 2
    (0, 2),  # → plot 3
    (0, 3),  # → plot 4
]


# ----- CONFIG -----
PORT = "/dev/tty.usbmodem212401"
BAUD = 115200
WINDOW = 60        # rolling points stored per plot
REDRAW_HZ = 0.1    # minimum pause between redraw batches (~10Hz)

AUTOSCALE_PERIOD = 0.5  # rescale Y every 0.5 sec (~2Hz)
# ------------------

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(1)

pattern = re.compile(r"Row\s*(\d+),\s*Col\s*(\d+)\s*:\s*(\d+)")

# buffers for 4 chosen cells
bufs = [[0]*WINDOW for _ in range(4)]
x = list(range(WINDOW))

plt.ion()
fig, axes = plt.subplots(4, 1, figsize=(6, 8))
lines = []

for i, ax in enumerate(axes):
    (r, c) = TARGETS[i]
    ln, = ax.plot(x, bufs[i])
    ax.set_title(f"Tracking Row {r}, Col {c}")
    ax.set_xlim(0, WINDOW)
    lines.append(ln)

last_autoscale = time.time()
last_redraw = time.time()

while True:
    try:
        ln = ser.readline().decode().strip()
        m = pattern.search(ln)
        if m:
            row = int(m.group(1))
            col = int(m.group(2))
            val = int(m.group(3))

            # Check if this reading matches one of our 4 chosen cells
            for i, (tr, tc) in enumerate(TARGETS):
                if row == tr and col == tc:
                    bufs[i].append(val)
                    del bufs[i][0]

        # Lightweight redraw at ~10Hz in batches
        if time.time() - last_redraw > REDRAW_HZ:
            for i, line in enumerate(lines):
                line.set_ydata(bufs[i])

            # Autoscale Y every 0.5sec (2Hz)
            if time.time() - last_autoscale > AUTOSCALE_PERIOD:
                for i, ax in enumerate(axes):
                    y = bufs[i]
                    ymin, ymax = min(y), max(y)
                    pad = (ymax - ymin)*0.1 if ymin != ymax else 1
                    ax.set_ylim(ymin - pad, ymax + pad)
                last_autoscale = time.time()

            fig.canvas.draw()
            fig.canvas.flush_events()
            last_redraw = time.time()

        time.sleep(0.002)  # tiny sleep avoids CPU spin

    except KeyboardInterrupt:
        print("Stopped.")
        ser.close()
        break
