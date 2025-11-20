import pandas as pd
import numpy as np

INPUT_FILE = "data/11182025_nomux_Node64_CH0_CH1_test3.csv"
OUTPUT_FILE = "processed/11182025_nomux_Node64_CH0_CH1_test3_processed.csv"

# =====================================
# USER SETTINGS — choose target node
# =====================================
TARGET_ROW = 8    # <-- change this
TARGET_COL = 8    # <-- change this

# =====================================
# Load CSV
# =====================================
df = pd.read_csv(INPUT_FILE)

timestamp = df.iloc[:, 0]

# Normalize timestamp to start at zero
t0 = timestamp.iloc[0]
timestamp_norm = timestamp - t0

# channels
ch0 = df.iloc[:, 1]
ch1 = df.iloc[:, 2]

# baseline = first row
baseline_ch0 = ch0.iloc[0]
baseline_ch1 = ch1.iloc[0]
baseline_avg = (baseline_ch0 + baseline_ch1) / 2

# current avg each row
current_avg = (ch0 + ch1) / 2

# percent change
percent_change = (current_avg - baseline_avg) / baseline_avg

# =====================================
# Build 8×8 grid columns (a11..a88)
# =====================================
grid_cols = {}

for r in range(1, 9):
    for c in range(1, 9):
        name = f"a{r}{c}"
        if r == TARGET_ROW and c == TARGET_COL:
            grid_cols[name] = percent_change
        else:
            grid_cols[name] = np.zeros(len(df))

# =====================================
# Construct output DataFrame
# =====================================
out_df = pd.DataFrame({"timestamp": timestamp_norm})

for name in grid_cols:
    out_df[name] = grid_cols[name]

# =====================================
# Save CSV
# =====================================
out_df.to_csv(OUTPUT_FILE, index=False)
print(f"Saved → {OUTPUT_FILE}")
