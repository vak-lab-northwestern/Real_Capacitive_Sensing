import csv
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks


csvfolder = 'data'
csvfilename = 'Full_Clasp.csv'
file_path = f"{csvfolder}/{csvfilename}"
times = []
ch1 = []  


channel_num_index = 1
ch_count = 1

with open(file_path, 'r') as infile:
    csvreader = csv.reader(infile)
    next(csvreader)  # skip header
    for row in csvreader:
        try:
            times.append(float(row[0]))
            ch1.append(float(row[channel_num_index]))
        except (ValueError, IndexError):
            times.append(float('nan'))
            ch1.append(np.nan)

# Convert to numpy arrays
times = np.array(times)
ch1 = np.array(ch1)


# Define baselines
baseline_ch1 = np.min(ch1)

# Find peaks
peaks_ch1, _ = find_peaks(ch1, height=baseline_ch1 + 20)

# Plot both channels
plt.figure(figsize=(10, 6))

# CH1
plt.plot(times, ch1, label="CH1", linewidth=2)
plt.axhline(baseline_ch1, color='gray', linestyle='--', linewidth=1)
for i, p in enumerate(peaks_ch1):
    cap_change = ch1[p] - baseline_ch1
    plt.plot([times[p], times[p]], [baseline_ch1, ch1[p]], linestyle=':', color='red')
    plt.text(times[p], ch1[p] + 0.01, f"{cap_change:.3f}", ha='center', va='bottom', fontsize=9, color='red')


plt.xlabel('Time (s)')
plt.ylabel('Differential Capacitance (pF)')
plt.title('Full Clasp (Cap vs Time)')
plt.legend()
plt.grid(False)
plt.tight_layout()
plt.show()
