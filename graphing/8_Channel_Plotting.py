import csv
import matplotlib.pyplot as plt
import numpy as np
from cmcrameri import cm  # cmcrameri colormaps

file = 'data'
csvfilename = 'FDC2214_Force_Test_CH5_CH6.csv'
file_path = f"{file}/{csvfilename}"
times = []
Max_Channel = 9
channels = {i: [] for i in range(1, Max_Channel)}  # raw channels 1–8

with open(file_path, 'r') as infile:
    csvreader = csv.reader(infile)
    next(csvreader)  # skip header
    for row in csvreader:
        try:
            times.append(float(row[0]))
            for i in range(1, Max_Channel):
                channels[i].append(float(row[i]))
        except (ValueError, IndexError):
            times.append(float('nan'))
            for i in range(1, Max_Channel):
                channels[i].append(np.nan)

# Convert to numpy arrays
times = np.array(times)
for i in range(1, Max_Channel):
    channels[i] = np.array(channels[i])

# Custom legend remapping
label_map = {
    7: "CH1",
    6: "CH2",
    # 3: "CH3",
    # 1: "CH4",
    # 5: "CH5",
    # 4: "CH6",
    # 8: "CH7",
    # 2: "CH8",
}

# Plot
plt.figure(figsize=(12, 7))
colors = cm.batlow(np.linspace(0, 3, 8))

for idx, (raw_ch, label) in enumerate(label_map.items()):
    plt.plot(times, channels[raw_ch], label=label, color=colors[idx], linewidth=2)

plt.ylim(300,320)
plt.xlabel('Time (s)')
plt.ylabel('Differential Capacitance (pF)')
plt.title('Capacitance vs Time')
plt.legend(ncol=2)
plt.grid(False)
plt.tight_layout()
plt.show()
