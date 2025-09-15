import os
import csv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy import signal

# --- Folders ---
csvfolder = "diff_pairs"
plotfolder = "diff_pairs_processed"
os.makedirs(plotfolder, exist_ok=True)

channels_to_plot = [3]  # adjust for your channel

# --- PARAMETERS ---
block_length = 10  # seconds per rest/pose segment
n_poses = 5        # number of poses
total_blocks = n_poses * 2 + 1  # rest + alternating rest/pose
rest_baseline_block = 0  # index of first block is baseline rest

# --- Exclude bad files ---
exclude_files = {
    "20250911_node1_node4_v3c.csv",
    "20250911_node1_node5_v1.csv"
}

# --- Group files by condition ---
conditions = {}
for fname in os.listdir(csvfolder):
    if not fname.endswith(".csv"):
        continue
    if fname in exclude_files:
        print(f"⚠️ Skipping excluded file: {fname}")
        continue
    base = "_".join(fname.split("_")[:-1])  # condition = everything except last token
    conditions.setdefault(base, []).append(fname)

# --- Collect summary results ---
summary_rows = []

for cond, files in conditions.items():
    print(f"\nProcessing condition: {cond}")
    all_repeats = []

    # --- Load repeats ---
    for f in sorted(files):
        filepath = os.path.join(csvfolder, f)
        times, vals = [], []

        with open(filepath) as infile:
            reader = csv.reader(infile)
            next(reader, None)  # skip header
            for row in reader:
                try:
                    t = float(row[0])
                    v = float(row[channels_to_plot[0]])
                    times.append(t)
                    vals.append(v)
                except:
                    continue

        if len(times) == 0:
            continue

        t0 = times[0]
        times = np.array(times) - t0  # normalize start to 0
        vals = np.array(vals)
        all_repeats.append((times, vals))

    if len(all_repeats) < 2:
        print("⚠️ Not enough repeats for condition")
        continue

    # --- Align x ranges across repeats ---
    t_min = max(rep[0][0] for rep in all_repeats)
    t_max = min(rep[0][-1] for rep in all_repeats)
    n_points = min(len(rep[0]) for rep in all_repeats)
    common_t = np.linspace(t_min, t_max, n_points)

    # --- Interpolate & smooth each repeat ---
    aligned_vals = []
    for t, v in all_repeats:
        v_interp = np.interp(common_t, t, v)
        v_smooth = signal.savgol_filter(v_interp, 20, 1)  # Savitzky–Golay
        aligned_vals.append(v_smooth)
    aligned_vals = np.vstack(aligned_vals)

    # --- Truncate to 110 s max ---
    mask = common_t <= 110
    common_t = common_t[mask]
    aligned_vals = aligned_vals[:, mask]

    # --- Compute ΔC relative to baseline ---
    dt = np.mean(np.diff(common_t))
    block_samples = int(block_length / dt)

    # Break into blocks
    blocks = []
    for i in range(total_blocks):
        start = i * block_samples
        end = min((i + 1) * block_samples, aligned_vals.shape[1])
        blocks.append(aligned_vals[:, start:end])

    # Baseline (first rest block)
    baseline = blocks[rest_baseline_block].mean()

    # ΔC
    delta_vals = aligned_vals - baseline
    mean_trace = delta_vals.mean(axis=0)
    min_trace = delta_vals.min(axis=0)
    max_trace = delta_vals.max(axis=0)

    # --- Per-pose stats ---
    pose_stds = []
    for i in range(1, total_blocks, 2):  # odd blocks = poses
        block = delta_vals[:, i * block_samples:(i + 1) * block_samples]
        pose_mean = block.mean()
        pose_std = block.std()
        pose_num = (i + 1) // 2
        summary_rows.append([cond, pose_num, pose_mean, pose_std])
        pose_stds.append(pose_std)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(common_t, mean_trace, color="blue", lw=1.5, label=f"{cond} mean")
    ax.fill_between(common_t, min_trace, max_trace,
                    color="blue", alpha=0.2, label="min–max")

    # Annotate per-pose std
    for pose_idx, std_val in enumerate(pose_stds, start=1):
        xpos = (pose_idx * 2 - 1 + 0.5) * block_length
        ypos = mean_trace.max() * 1.05
        ax.text(xpos, ypos, f"σ={std_val:.1f} pF",
                ha="center", va="bottom", fontsize=9, color="red")

    # --- Y-lim span = 700 ---
    ymin, ymax = mean_trace.min(), mean_trace.max()
    center = (ymin + ymax) / 2
    ax.set_ylim(center - 350, center + 400)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ΔC (pF)")
    ax.set_title("Δ Capacitance vs Time")
    ax.legend(loc="upper left")
    plt.tight_layout()

    outfile = os.path.join(plotfolder, f"{cond}_processed.png")
    plt.savefig(outfile, dpi=300)
    plt.close()

# --- Save summary table ---
summary_df = pd.DataFrame(summary_rows, columns=["Condition", "Pose", "Mean ΔC (pF)", "Std ΔC (pF)"])
summary_file = os.path.join(plotfolder, "summary.csv")
summary_df.to_csv(summary_file, index=False)
print(f"\n✅ Summary saved to {summary_file}")
