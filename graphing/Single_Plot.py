import csv
import os
import math
import statistics
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from cmcrameri import cm

csvfolder = "data"
plotfolder = "poses"

pose_files = ["test8.csv"]

channels_to_plot = [1]   

colors = cm.batlow(np.linspace(0, 1, 8))

plt.figure(figsize=(10, 6))

for csvfilename in pose_files:
    file_path = os.path.join(csvfolder, csvfilename)
    if not os.path.exists(file_path):
        print(f"⚠️ Missing file: {csvfilename}")
        continue
    
    # Process each channel separately
    for ch_idx, channel_num_index in enumerate(channels_to_plot, start=0):
        binned_data = defaultdict(list)

        with open(file_path, "r") as infile:
            csvreader = csv.reader(infile)
            next(csvreader, None) 
            for row in csvreader:
                try:
                    time = float(row[0])
                    value = float(row[channel_num_index])
                    time_bin = math.floor(time)
                    binned_data[time_bin].append(value)
                except (ValueError, IndexError):
                    continue

        if not binned_data:
            print(f"⚠️ No valid data in {csvfilename} for CH{channel_num_index}")
            continue

        times = sorted(binned_data.keys())
        ch_avg = [statistics.mean(binned_data[t]) for t in times]

        # Slice
        t0 = times[0]
        start = t0
        end = start + 130

        sliced_times, sliced_avg = [], []
        for t, v in zip(times, ch_avg):
            if start <= t < end:
                sliced_times.append(t - start)
                sliced_avg.append(v)

        if not sliced_times:
            print(f"⚠️ Not enough data in {csvfilename} for CH{channel_num_index}")
            continue

        # Plot this channel
        plt.plot(
            sliced_times, sliced_avg,
            label=f"CH{channel_num_index}",
            color=colors[ch_idx],
            linewidth=2
        )

plt.xlim(0, 110)
plt.ylim(300, 400)
plt.xlabel("Time (s)")
plt.ylabel("Differential Capacitance (pF)")
plt.title("5 Finger Poses (Averaged Cap vs Time)")

# Vertical dotted lines every 10s
for x in range(12, 110, 10):
    plt.axvline(x=x, color="gray", linestyle="--", linewidth=1, alpha=0.6)

plt.legend()
plt.grid(False)
plt.tight_layout()
plt.show()
