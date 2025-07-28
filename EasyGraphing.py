import serial
import matplotlib.pyplot as plt
from collections import deque
import math

# FDC2214 constants
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)  # ~0.149 Hz per LSB
inductance = 180e-9  # H

def raw_to_capacitance(raw):
    freq = raw * scale_factor
    if freq <= 0:
        return 0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # convert to picofarads

# Serial setup
ser = serial.Serial('COM8', 115200)  # Update COM port if needed
buffer_len = 100

# Create buffers for 4 channels
ch = [deque([0] * buffer_len) for _ in range(4)]

# Plot setup
plt.ion()
fig, ax = plt.subplots()
lines = [ax.plot(ch[i], label=f"CH{i}")[0] for i in range(4)]
ax.legend()

# Live update loop
while True:
    line = ser.readline().decode().strip()
    try:
        raw_values = list(map(int, line.split(",")))
        if len(raw_values) == 4:
            cap_values = [raw_to_capacitance(raw) for raw in raw_values]

            for i in range(4):
                ch[i].append(cap_values[i])
                ch[i].popleft()
                lines[i].set_ydata(ch[i])

            ax.relim()
            ax.autoscale_view()
            plt.pause(0.01)
    except Exception as e:
        # Optional: print(f"Error: {e}") for debugging
        pass
