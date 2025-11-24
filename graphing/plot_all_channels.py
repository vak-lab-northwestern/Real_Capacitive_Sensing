import os
import glob
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

def find_csv_by_date(data_dir: str, date_str: str = None) -> str:
    """Find a CSV file by date string (YYYYMMDD). If None, finds yesterday's file. Falls back to most recent CSV."""
    if date_str is None:
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


def plot_all_channels(date_str: str = None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(script_dir, "..", "data"))

    try:
        csv_file = find_csv_by_date(data_dir, date_str)

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

        # Calculate sampling rate for filter design
        time_diff = np.diff(df['timestamp'])
        if len(time_diff) > 0 and np.all(time_diff > 0):
            avg_sample_rate = 1.0 / np.mean(time_diff)
        else:
            avg_sample_rate = 2.5  # Default fallback Hz
            print(f"[WARNING] Unable to estimate sampling rate, using default: {avg_sample_rate:.2f} Hz")
        
        print(f"[INFO] Estimated sampling rate: {avg_sample_rate:.2f} Hz")

        # Apply low-pass filter to all channels
        cutoff_freq = 0.5  # Hz - cutoff frequency for low-pass filter
        nyquist_freq = avg_sample_rate / 2.0
        normal_cutoff = cutoff_freq / nyquist_freq
        
        if normal_cutoff >= 1.0:
            print(f"[WARNING] Cutoff frequency {cutoff_freq} Hz is too high for sample rate {avg_sample_rate:.2f} Hz. Skipping filter.")
            df_filtered = df.copy()
        else:
            # Design Butterworth low-pass filter
            b, a = signal.butter(4, normal_cutoff, btype='low', analog=False)
            
            # Apply filter to each channel
            df_filtered = df.copy()
            for channel in channel_cols:
                filtered_data = signal.filtfilt(b, a, df[channel].values)
                df_filtered[channel] = filtered_data
            
            print(f"[INFO] Applied low-pass filter with cutoff frequency: {cutoff_freq} Hz")

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12), sharex=False)
        color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']

        # Calculate c_0 (baseline) for each channel from first 10 seconds (using filtered data)
        baseline_window = 10.0  # seconds
        baseline_mask = df_filtered['timestamp'] <= baseline_window
        c0_values = {}
        delta_c_over_c0 = {}
        
        for channel in channel_cols:
            baseline_data = df_filtered.loc[baseline_mask, channel]
            if len(baseline_data) > 0:
                c0_values[channel] = baseline_data.mean()
            else:
                # Fallback: use first value if no data in first 10s
                c0_values[channel] = df_filtered[channel].iloc[0]
            
            # Calculate delta_c / c_0 using filtered data
            delta_c = df_filtered[channel] - c0_values[channel]
            delta_c_over_c0[channel] = delta_c / c0_values[channel]

        # First subplot (top-left): Full time range (filtered data)
        for idx, (channel, label) in enumerate(zip(channel_cols, labels)):
            color = color_cycle[idx % len(color_cycle)]
            ax1.plot(df_filtered['timestamp'], df_filtered[channel], linewidth=1.5, alpha=0.85, color=color, label=label)

        ax1.set_ylabel('Capacitance (pF)', fontsize=12)
        ax1.set_title(f'All Channels (Low-Pass Filtered, cutoff={cutoff_freq}Hz)', fontsize=13, fontweight='bold')
        ax1.legend(fontsize=9, ncol=4)
        ax1.grid(True, alpha=0.3)

        # Second subplot (top-right): Zoomed view [0, 300s] (filtered data)
        for idx, (channel, label) in enumerate(zip(channel_cols, labels)):
            color = color_cycle[idx % len(color_cycle)]
            ax2.plot(df_filtered['timestamp'], df_filtered[channel], linewidth=1.5, alpha=0.9, color=color, label=label)

        ax2.set_ylabel('Capacitance (pF)', fontsize=12)
        ax2.set_title('Zoomed View - First 300 seconds (Filtered)', fontsize=13, fontweight='bold')
        ax2.set_xlim([0, 300])
        ax2.set_ylim([350, 360])
        ax2.legend(fontsize=9, ncol=4)
        ax2.grid(True, alpha=0.3)

        # Third subplot (bottom-left): Normalized change (delta_c / c_0) - All channels (from filtered data)
        for idx, (channel, label) in enumerate(zip(channel_cols, labels)):
            color = color_cycle[idx % len(color_cycle)]

            ax3.plot(df_filtered['timestamp'], delta_c_over_c0[channel], linewidth=1.5, alpha=0.9, color=color, label=label)

        ax3.set_xlabel('Time (s)', fontsize=12)
        ax3.set_ylabel('ΔC / C₀', fontsize=12)
        ax3.set_title(f'Normalized Change - All Channels (C₀ from first {baseline_window}s)', fontsize=13, fontweight='bold')
        ax3.legend(fontsize=9, ncol=4)
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

        # Fourth subplot (bottom-right): Normalized change (delta_c / c_0) - CH7 only (from filtered data)
        ch7_channel = 'CH7_pF'
        if ch7_channel in channel_cols:
            ch7_idx = channel_cols.index(ch7_channel)
            ch7_color = color_cycle[ch7_idx % len(color_cycle)]
            ax4.plot(df_filtered['timestamp'], delta_c_over_c0[ch7_channel], linewidth=2.0, alpha=0.9, color=ch7_color, label='CH7')
        else:
            print(f"[WARNING] CH7_pF not found in channels. Available channels: {channel_cols}")

        ax4.set_xlabel('Time (s)', fontsize=12)
        ax4.set_ylabel('ΔC / C₀', fontsize=12)
        ax4.set_title('Normalized Change - CH7 Only (Zoomed 0-300s, Filtered)', fontsize=13, fontweight='bold')
        ax4.set_xlim([0, 300])
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

        duration = df_filtered['timestamp'].iloc[-1] - df_filtered['timestamp'].iloc[0]

        stats_lines = []
        for channel, label in zip(channel_cols, labels):
            mean_val = df_filtered[channel].mean()
            std_val = df_filtered[channel].std()
            min_val = df_filtered[channel].min()
            max_val = df_filtered[channel].max()
            stats_lines.append(
                f'{label}: {mean_val:.2f}±{std_val:.2f} pF  (min={min_val:.2f}, max={max_val:.2f})'
            )

        stats_text = '\n'.join(stats_lines)
        plt.figtext(0.01, 0.01, stats_text, fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        plt.show()

        print("\n=== Summary Statistics (Filtered Data) ===")
        print(f"File: {csv_file}")
        print(f"Data points: {len(df_filtered)}")
        print(f"Time range: {df_filtered['timestamp'].min():.2f} - {df_filtered['timestamp'].max():.2f} seconds")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Low-pass filter cutoff: {cutoff_freq} Hz")

        for channel, label in zip(channel_cols, labels):
            mean_val = df_filtered[channel].mean()
            std_val = df_filtered[channel].std()
            min_val = df_filtered[channel].min()
            max_val = df_filtered[channel].max()
            c0_val = c0_values[channel]
            print(f"\n{label}:")
            print(f"  C₀ (baseline, first {baseline_window}s): {c0_val:.2f} pF")
            print(f"  Mean: {mean_val:.2f} pF")
            print(f"  Std:  {std_val:.2f} pF")
            print(f"  Min:  {min_val:.2f} pF")
            print(f"  Max:  {max_val:.2f} pF")
            print(f"  Range: {max_val - min_val:.2f} pF")
            max_delta_c_over_c0 = delta_c_over_c0[channel].max()
            min_delta_c_over_c0 = delta_c_over_c0[channel].min()
            print(f"  ΔC/C₀ range: [{min_delta_c_over_c0:.4f}, {max_delta_c_over_c0:.4f}]")

        print(f"\nSampling rate: {avg_sample_rate:.2f} Hz")

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print("Please make sure the CSV files exist in the data directory.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Plot all channels from CSV data')
    parser.add_argument('--date', type=str, default=None,
                        help='Date string in YYYYMMDD format (e.g., 11242025). Default: yesterday')
    args = parser.parse_args()
    
    plot_all_channels(args.date)
