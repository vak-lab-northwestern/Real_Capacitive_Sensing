import csv
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks

csvfilename = 'FDC2214_Force_Test_CH4_CH5.csv'
times = []
ch1 = []  
ch2 = []  

channel_num = 5
channel_num_2 = 6

with open(csvfilename, 'r') as infile:
    csvreader = csv.reader(infile)
    next(csvreader)  # skip header
    for row in csvreader:
        try:
            times.append(float(row[0]))
            ch1.append(float(row[channel_num]))
            ch2.append(float(row[channel_num_2]))
        except (ValueError, IndexError):
            times.append(float('nan'))
            ch1.append(np.nan)
            ch2.append(np.nan)

# Convert to numpy arrays
times = np.array(times)
ch1 = np.array(ch1)
ch2 = np.array(ch2)

# Define baselines
baseline_ch1 = np.min(ch1)
baseline_ch2 = np.min(ch2)

# Find peaks
peaks_ch1, _ = find_peaks(ch1, height=baseline_ch1 + 20)
peaks_ch2, _ = find_peaks(ch2, height=baseline_ch2 + 20)

# Plot both channels
plt.figure(figsize=(10, 6))

# CH1
plt.plot(times, ch1, label="CH5", linewidth=2)
plt.axhline(baseline_ch1, color='gray', linestyle='--', linewidth=1)
for i, p in enumerate(peaks_ch1):
    cap_change = ch1[p] - baseline_ch1
    plt.plot([times[p], times[p]], [baseline_ch1, ch1[p]], linestyle=':', color='red')
    plt.text(times[p], ch1[p] + 0.01, f"{cap_change:.3f}", ha='center', va='bottom', fontsize=9, color='red')

# CH2
plt.plot(times, ch2, label="CH6", linewidth=2)
plt.axhline(baseline_ch2, color='blue', linestyle='--', linewidth=1)
for i, p in enumerate(peaks_ch2):
    cap_change = ch2[p] - baseline_ch2
    plt.plot([times[p], times[p]], [baseline_ch2, ch2[p]], linestyle=':', color='purple')
    plt.text(times[p], ch2[p] + 0.01, f"{cap_change:.3f}", ha='center', va='bottom', fontsize=9, color='purple')

plt.xlabel('Time')
plt.ylabel('Differential Capacitance')
plt.title('Capacitance vs Time with Peak Differences (CH5 & CH6)')
plt.legend()
plt.grid(False)
plt.tight_layout()
plt.show()
