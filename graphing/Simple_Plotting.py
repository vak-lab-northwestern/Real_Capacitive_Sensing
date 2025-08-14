import csv
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks

csvfilename = 'CLEAN4.csv'
times = []
channel = []

with open(csvfilename, 'r') as infile:
    csvreader = csv.reader(infile)
    next(csvreader)  # skip header
    for row in csvreader:
        try:
            times.append(float(row[0]))
            channel.append(float(row[1]))
        except (ValueError, IndexError):
            times.append(float('nan'))

# Convert to numpy arrays for easier processing
times = np.array(times)
channel = np.array(channel)

# Define baseline (could be min, median, or other reference)
baseline = np.min(channel)

# Find peaks (adjust 'height' threshold as needed)
peaks, _ = find_peaks(channel, height=baseline + 25)

# Plot main signal
plt.figure(figsize=(8, 5))
plt.plot(times, channel, label="CH0", linewidth = 2)

# Plot baseline
plt.axhline(baseline, color='gray', linestyle='--', linewidth=1, label='Baseline')

# Add dotted lines and labels for each peak
for i, p in enumerate(peaks):
    cap_change = channel[p] - baseline
    if i == 0: 
        plt.plot([times[p], times[p]], [baseline, channel[p]], linestyle=':', color='red', label = 'Δ Cap')
    else:
        plt.plot([times[p], times[p]], [baseline, channel[p]], linestyle =':', color='red')
    plt.text(times[p], channel[p] + 0.01,  
             f"{cap_change:.3f}", ha='center', va='bottom', fontsize=10, color='red')

plt.xlabel('Time')
plt.ylabel('Differential Capacitance')
plt.title('Capacitance vs Time with Peak Differences')
plt.legend()
plt.grid(False)
plt.tight_layout()
plt.show()
