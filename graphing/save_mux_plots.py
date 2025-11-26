"""
Generate and save plots for capacitance CSV files collected on a given date.
Saves figures into ../MUX_Plots with consistent styling.
No pandas dependency to avoid environment issues.
"""

import os
import glob
import csv
import argparse
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

Y_LIMITS = (350, 400)


def find_csv_files(data_dir: str, date_str: str):
    pattern = os.path.join(data_dir, f"*{date_str}*.csv")
    files = glob.glob(pattern)
    files.sort()
    return files


def load_csv(csv_path: str):
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError(f"No header found in {csv_path}")

        # Timestamp column may be 'timestamp' or 'timestamp_s'
        timestamp_col = None
        for candidate in ['timestamp', 'timestamp_s']:
            if candidate in fieldnames:
                timestamp_col = candidate
                break
        if timestamp_col is None:
            raise KeyError("No 'timestamp' or 'timestamp_s' column")

        channel_cols = [fn for fn in fieldnames if fn.startswith('CH') and fn.endswith('_pF')]
        if not channel_cols:
            raise KeyError(f"No channel columns (CH*_pF) found in {csv_path}")
        channel_cols.sort()

        timestamps = []
        channel_data = {col: [] for col in channel_cols}

        for row in reader:
            try:
                timestamps.append(float(row[timestamp_col]))
                for col in channel_cols:
                    channel_data[col].append(float(row[col]))
            except ValueError:
                continue  # skip malformed rows

    return timestamps, channel_cols, channel_data


def apply_ylim(ax):
    if Y_LIMITS:
        ax.set_ylim(Y_LIMITS)


def plot_csv(csv_path: str, output_dir: str):
    timestamps, channel_cols, channel_data = load_csv(csv_path)
    labels = [col.replace('_pF', '') for col in channel_cols]

    fig, ax = plt.subplots(figsize=(14, 7))
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    for idx, (col, label) in enumerate(zip(channel_cols, labels)):
        color = colors[idx % len(colors)]
        ax.plot(timestamps, channel_data[col], color=color, linewidth=1.5, alpha=0.9, label=label)

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Capacitance (pF)')
    ax.set_title(f'{os.path.basename(csv_path)} - All Channels')
    ax.legend(ncol=min(4, len(labels)))
    ax.grid(True, alpha=0.3)
    apply_ylim(ax)

    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(csv_path))[0]
    out_path = os.path.join(output_dir, f"{base}.png")
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"[INFO] Saved plot -> {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Save plots for capacitance CSV files by date")
    parser.add_argument('--date', default='11102025', help='Date string to match (default: 11102025)')
    parser.add_argument('--data-dir', default='../data', help='Relative path to data directory')
    parser.add_argument('--output-dir', default='../MUX_Plots', help='Relative path to output directory')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(script_dir, args.data_dir))
    output_dir = os.path.normpath(os.path.join(script_dir, args.output_dir))

    files = find_csv_files(data_dir, args.date)
    if not files:
        print(f"[WARNING] No CSV files found for {args.date} in {data_dir}")
        return

    print(f"[INFO] Found {len(files)} file(s) for {args.date}")

    for csv_path in files:
        try:
            plot_csv(csv_path, output_dir)
        except Exception as exc:
            print(f"[ERROR] Failed to plot {csv_path}: {exc}")


if __name__ == '__main__':
    main()
