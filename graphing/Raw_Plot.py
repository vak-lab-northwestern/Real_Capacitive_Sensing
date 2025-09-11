import csv
import os
import numpy as np
import matplotlib.pyplot as plt
#from cmcrameri import cm

csvfolder = "data"
pose_files = ["differential_capacitance_20250911_174036.csv"]

#pose_files = ["Green_Thread_Cap_Pressure_Test_1hz.csv"] 
#pose_files = ["Red_Ployamide_Cap_Pressure_Test_1hz.csv"]
#pose_files = ["Silver_Polyamide_Cap_Pressure_Test_1hz.csv"]

channels_to_plot = [1]   # column indexes to plot (0 = time, 1 = first channel, etc.)

#colors = cm.batlow(np.linspace(0, 1, len(channels_to_plot)))

plt.figure(figsize=(10, 6))

for csvfilename in pose_files:
    file_path = "data/differential_capacitance_20250911_174036.csv"
    # file_path = os.path.join(csvfolder, csvfilename)
    # if not os.path.exists(file_path):
    #     print(f"⚠️ Missing file: {csvfilename}")
    #     continue

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
    t0 = times[0]
    times = [t - t0 for t in times]

    # Plot each channel
    for idx, ch in enumerate(channels_to_plot):
        plt.plot(
            times, channel_data[ch],
            label=f"CH{ch}",
            #color=colors[idx],
            linewidth=1.2
        )

plt.xlabel("Time (s)")
plt.ylabel("Capacitance (pF)")
plt.title("8:1 MUX Single-Ended Capacitance Readings")
plt.legend(loc="upper left")
plt.grid(False)
plt.tight_layout()
plt.show()
