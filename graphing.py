from serial import Serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from datetime import datetime
import pandas as pd

port_name = "/dev/tty.usbmodem2101"
# run "ls /dev/tty.*" on your own mac to get the correct port name
baud_rate = 115200
plot_window_seconds = 60

device = Serial(port_name, baud_rate, timeout=1)
device.reset_input_buffer()

time_data = []
cap_data = []
start_time = datetime.now()

fig, ax = plt.subplots()
plt.subplots_adjust(bottom=0.2)
ax.set_title("Live FDC2214 Capacitance Data")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Capacitance (pF)")
ax.grid(True)
line, = ax.plot([], [], lw=2)
ax.set_xlim(0, plot_window_seconds)

def stop(event):
    plt.close(fig)

ax_stop = plt.axes([0.8, 0.05, 0.1, 0.075])
btn_stop = Button(ax_stop, 'Stop')
btn_stop.on_clicked(stop)

def update(frame):
    if device.in_waiting > 0:
        try:
            raw_line = device.readline().decode('utf-8').strip()
            cap_val = float(raw_line)
        except:
            return line,

        now = datetime.now()
        t = (now - start_time).total_seconds()
        time_data.append(t)
        cap_data.append(cap_val)
        line.set_data(time_data, cap_data)
        if t > plot_window_seconds:
            ax.set_xlim(t - plot_window_seconds, t)
        ax.set_ylim(min(cap_data) * 0.9, max(cap_data) * 1.1)
    return line,

ani = FuncAnimation(fig, update, blit=True, interval=100)
plt.show()

df = pd.DataFrame({'Time_s': time_data, 'Capacitance_pF': cap_data})
df.to_csv('fdc2214_data_log_20250729.csv', index=False)
print("Data saved to fdc2214_data_log.csv")
