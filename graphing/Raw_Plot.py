import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from cmcrameri import cm

csvfolder = "diff_pairs"
data = ["20250911_node1_node4_v1.csv", "20250911_node1_node4_v2.csv", "20250911_node1_node4_v3c.csv",
        "20250911_node1_node5_v1.csv", "20250911_node1_node5_v2.csv", "20250911_node1_node5_v3.csv",
        "20250911_node1_node6_v1.csv", "20250911_node1_node6_v2.csv", "20250911_node1_node6_v3.csv",
        "20250911_node2_node4_v1.csv", "20250911_node2_node4_v2.csv", "20250911_node2_node4_v3.csv",
        "20250911_node2_node5_v1.csv", "20250911_node2_node5_v2.csv", "20250911_node2_node5_v3.csv",
        "20250911_node2_node6_v1.csv", "20250911_node2_node6_v2.csv", "20250911_node2_node6_v3.csv",
        "20250911_node3_node4_v1.csv", "20250911_node3_node4_v2.csv", "20250911_node3_node4_v3.csv",
        "20250911_node3_node5_v1.csv", "20250911_node3_node5_v2.csv", "20250911_node3_node5_v3.csv",
        "20250911_node3_node6_v1.csv", "20250911_node3_node6_v2.csv", "20250911_node3_node6_v3.csv"]

plotfolder = "diff_pairs"

channels_to_plot = [3]   # column indexes to plot (0 = time, 1 = first channel, etc.)

colors = cm.batlow(np.linspace(0, 1, len(channels_to_plot)))



for csvfilename in data:
    file_path = os.path.join(csvfolder, csvfilename)
    if not os.path.exists(file_path):
        print(f"⚠️ Missing file: {csvfilename}")
        continue
    plt.figure(figsize=(10, 6))
    # Load raw data
    times = []
    channel_data = {ch: [] for ch in channels_to_plot}

    with open(file_path, "r") as infile:
        csvreader = csv.reader(infile)
        next(csvreader, None)  # skip header
        for row in csvreader:
            try:
                t = float(row[0])
                times.append(t)
                for ch in channels_to_plot:
                    channel_data[ch].append(float(row[ch]))
            except (ValueError, IndexError):
                continue

    if not times:
        print(f"⚠️ No valid data in {csvfilename}")
        continue

    # Normalize time to start at 0
    t0 = times[0] + 1
    times = [t - t0 for t in times]
    channel_name = csvfilename.replace("20250911", "").replace(".csv", "").replace("_", " ")

    # Plot each channel
    for idx, ch in enumerate(channels_to_plot):
        plt.plot(
            times, channel_data[ch],
            label=f"{channel_name}",
            color=colors[idx],
            linewidth=1.2
        )

    plt.xlim(0,120)
    plt.xlabel("Time (s)")
    plt.ylabel("Capacitance (pF)")
    title_name = "Raw Data from Differential Pairs"
    plt.title(title_name)
    plt.legend(loc="upper left")
    plt.grid(False)
    plt.tight_layout()
    outfile = os.path.join(plotfolder, f"{channel_name}.png")
    plt.savefig(outfile, dpi=300)
    plt.close()

# plt.xlim(0,120)
# plt.ylim(100, 600)
