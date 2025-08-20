import csv
import os
import matplotlib.pyplot as plt
import numpy as np
from cmcrameri import cm

csvfolder = "data"
plotfolder = "plots"

# Create output folder if it doesn’t exist
os.makedirs(plotfolder, exist_ok=True)

# List all your possible poses
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

# Assign colors consistently across poses
colors = cm.batlow(np.linspace(0, 1, len(pose_files)))

channel_num_index = 1  # which column to read

for idx, csvfilename in enumerate(pose_files):
    file_path = os.path.join(csvfolder, csvfilename)
    if not os.path.exists(file_path):
        print(f"Skipping missing file: {csvfilename}")
        continue

    pose = os.path.splitext(csvfilename)[0].replace("_", " ")
    plot_title = pose + " (Cap vs Time)"

    times, ch1 = [], []

    # Read CSV
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

    times = np.array(times)
    ch1 = np.array(ch1)

    # Plot for this pose
    plt.figure(figsize=(10, 6))
    plt.plot(times, ch1, label=pose, color=colors[idx], linewidth=2)

    # Auto-fit x, fixed y
    plt.xlim(np.nanmin(times), np.nanmax(times))
    plt.ylim(300, 350)

    plt.xlabel("Time (s)")
    plt.ylabel("Differential Capacitance (pF)")
    plt.title(plot_title)
    plt.legend()
    plt.grid(False)
    plt.tight_layout()

    # Save to file
    outfile = os.path.join(plotfolder, f"{pose}.png")
    plt.savefig(outfile, dpi=300)
    plt.close()

    print(f"Saved {outfile}")
