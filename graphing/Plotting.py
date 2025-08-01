import csv
from collections import defaultdict
import math
import statistics
import matplotlib.pyplot as plt
# Create 4 sensing units by multiplying channels as specified

# Read the cleaned CSV
times = []
channels = [[] for _ in range(4)]
sensing_units = [[] for _ in range(4)]

with open('CLEAN2.csv', 'r') as infile:
    csvreader = csv.reader(infile)
    next(csvreader)  # skip header
    for row in csvreader:
        try:
            times.append(float(row[0]))
        except (ValueError, IndexError):
            times.append(float('nan'))
        for ch in range(4):
            if ch + 1 < len(row):
                val = row[ch + 1]
                channels[ch].append(float(val) if val != '' else float('nan'))
            else:
                channels[ch].append(float('nan'))

for i in range(len(times)):
    ch0 = channels[0][i]
    ch1 = channels[1][i]
    ch2 = channels[2][i]
    ch3 = channels[3][i]
    sensing_units[0].append(ch0 * ch2)
    sensing_units[1].append(ch0 * ch3)
    sensing_units[2].append(ch1 * ch2)
    sensing_units[3].append(ch1 * ch3)

# --- [2] --- [3] ---
# --- [0] --- [1] ---

# Plot
plt.figure(figsize=(10, 6))
for ch in range(4):
    plt.plot(times, sensing_units[ch], label=f'Unit{ch}_Avg')
plt.xlabel('Time (s)')
plt.ylabel('Filtered Average (pF)')
plt.title('Filtered Units Averages Over Time')
plt.legend()
plt.tight_layout()
plt.show()