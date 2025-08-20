import csv
import os
import matplotlib.pyplot as plt
import numpy as np
from cmcrameri import cm

csvfolder = "data"

# List of poses to include (fixed order)
pose_files = [
    "Peace_Sign.csv",
    "Pointer.csv",
    "Index_Pinch.csv",
    "Middle_Pinch.csv",
    "Fingers_Crossed.csv",
    "Fingers_Together.csv",
    "Full_Stretch.csv",
    "Full_Clasp.csv",
]

# Pre-assign colors to poses
colors = cm.batlow(np.linspace(0, 1, len(pose_files)))

plt.figure(figsize=(10, 6))

for idx, csvfilename in enumerate(pose_files):
    file_path = os.path.join(csvfolder, csvfilename)
    if not os.path.exists(file_path):
        continue  # skip missing files
    
    pose = os.path.splitext(csvfilename)[0].replace("_", " ")

    times, ch1 = [], []
    channel_num_index = 1  # using channel 1 (index=1 in CSV)

    # Read CSV file
    with open(file_path, "r") as infile:
        csvreader = csv.reader(infile)
        next(csvreader)  # skip header
        for row in csvreader:
            try:
                times.append(float(row[0]))
                ch1.append(float(row[channel_num_index]))
            except (ValueError, IndexError):
                times.append(np.nan)
                ch1.append(np.nan)

    # Convert to numpy arrays
    times = np.array(times)
    ch1 = np.array(ch1)

    # Plot only the raw curve
    plt.plot(times, ch1, label=pose, color=colors[idx], linewidth=2)

# Final formatting
plt.xlim(10, 35)
plt.ylim(300, 350)
plt.xlabel("Time (s)")
plt.ylabel("Differential Capacitance (pF)")
plt.title("All Poses (Cap vs Time)")
plt.legend()
plt.grid(False)
plt.tight_layout()
plt.show()
