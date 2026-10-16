import csv
import os
import math
import statistics
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from cmcrameri import cm

csvfolder = "data"
plotfolder = "MUX_Plots"

# List your 3 test files here
test_files = [
    "11132025_nomux_Node1_CH0_CH1_test1.csv",
    "11132025_nomux_Node1_CH0_CH1_test2.csv",
    "11132025_nomux_Node1_CH0_CH1_test3.csv"
]

# Channels to plot
channels_to_plot = [0, 1]

# Duration to plot (seconds)
duration = 600

# Function to read and bin data from a single file
def read_and_bin_file(file_path, channel_num, duration):
    """Read CSV and return time-binned averages for specified channel"""
    binned_data = defaultdict(list)
    
    with open(file_path, "r") as infile:
        csvreader = csv.reader(infile)
        next(csvreader, None)  # skip header
        for row in csvreader:
            try:
                time = float(row[0])
                value = float(row[channel_num])
                time_bin = math.floor(time)
                binned_data[time_bin].append(value)
            except (ValueError, IndexError):
                continue
    
    if not binned_data:
        return None, None
    
    times = sorted(binned_data.keys())
    averages = [statistics.mean(binned_data[t]) for t in times]
    
    # Slice to specified duration
    t0 = times[0]
    start = t0
    end = start + duration
    
    sliced_times, sliced_avg = [], []
    for t, v in zip(times, averages):
        if start <= t < end:
            sliced_times.append(t - start)
            sliced_avg.append(v)
    
    return sliced_times, sliced_avg


# Dictionary to store data from all files: {channel: [file1_data, file2_data, file3_data]}
channel_data = {ch: [] for ch in channels_to_plot}

# Read all files
for filename in test_files:
    file_path = os.path.join(csvfolder, filename)
    if not os.path.exists(file_path):
        print(f"⚠️ Missing file: {filename}")
        continue
    
    print(f"Reading {filename}...")
    for channel_num in channels_to_plot:
        times, values = read_and_bin_file(file_path, channel_num, duration)
        if times is not None:
            channel_data[channel_num].append((times, values))
        else:
            print(f"⚠️ No valid data for CH{channel_num} in {filename}")

# Average across files for each channel
colors = cm.batlow(np.linspace(0, 1, max(channels_to_plot) + 1))
plt.figure(figsize=(10, 6))

for channel_num in channels_to_plot:
    file_data = channel_data[channel_num]
    
    if not file_data:
        print(f"⚠️ No data collected for CH{channel_num}")
        continue
    
    # Find the minimum length across all files for this channel
    min_length = min(len(times) for times, _ in file_data)
    
    # Truncate all data to the minimum length and collect values
    times_ref = file_data[0][0][:min_length]
    all_values = []
    
    for times, values in file_data:
        all_values.append(values[:min_length])
    
    # Calculate mean and standard deviation across files
    all_values = np.array(all_values)
    mean_values = np.mean(all_values, axis=0)
    std_values = np.std(all_values, axis=0)
    
    # Plot mean with shaded standard deviation
    plt.plot(
        times_ref, mean_values,
        label=f"CH{channel_num} (n={len(file_data)})",
        color=colors[channel_num],
        linewidth=2
    )
    
    plt.fill_between(
        times_ref,
        mean_values - std_values,
        mean_values + std_values,
        color=colors[channel_num],
        alpha=0.2
    )

# Formatting
plt.xlabel("Time (s)", fontsize=12)
plt.ylabel("Capacitance (pF)", fontsize=12)
plt.title("Average Single-Ended Capacitance vs Time (3 Trials)", fontsize=14)
plt.legend(loc="upper left")
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Save and show
os.makedirs(plotfolder, exist_ok=True)
outfile = os.path.join(plotfolder, "averaged_channels.png")
plt.savefig(outfile, dpi=300)
print(f"✓ Plot saved to {outfile}")
plt.show()