import serial
import time
import matplotlib.pyplot as plt
from collections import deque

# Serial connection
ser = serial.Serial("/dev/tty.usbmodem21101", 115200, timeout=1)

# LPF coefficient (exponential IIR)
alpha = 0.35
filtered = 0
initialized = False

# Data buffers for plotting
t_buffer = deque(maxlen=200)
raw_buffer = deque(maxlen=200)
filt_buffer = deque(maxlen=200)

plt.ion()

# Create figure
fig, ax = plt.subplots()

while True:
    line = ser.readline().decode().strip()

    if not line:
        continue

    try:
        raw = float(line)

        # initialize
        if not initialized:
            filtered = raw
            initialized = True
        else:
            filtered = alpha * raw + (1 - alpha) * filtered

        # save data
        t_buffer.append(time.time())
        raw_buffer.append(raw)
        filt_buffer.append(filtered)

        # clear + replot
        ax.clear()
        # ax.plot(t_buffer, raw_buffer, label="Raw")
        ax.plot(t_buffer, filt_buffer, label="Filtered")

        # dynamic Y scaling
        y_min = min(min(raw_buffer), min(filt_buffer))
        y_max = max(max(raw_buffer), max(filt_buffer))
        #ax.set_ylim(y_min - 0.8*abs(y_min), y_max + 0.2*abs(y_max))
        ax.set_ylim(y_min, y_max)

        ax.legend()
        fig.canvas.draw()
        fig.canvas.flush_events()

    except ValueError:
        continue

    time.sleep(0.01)
