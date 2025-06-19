import csv
from collections import defaultdict
import math
import statistics

data = defaultdict(list)

with open('fdc2214_data_log.csv', 'r') as file:
    csvreader = csv.reader(file)
    next(csvreader)  
    for row in csvreader:

        try:
            time = float(row[0])         
            measurement = float(row[1])  

            if time > 350:
                time_bin = math.floor(time)
                data[time_bin].append(measurement)

        except (ValueError, IndexError):
            continue

filtered_averages = {}

for time_bin, values in data.items():
    if len(values) < 2:
        continue  
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)

    filtered_values = [v for v in values if (mean - 2 * stdev) <= v <= (mean + 2 * stdev)]

    if filtered_values:
        filtered_avg = sum(filtered_values) / len(filtered_values)
        filtered_averages[time_bin] = filtered_avg

sorted_time_bins = sorted(filtered_averages.keys())

with open('organized_output.csv', 'w', newline='') as outfile:
    csvwriter = csv.writer(outfile)
    csvwriter.writerow(['Time', 'AverageMeasurement']) 

    for time_bin in sorted_time_bins:
        csvwriter.writerow([time_bin, filtered_averages[time_bin]])


