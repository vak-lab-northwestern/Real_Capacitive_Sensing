import csv
import os
import matplotlib.pyplot as plt

csvfolder = "data"
data = ["11132025_nomux_Node1_CH0_CH1_test2.csv"]
plotfolder = "MUX_plots"


channels_to_plot = [2,3]   # column indexes to plot (0 = time, 1 = first channel, etc.)

# colors = cm.batlow(np.linspace(0, 1, len(channels_to_plot)))


from cmcrameri import cm
import numpy as np

# === PATHS ===
csvfolder = "data"           # folder containing CSV logs
data = ["11102025_nomux_test1_CH0.csv"]   # replace with your actual filename
plotfolder = "MUX_plots"     # folder for saving plots

# === LOOP THROUGH FILES ===
for csvfilename in data:
    file_path = os.path.join(csvfolder, csvfilename)
    if not os.path.exists(file_path):
        print(f"⚠️ Missing file: {csvfilename}")
        continue

    # Create figure
    plt.figure(figsize=(12, 6))

    # Load CSV header to detect channels automatically
    with open(file_path, "r") as infile:
        csvreader = csv.reader(infile)
        header = next(csvreader)
        num_columns = len(header)
        times = []
        channel_data = {i: [] for i in range(1, num_columns)}  # skip timestamp (col 0)

        for row in csvreader:
            if len(row) != num_columns:
                continue  # skip malformed lines
            try:
                times.append(float(row[0]))
                for i in range(1, num_columns):
                    channel_data[i].append(float(row[i]))
            except ValueError:
                continue

    if not times:
        print(f"⚠️ No valid data in {csvfilename}")
        continue

    # Normalize time
    t0 = times[0]
    times = [t - t0 for t in times]

    # Generate colors automatically
    num_channels = len(channel_data)
    colors = cm.batlow(np.linspace(0, 1, num_channels))

    # Plot all channels
    for idx, ch in enumerate(channel_data):
        plt.plot(
            times,
            channel_data[ch],
            label=header[ch],   # use header names as labels
            linewidth=1.2,
            color=colors[idx]
        )

    # Plot settings
    plt.xlabel("Time (s)")
    plt.ylabel("Capacitance (pF)")
    plt.title(f"Multiplexed FDC2214 Data ({csvfilename})")
    plt.legend(loc="upper left", ncol=4, fontsize=8)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # # Create plot folder if missing
    # if not os.path.exists(plotfolder):
    #     os.makedirs(plotfolder)

    # outfile = os.path.join(plotfolder, f"{os.path.splitext(csvfilename)[0]}.png")
    # plt.savefig(outfile, dpi=300)
    # plt.close()
    # print(f"✅ Saved plot → {outfile}")

# === OLD CODE COMMENTED OUT ===
# channels_to_plot = [0,1,2,...]
# manually specifying channels is no longer needed
