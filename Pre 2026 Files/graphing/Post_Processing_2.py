import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from glob import glob

def plot_node_comparison(folder=".", channels=None):
    # Collect all CSV files in folder
    csv_files = sorted(glob(os.path.join(folder, "*.csv")))
    if not csv_files:
        print(f"No CSV files found in folder: {folder}")
        return
    
    print(f"Found {len(csv_files)} CSV files in {folder}\n")
    
    datasets = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            if "timestamp" not in df.columns:
                print(f"Skipping {file}, no 'timestamp' column found.")
                continue
            # Normalize time to start from 0
            df = df.copy()
            df["timestamp"] -= df["timestamp"].min()
            datasets.append((os.path.basename(file), df))
            print(f"Loaded {file} with shape {df.shape}")
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    if not datasets:
        print("No valid datasets to process.")
        return
    
    # If channels not provided, auto-select all except timestamp
    if channels is None:
        channels = [c for c in datasets[0][1].columns if c != "timestamp"]
        print(f"Auto-selected channels: {channels}")
    
    # Color palette
    colors = [
        "#0072B2", "#56B4E9", "#D55E00", "#E69F00",
        "#009E73", "#CC79A7", "#F0E442", "#999999"
    ]
    
    plt.figure(figsize=(15, 10))
    
    # Plot
    for file_idx, (fname, df) in enumerate(datasets):
        for ch_idx, ch in enumerate(channels):
            if ch not in df.columns:
                print(f"Warning: {ch} not in {fname}, skipping.")
                continue
            color = colors[ch_idx % len(colors)]
            linestyle = ["-", "--", ":", "-."][file_idx % 4]  # alternate styles for files
            plt.plot(df["timestamp"], df[ch],
                     linewidth=2, alpha=0.8,
                     color=color, linestyle=linestyle,
                     label=f"{ch} ({fname})")
    
    # Labels and style
    plt.xlabel("Time (s)", fontsize=12)
    plt.ylabel("Capacitance (pF)", fontsize=12)
    plt.title(f"Channel Comparison ({len(datasets)} files)", fontsize=14, fontweight="bold")
    plt.legend(fontsize=10, loc="best")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # === Build statistics box text ===
    stats_text = ""
    for fname, df in datasets:
        stats_text += f"{fname}:\n"
        for ch in channels:
            if ch in df.columns:
                stats_text += (f"  {ch}: "
                               f"{df[ch].mean():.2f}±{df[ch].std():.2f} pF\n")
        stats_text += "\n"
    
    plt.text(0.02, 0.98, stats_text.strip(), transform=plt.gca().transAxes,
             verticalalignment='top', horizontalalignment='left',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
             fontsize=9, family="monospace")
    
    # Save and show
    output_filename = "Single_Hand_Test.png"
    plt.savefig(output_filename, dpi=300, bbox_inches="tight",
                facecolor="white", edgecolor="none", format="png")
    print(f"\nPlot saved as: {output_filename}\n")
    plt.show()
    
    # === Print full summary statistics ===
    print("=== Summary Statistics (Time-offset data) ===\n")
    for fname, df in datasets:
        print(f"File: {fname}")
        print(f"  Data points: {len(df)}")
        print(f"  Duration: {df['timestamp'].max():.2f} seconds")
        for ch in channels:
            if ch in df.columns:
                mean = df[ch].mean()
                std = df[ch].std()
                min_val = df[ch].min()
                max_val = df[ch].max()
                print(f"  {ch}:")
                print(f"    Mean: {mean:.2f} pF")
                print(f"    Std:  {std:.2f} pF")
                print(f"    Min:  {min_val:.2f} pF")
                print(f"    Max:  {max_val:.2f} pF")
        print("-" * 40)

if __name__ == "__main__":
    # Example usage
    plot_node_comparison(
        folder="single_finger_tests", 
        channels=["CH0_pF", "CH1_pF"]
    )
