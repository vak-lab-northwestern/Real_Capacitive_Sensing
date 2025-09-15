import os
import csv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy import signal

# --- Folders ---
csvfolder = "diff_pairs"
plotfolder = "diff_pairs_processed_2"
os.makedirs(plotfolder, exist_ok=True)

channels_to_plot = [3]  # adjust for your channel

# --- PARAMETERS ---
block_length = 10  # seconds per rest/pose segment
n_poses = 5        # number of poses
total_blocks = n_poses * 2 + 1  # rest + alternating rest/pose
rest_baseline_block = 0  # index of first block is baseline rest
compute_overall_std = True  # toggle for computing overall std

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
        # ensure window length is valid for savgol_filter (odd and <= len)
        wl = min(21, len(v_interp) if len(v_interp) % 2 == 1 else len(v_interp)-1)
        wl = max(3, wl)  # minimum reasonable window
        v_smooth = signal.savgol_filter(v_interp, wl, 1)  # Savitzky–Golay
        aligned_vals.append(v_smooth)
    aligned_vals = np.vstack(aligned_vals)

    # --- Truncate to 110 s max ---
    mask = common_t <= 110
    common_t = common_t[mask]
    aligned_vals = aligned_vals[:, mask]

    # --- Compute ΔC relative to baseline ---
    dt = np.mean(np.diff(common_t))
    block_samples = int(block_length / dt)
    if block_samples <= 0:
        block_samples = 1  # safety

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
    all_pose_vals = []
    for i in range(1, total_blocks, 2):  # odd blocks = poses
        block = delta_vals[:, i * block_samples:(i + 1) * block_samples]
        if block.size == 0:
            continue
        pose_mean = block.mean()
        pose_std = block.std()
        pose_num = (i + 1) // 2
        summary_rows.append([cond, pose_num, pose_mean, pose_std])
        all_pose_vals.append(block.flatten())

    # --- Compute overall std across all pose blocks ---
    if compute_overall_std and all_pose_vals:
        all_pose_vals = np.concatenate(all_pose_vals)
        overall_pose_std = all_pose_vals.std()
        summary_rows.append([cond, "Overall", np.nan, overall_pose_std])

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(common_t, mean_trace, color="blue", lw=1.5, label=f"{cond} mean")
    ax.fill_between(common_t, min_trace, max_trace,
                    color="blue", alpha=0.2, label="min–max")

    # --- Y-lim span = 700 (keeps consistent vertical span) ---
    ymin, ymax = mean_trace.min(), mean_trace.max()
    center = (ymin + ymax) / 2
    ax.set_ylim(center - 400, center + 400)

    # --- Gray vertical lines every 10s ---
    for x in range(0, 111, 10):
        ax.axvline(x=x, color="gray", linestyle="--", linewidth=1, alpha=0.6)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ΔC (pF)")
    ax.set_title("Δ Capacitance vs Time")
    ax.legend(loc="upper left")
    plt.tight_layout()

    outfile = os.path.join(plotfolder, f"{cond}_processed.png")
    plt.savefig(outfile, dpi=300)
    plt.close()

# --- Save summary table (pose-level) ---
summary_df = pd.DataFrame(summary_rows, columns=["Condition", "Pose", "Mean ΔC (pF)", "Std ΔC (pF)"])
summary_file = os.path.join(plotfolder, "summary.csv")
summary_df.to_csv(summary_file, index=False)
print(f"\n✅ Summary saved to {summary_file}")

# --- Post-process: Compute SNR summary ---
df = pd.read_csv(summary_file)
df_numeric = df[pd.to_numeric(df["Pose"], errors="coerce").notna()].copy()
df_numeric["Pose"] = df_numeric["Pose"].astype(int)

# Compute SNR per pose
df_numeric["SNR"] = df_numeric["Mean ΔC (pF)"] / df_numeric["Std ΔC (pF)"]

rows = []
for cond, group in df_numeric.groupby("Condition"):
    avg_snr = group["SNR"].mean()
    lowest_snr = group.loc[group["SNR"].idxmin(), ["Pose", "SNR"]]
    highest_std = group.loc[group["Std ΔC (pF)"].idxmax(), ["Pose", "Std ΔC (pF)"]]

    rows.append({
        "Condition": cond,
        "Average SNR": avg_snr,
        "Lowest SNR Pose": int(lowest_snr["Pose"]),
        "Lowest SNR Value": lowest_snr["SNR"],
        "Highest Std Pose": int(highest_std["Pose"]),
        "Highest Std Value": highest_std["Std ΔC (pF)"]
    })

snr_summary = pd.DataFrame(rows)

# --- Save & Show ---
snr_summary_file = os.path.join(plotfolder, "snr_summary.csv")
snr_summary.to_csv(snr_summary_file, index=False)

print(f"\n✅ SNR summary saved to {snr_summary_file}")
print("\n📊 SNR Summary Table:")
print(snr_summary.to_string(index=False, float_format="%.2f"))

# --- Save table as PNG ---
fig, ax = plt.subplots(figsize=(10, len(snr_summary) * 0.6 + 1))
ax.axis("off")

table = ax.table(
    cellText=snr_summary.round(2).values,
    colLabels=snr_summary.columns,
    cellLoc="center",
    loc="center"
)

table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.1, 1.3)

plt.tight_layout()
plt.savefig(os.path.join(plotfolder, "snr_summary_table.png"), dpi=300)
plt.close()

print(f"📈 Table figure saved to {os.path.join(plotfolder, 'snr_summary_table.png')}")
