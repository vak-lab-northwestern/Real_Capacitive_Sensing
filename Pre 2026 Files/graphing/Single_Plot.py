import csv
import os
import math
import statistics
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from cmcrameri import cm
import re 


csvfolder = "data"
plotfolder = "Array_Plots"

pose_files = [
    # "09022025_Long_Touch_CH1_CH2_Node_2.csv",
    # "09022025_Long_Touch_CH2_Node_3b.csv",
    # "09022025_Long_Touch_CH2_CH3_Node_4.csv",
    # "09022025_Long_Touch_CH3_Node_5.csv",
    # "09022025_Long_Touch_CH3_CH4_Node_6.csv",
    # "09022025_Long_Touch_CH4_Node_7.csv",
    # "09022025_Long_Touch_CH4_CH5_Node_8.csv",
    # "09022025_Long_Touch_CH5_Node_9.csv"
]

colors = cm.batlow(np.linspace(0, 1, 8))  # consistent colors for up to 8 channels

for csvfilename in pose_files:
    file_path = os.path.join(csvfolder, csvfilename)
    if not os.path.exists(file_path):
        print(f"⚠️ Missing file: {csvfilename}")
        continue

    # # Extract channel numbers from filename (e.g. CH1, CH2 → [1, 2])
    # ch_matches = re.findall(r"CH(\d+)", csvfilename)
    # if not ch_matches:
    #     print(f"⚠️ No channel info in {csvfilename}")
    #     continue
    # channels_to_plot = [int(ch) for ch in ch_matches]
    channels_to_plot = [5]   
    # Containers for force alignment
    sliced_times_ref = None
    npoints = None

    # Create a new figure for this file
    plt.figure(figsize=(10, 6))


    # Process and plot each channel
    for channel_num in channels_to_plot:
        
        binned_data = defaultdict(list)

        with open(file_path, "r") as infile:
            csvreader = csv.reader(infile)
            next(csvreader, None)  # skip header
            for row in csvreader:
                try:
                    time = float(row[0])
                    value = float(row[channel_num])  # use the extracted channel index
                    time_bin = math.floor(time)
                    binned_data[time_bin].append(value)
                except (ValueError, IndexError):
                    continue

        if not binned_data:
            print(f"⚠️ No valid data in {csvfilename} for CH{channel_num}")
            continue

        times = sorted(binned_data.keys())
        ch_avg = [statistics.mean(binned_data[t]) for t in times]

        # Slice to first 130 seconds
        t0 = times[0]
        start = t0
        end = start + 600

        sliced_times, sliced_avg = [], []
        for t, v in zip(times, ch_avg):
            if start <= t < end:
                sliced_times.append(t - start)
                sliced_avg.append(v)

        if not sliced_times:
            print(f"⚠️ Not enough data in {csvfilename} for CH{channel_num}")
            continue
        
        if sliced_times_ref is None:
            sliced_times_ref = sliced_times
            npoints = len(sliced_times_ref)

        # Plot this channel
        plt.plot(
            sliced_times, sliced_avg,
            label=f"CH{channel_num}",
            color=colors[(channel_num-1) % len(colors)],
            linewidth=2
        )

    # Formatting per figure
    plt.xlabel("Time (s)")
    plt.ylabel("Capacitance (pF)")
    # Clean up title: remove prefix & .csv
    title_name = csvfilename.replace("09022025_Long_Touch_", "").replace(".csv", "")
    plt.title("Differential Capacitance vs Time")

    # Vertical dotted lines every 10s
    # for x in range(12, 110, 10):
        # plt.axvline(x=x, color="gray", linestyle="--", linewidth=1, alpha=0.6)

    plt.legend(loc="upper left")
    plt.grid(False)
    plt.tight_layout()
    # outfile = os.path.join(plotfolder, f"{title_name}.png")
    # plt.savefig(outfile, dpi=300)
    # plt.close()
    plt.show()

    # if sliced_times_ref is not None:
    # # 3 cycles of sinusoidal force between 0 and 10 N
    #     cycles = 3
    #     force = 5 * (1 - np.cos(2 * np.pi * cycles * np.linspace(0, 1, npoints)))  # 0→10 N sinusoidal

    #     # Make sure lengths match
    #     force = force[:npoints]

    #     plt.figure(figsize=(10, 4))
    #     plt.plot(sliced_times_ref, force, color="red", linewidth=2)
    #     plt.ylim(0, 11)
    #     plt.xlabel("Time (s)")
    #     plt.ylabel("Force (N)")
    #     plt.title(f"Force vs Time — {title_name}")
    #     plt.grid(True, alpha=0.4)
    #     plt.tight_layout()
    #     outfile = os.path.join(plotfolder, f"{title_name}_Force.png")
    #     plt.savefig(outfile, dpi=300)
    #     plt.close()
    #     plt.show()

