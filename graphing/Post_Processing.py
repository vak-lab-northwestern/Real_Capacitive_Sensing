import os
import csv
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy import signal
import matplotlib.lines as mlines  # ✅ for legend proxy

# --- Folders ---
csvfolder = "single_tests"
plotfolder = "single_plots"
os.makedirs(plotfolder, exist_ok=True)

# --- Parameters ---
channels_to_plot = [1,2]       # adjust for your channel
block_length = 10            # seconds per rest/pose segment
n_poses = 5                  # number of poses
total_blocks = n_poses * 2 + 1   # rest + alternating rest/pose
rest_baseline_block = 0          # index of first block is baseline rest

# --- Exclude bad files ---
exclude_files = {
    # "20250911_node1_node4_v3c.csv",
    # "20250911_node1_node5_v1.csv"
}

# --- Group files by condition ---
conditions = {}
for fname in os.listdir(csvfolder):
    if not fname.endswith(".csv"):
        continue
    if fname in exclude_files:
        print(f"⚠️ Skipping excluded file: {fname}")
        continue
    base = "_".join(fname.split("_")[:-1])
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
        times = np.array(times) - t0
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
        wl = min(21, len(v_interp) if len(v_interp) % 2 == 1 else len(v_interp) - 1)
        wl = max(3, wl)
        v_smooth = signal.savgol_filter(v_interp, wl, 1)
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
        block_samples = 1

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

    # --- Per-pose stats & absolute extrema markers ---
    pose_markers = []  # store times of extrema (abs max)
    for i in range(1, total_blocks, 2):  # skip rest blocks including 0
        block = delta_vals[:, i * block_samples:(i + 1) * block_samples]
        if block.size == 0:
            continue

        pose_num = (i + 1) // 2

        # For each repeat, take the absolute extremum (max of |signal|)
        extrema_per_repeat = []
        for repeat in block:
            max_val = repeat.max()
            min_val = repeat.min()
            extrema_val = max_val if abs(max_val) >= abs(min_val) else min_val
            extrema_per_repeat.append(extrema_val)

        extrema_per_repeat = np.array(extrema_per_repeat)
        pose_val = extrema_per_repeat.mean()
        pose_std = extrema_per_repeat.std()
        pose_snr = abs(pose_val) / pose_std if pose_std > 0 else np.nan

        # --- Marker placement (on block mean) ---
        block_mean = block.mean(axis=0)
        max_idx, min_idx = np.argmax(block_mean), np.argmin(block_mean)
        if abs(block_mean[max_idx]) >= abs(block_mean[min_idx]):
            extremum_idx = max_idx
        else:
            extremum_idx = min_idx

        extremum_time = common_t[i * block_samples + extremum_idx]
        pose_markers.append(extremum_time)

        summary_rows.append([cond, pose_num, pose_val, pose_std, pose_snr])

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(common_t, mean_trace, color="blue", lw=1.5, label=f"{cond} mean")
    ax.fill_between(common_t, min_trace, max_trace,
                    color="blue", alpha=0.2, label="min–max")

    # --- Orange vertical lines at extrema (full height) ---
    for mt in pose_markers:
        ax.axvline(x=mt, color="orange", linestyle="-", linewidth=1.5, alpha=0.9)

    # ✅ Proxy line for legend only (no stray line at 0/-1)
    orange_proxy = mlines.Line2D([], [], color="orange", linewidth=1.5,
                                 linestyle="-", label="Pose sampling point")

    # --- Y-lim span = 800 (more space below) ---
    ymin, ymax = mean_trace.min(), mean_trace.max()
    center = (ymin + ymax) / 2
    ax.set_ylim(center - 400, center + 400)

    # --- Gray vertical lines every 10s ---
    for x in range(10, 111, 10):  # start at 10s, skip 0
        ax.axvline(x=x, color="gray", linestyle="--", linewidth=1, alpha=0.6)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ΔC (pF)")
    ax.set_title("Δ Capacitance vs Time")

    # ✅ Legend with proxy
    handles, labels = ax.get_legend_handles_labels()
    handles.append(orange_proxy)
    ax.legend(handles=handles, loc="upper left")

    plt.tight_layout()
    outfile = os.path.join(plotfolder, f"{cond}_processed.png")
    plt.savefig(outfile, dpi=300)
    plt.close()

# --- Save summary table ---
summary_df = pd.DataFrame(
    summary_rows,
    columns=["Condition", "Pose", "Abs Max ΔC (pF)", "Std ΔC (pF)", "SNR"]
)
summary_file = os.path.join(plotfolder, "summary.csv")
summary_df.to_csv(summary_file, index=False)
print(f"\n✅ Summary saved to {summary_file}")

# --- Post-process: SNR summary ---
rows = []
for cond, group in summary_df.groupby("Condition"):
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
