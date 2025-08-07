import csv
from collections import defaultdict
import math
import statistics
import matplotlib.pyplot as plt

# data[channel][time_bin] = list of measurements
data = [defaultdict(list) for _ in range(4)]

start_time = 58

with open('FDC2214DATA4.csv', 'r') as file:
    
    csvreader = csv.reader(file)
    next(csvreader)  
    for row in csvreader:
        try:
            time = float(row[0])
            if time > start_time:
                time_bin = math.floor(time)
                for ch in range(4):
                    measurement = float(row[ch + 1])
                    data[ch][time_bin].append(measurement)
        except (ValueError, IndexError):
            continue

filtered_averages = [{} for _ in range(4)]

for ch in range(4):
    for time_bin, values in data[ch].items():
        if len(values) < 2:
            continue
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        filtered_values = [v for v in values if (mean - 2 * stdev) <= v <= (mean + 2 * stdev)]
        if filtered_values:
            filtered_avg = sum(filtered_values) / len(filtered_values)
            filtered_averages[ch][time_bin] = filtered_avg

# Write output for each channel
with open('CLEAN4.csv', 'w', newline='') as outfile:
    csvwriter = csv.writer(outfile)
    csvwriter.writerow(['Time', 'Ch0_Avg', 'Ch1_Avg', 'Ch2_Avg', 'Ch3_Avg'])

    # Get all unique time bins across all channels, sorted
    all_time_bins = sorted(set().union(*[fa.keys() for fa in filtered_averages]))
    for time_bin in all_time_bins:
        row = [time_bin]
        for ch in range(4):
            row.append(filtered_averages[ch].get(time_bin, ''))
        csvwriter.writerow(row)



