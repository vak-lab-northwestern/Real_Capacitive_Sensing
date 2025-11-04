import csv
import os
import numpy as np
import matplotlib.pyplot as plt
from cmcrameri import cm

csvfolder = "data"
data = ["11042025_MUX_1_1_CH4_CH7_Test2.csv"]
plotfolder = "MUX_plots"


channels_to_plot = [5,8]   # column indexes to plot (0 = time, 1 = first channel, etc.)

# colors = cm.batlow(np.linspace(0, 1, len(channels_to_plot)))



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
    t0 = times[0] + 110
    times = [t - t0 for t in times]
    channel_name = csvfilename.replace("20250911", "").replace(".csv", "").replace("_", " ")

    # Plot each channel
    for idx, ch in enumerate(channels_to_plot):
        raw = idx+4
        num = str(raw)
        plt.plot(
            times, channel_data[ch],
            label=f"{"CH" + num}",
            linewidth=1.2
        )

    # plt.ylim(500,1500)
    plt.xlabel("Time (s)")
    plt.ylabel("Capacitance (pF)")
    title_name = "4x4 MUX Single Config"
    plt.title(title_name)
    plt.legend(loc="upper left")
    plt.grid(False)
    plt.tight_layout()
    # plt.show()
    outfile = os.path.join(plotfolder, f"{channel_name}.png")
    plt.savefig(outfile, dpi=300)
    plt.close()

# plt.xlim(0,120)
# plt.ylim(100, 600)
