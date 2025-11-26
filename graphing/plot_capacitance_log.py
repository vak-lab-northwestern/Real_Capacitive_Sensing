"""
Plot Capacitance Log Data
Quick plotting script for capacitance log files
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

def plot_capacitance_log(filename):
    """Plot capacitance data from a log file"""
    
    # Check if file exists
    if not os.path.exists(filename):
        print(f"[ERROR] File not found: {filename}")
        return
    
    # Read data
    print(f"[INFO] Reading data from {filename}")
    df = pd.read_csv(filename)
    
    # Get channel columns
    channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
    num_channels = len(channel_cols)
    
    if num_channels == 0:
        print("[ERROR] No capacitance channels found in data")
        return
    
    print(f"[INFO] Found {num_channels} channels: {', '.join(channel_cols)}")
    print(f"[INFO] Data points: {len(df)}")
    print(f"[INFO] Duration: {df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]:.2f} seconds")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Top plot: All channels
    ax1 = axes[0]
    for col in channel_cols:
        ax1.plot(df['timestamp'], df[col], label=col.replace('_pF', ''), linewidth=1.5, alpha=0.8)
    
    ax1.set_xlabel('Time (s)', fontsize=14)
    ax1.set_ylabel('Capacitance (pF)', fontsize=14)
    ax1.set_title(f'Capacitance vs Time - All Channels', fontsize=16, fontweight='bold')
    ax1.legend(ncol=4, loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim([df['timestamp'].min(), df['timestamp'].max()])
    
    # Bottom plot: Zoomed in (first 60 seconds)
    ax2 = axes[1]
    zoom_end = min(60, df['timestamp'].max())
    df_zoom = df[df['timestamp'] <= zoom_end]
    
    for col in channel_cols:
        ax2.plot(df_zoom['timestamp'], df_zoom[col], label=col.replace('_pF', ''), linewidth=1.5, alpha=0.8)
    
    ax2.set_xlabel('Time (s)', fontsize=14)
    ax2.set_ylabel('Capacitance (pF)', fontsize=14)
    ax2.set_title(f'Capacitance vs Time - First 60 seconds (Zoom)', fontsize=16, fontweight='bold')
    ax2.legend(ncol=4, loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim([0, zoom_end])
    
    # Add statistics box
    stats_text = f"Statistics:\n"
    stats_text += f"Duration: {df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]:.1f} s\n"
    stats_text += f"Points: {len(df)}\n"
    stats_text += f"Sample rate: {len(df)/(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]):.2f} Hz\n\n"
    
    for col in channel_cols:
        mean_val = df[col].mean()
        std_val = df[col].std()
        stats_text += f"{col.replace('_pF', '')}: {mean_val:.2f}±{std_val:.2f} pF\n"
    
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            fontsize=10)
    
    plt.tight_layout()
    
    # Save plot
    base_name = os.path.splitext(os.path.basename(filename))[0]
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    output_file = os.path.join(output_dir, f"{base_name}_plot.png")
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"[INFO] Plot saved to {output_file}")
    
    # Show plot
    plt.show()
    
    return fig

if __name__ == "__main__":
    # Default file
    default_file = "/Users/cathdxx/cap-sensing/sensing/data/capacitance_log_20251030_120037.csv"
    
    # Allow command line argument
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = default_file
    
    plot_capacitance_log(filename)


