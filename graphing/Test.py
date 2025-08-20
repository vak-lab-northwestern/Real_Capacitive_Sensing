import csv
import matplotlib.pyplot as plt
import numpy as np

csvfolder = 'data'
csvfilename = 'FDC2214_Force_Test_CH4.csv'
file_path = f"{csvfolder}/{csvfilename}"

times = []
values = []
channel = 1

with open(file_path, 'r') as infile:
    csvreader = csv.reader(infile)
    next(csvreader)  # skip header row
    for row in csvreader:
        try:
            times.append(float(row[0]))  
            values.append(float(row[channel]))  
        except (ValueError, IndexError):
            times.append(np.nan)
            values.append(np.nan)

times = np.array(times)
values = np.array(values)

plt.figure(figsize=(8, 5))
plt.plot(times, values, label="Column 2 vs Column 1", linewidth=1.5)
plt.xlabel("Time (s)")
plt.ylabel("Value")
plt.title("CSV Plot: Column 1 vs Column 2")
plt.legend()
plt.tight_layout()
plt.show()
