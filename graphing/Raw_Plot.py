import csv
import os
import matplotlib.pyplot as plt
from cmcrameri import cm
import numpy as np

# === PATHS ===
csvfolder = "data"
data = ["11162025_mux_Node1_CH0_CH1_test2.csv"]
plotfolder = "MUX_plots"

# === CHOOSE CHANNELS TO PLOT ===
# Set to None to plot all channels, or specify a list like [1, 2] for specific channels
channels_to_plot = [1, 2]  # Column indexes (1 = first data channel after time)

# === LOOP THROUGH FILES ===
for csvfilename in data:
    file_path = os.path.join(csvfolder, csvfilename)
    if not os.path.exists(file_path):
        print(f"⚠️ Missing file: {csvfilename}")
        continue
    
    # Create figure
    plt.figure(figsize=(12, 6))
    
    # Load CSV header to detect channels
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
    
    # Determine which channels to plot
    if channels_to_plot is None:
        # Plot all channels
        selected_channels = list(channel_data.keys())
    else:
        # Plot only specified channels
        selected_channels = [ch for ch in channels_to_plot if ch in channel_data]
        if not selected_channels:
            print(f"⚠️ No valid channels selected for {csvfilename}")
            continue
    
    # Generate colors for selected channels
    num_channels = len(selected_channels)
    colors = cm.batlow(np.linspace(0, 1, num_channels))
    
    # Plot selected channels
    for idx, ch in enumerate(selected_channels):
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
    
    # Save plot (uncomment to enable)
    # if not os.path.exists(plotfolder):
    #     os.makedirs(plotfolder)
    # outfile = os.path.join(plotfolder, f"{os.path.splitext(csvfilename)[0]}.png")
    # plt.savefig(outfile, dpi=300)
    # plt.close()
    # print(f"✅ Saved plot → {outfile}")
    
    plt.show()