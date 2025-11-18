import pandas as pd
import numpy as np
import csv

INPUT = "sample_raw_cap_data.csv"
OUTPUT = "grid_output.csv"

def main():
    df = pd.read_csv(INPUT)

    # Get grid size
    max_r = df["row_index"].max()
    max_c = df["col_index"].max()

    frame_size = max_r * max_c
    total_samples = len(df)

    if total_samples % frame_size != 0:
        print("WARNING: total samples not divisible by frame size")

    num_frames = total_samples // frame_size

    print(f"Detected {max_r}x{max_c} grid")
    print(f"Frame size = {frame_size}")
    print(f"Frames = {num_frames}")

    rows_out = []
    header = ["timestamp"]

    # Build headers a11..aNN
    for r in range(1, max_r+1):
        for c in range(1, max_c+1):
            header.append(f"a{r}{c}")

    # Process frame by frame
    for i in range(num_frames):
        chunk = df.iloc[i*frame_size : (i+1)*frame_size]

        # timestamp is the timestamp of the 1,1 sample
        ts_11 = chunk[(chunk["row_index"]==1) & (chunk["col_index"]==1)]["timestamp"].iloc[0]

        row = [ts_11]

        # fill in grid values
        for r in range(1, max_r+1):
            for c in range(1, max_c+1):
                value = chunk[(chunk["row_index"]==r) & (chunk["col_index"]==c)]["avg"].iloc[0]
                row.append(value)

        rows_out.append(row)

    # write output
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows_out)

    print(f"Saved corrected grid CSV to {OUTPUT}")

if __name__ == "__main__":
    main()
