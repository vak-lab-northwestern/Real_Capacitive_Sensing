import os
import glob
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def find_yesterday_csv(data_dir: str) -> str:
    """Find a CSV file from yesterday. Falls back to most recent CSV."""
    today = datetime.now().date()
    target_date = today - timedelta(days=1)
    date_str = target_date.strftime("%Y%m%d")

    pattern = os.path.join(data_dir, f"*{date_str}*.csv")
    candidates = glob.glob(pattern)
    if candidates:
        candidates.sort(key=os.path.getmtime, reverse=True)
        print(f"[INFO] Found {len(candidates)} files for {date_str}. Using {os.path.basename(candidates[0])}")
        return candidates[0]

    all_csv = glob.glob(os.path.join(data_dir, "*.csv"))
    if not all_csv:
        raise FileNotFoundError("No CSV files found in data directory")

    all_csv.sort(key=os.path.getmtime, reverse=True)
    print(f"[WARNING] No files found for {date_str}. Using most recent: {os.path.basename(all_csv[0])}")
    return all_csv[0]


def plot_all_channels():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(script_dir, "..", "data"))

    try:
        csv_file = find_yesterday_csv(data_dir)

        print(f"[INFO] Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"[INFO] Data shape: {df.shape}")
        print(f"[INFO] Columns: {df.columns.tolist()}")

        if 'timestamp' not in df.columns:
            raise KeyError("'timestamp' column not found in data")

        channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
        if not channel_cols:
            raise KeyError("No channel columns (CH*_pF) found in data")
        channel_cols.sort()
        labels = [col.replace('_pF', '') for col in channel_cols]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), sharex=True)
        color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']

        for idx, (channel, label) in enumerate(zip(channel_cols, labels)):
            color = color_cycle[idx % len(color_cycle)]
            ax1.plot(df['timestamp'], df[channel], linewidth=1.5, alpha=0.85, color=color, label=label)

        ax1.set_ylabel('Capacitance (pF)', fontsize=12)
        ax1.set_title(f'All Channels - {os.path.basename(csv_file)}', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10, ncol=4)
        ax1.grid(True, alpha=0.3)

        duration = df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
        zoom_duration = min(60, duration)
        zoom_mask = df['timestamp'] <= (df['timestamp'].iloc[0] + zoom_duration)
        df_zoom = df[zoom_mask]

        for idx, (channel, label) in enumerate(zip(channel_cols, labels)):
            color = color_cycle[idx % len(color_cycle)]
            ax2.plot(df_zoom['timestamp'], df_zoom[channel], linewidth=1.5, alpha=0.9, color=color, label=label)

        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Capacitance (pF)', fontsize=12)
        ax2.set_title(f'Zoomed View - First {zoom_duration:.1f} seconds', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10, ncol=4)
        ax2.grid(True, alpha=0.3)

        stats_lines = []
        for channel, label in zip(channel_cols, labels):
            mean_val = df[channel].mean()
            std_val = df[channel].std()
            min_val = df[channel].min()
            max_val = df[channel].max()
            stats_lines.append(
                f'{label}: {mean_val:.2f}±{std_val:.2f} pF  (min={min_val:.2f}, max={max_val:.2f})'
            )

        stats_text = '\n'.join(stats_lines)
        plt.figtext(0.01, 0.01, stats_text, fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.18)
        plt.show()

        print("\n=== Summary Statistics ===")
        print(f"File: {csv_file}")
        print(f"Data points: {len(df)}")
        print(f"Time range: {df['timestamp'].min():.2f} - {df['timestamp'].max():.2f} seconds")
        print(f"Duration: {duration:.2f} seconds")

        for channel, label in zip(channel_cols, labels):
            mean_val = df[channel].mean()
            std_val = df[channel].std()
            min_val = df[channel].min()
            max_val = df[channel].max()
            print(f"\n{label}:")
            print(f"  Mean: {mean_val:.2f} pF")
            print(f"  Std:  {std_val:.2f} pF")
            print(f"  Min:  {min_val:.2f} pF")
            print(f"  Max:  {max_val:.2f} pF")
            print(f"  Range: {max_val - min_val:.2f} pF")

        time_diff = np.diff(df['timestamp'])
        if len(time_diff) > 0 and np.all(time_diff > 0):
            avg_sample_rate = 1.0 / np.mean(time_diff)
            print(f"\nEstimated sampling rate: {avg_sample_rate:.2f} Hz")
        else:
            print("\n[WARNING] Unable to estimate sampling rate (insufficient or invalid timestamps)")

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print("Please make sure the CSV files exist in the data directory.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    plot_all_channels()
