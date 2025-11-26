#!/usr/bin/env python3
"""
Pressure Map Demo Script (Version 3)
Demonstrates creating pressure maps from capacitance data using a 4x4 contact node mesh.

This script:
1. Creates a 4x4 mesh of contact nodes
2. Loads capacitance data from CSV files
3. Maps capacitance values to mesh nodes
4. Creates interpolated pressure maps
5. Visualizes the results

Usage:
    python pressure_map_3.py
    python pressure_map_3.py --csv-file <filename>
    python pressure_map_3.py --date-pattern 10122025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
import glob
import os
import argparse
import sys

# Import functions from create_pressure_map.py
try:
    from create_pressure_map import create_4x4_mesh, visualize_mesh
except ImportError:
    print("[ERROR] Could not import from create_pressure_map.py")
    print("[ERROR] Make sure create_pressure_map.py is in the same directory")
    sys.exit(1)


def load_capacitance_data(csv_file):
    """
    Load capacitance data from a CSV file.
    
    Args:
        csv_file: Path to CSV file with capacitance data
        
    Returns:
        df: DataFrame with capacitance data
    """
    try:
        df = pd.read_csv(csv_file)
        print(f"[INFO] Loaded data from {os.path.basename(csv_file)}")
        print(f"[INFO] Data shape: {df.shape}")
        print(f"[INFO] Columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"[ERROR] Failed to load {csv_file}: {e}")
        return None


def map_channels_to_nodes(channel_data, channel_mapping=None):
    """
    Map capacitance channel data to 4x4 mesh nodes.
    
    Args:
        channel_data: Dictionary or Series with channel values (e.g., {'CH0_pF': 100, 'CH1_pF': 150})
        channel_mapping: Optional dict mapping channel names to node IDs (0-15)
                         If None, uses default mapping
        
    Returns:
        node_values: Array of 16 values corresponding to each node
    """
    # Default mapping: channels to nodes (can be customized)
    if channel_mapping is None:
        # Simple mapping: CH0->Node0, CH1->Node1, etc. (up to 16 channels)
        channel_mapping = {f'CH{i}_pF': i for i in range(16)}
    
    node_values = np.zeros(16)  # 4x4 = 16 nodes
    
    for channel_name, value in channel_data.items():
        if channel_name in channel_mapping:
            node_id = channel_mapping[channel_name]
            if 0 <= node_id < 16:
                node_values[node_id] = value
    
    return node_values


def create_pressure_map(node_positions, node_values, method='cubic', resolution=100):
    """
    Create an interpolated pressure map from node values.
    
    Args:
        node_positions: Array of (x, y) positions for nodes
        node_values: Array of pressure/capacitance values for each node
        method: Interpolation method ('linear', 'cubic', 'nearest')
        resolution: Resolution of the output grid
        
    Returns:
        xi, yi, zi: Grid coordinates and interpolated values
    """
    # Create a fine grid for interpolation
    x_min, x_max = node_positions[:, 0].min(), node_positions[:, 0].max()
    y_min, y_max = node_positions[:, 1].min(), node_positions[:, 1].max()
    
    # Add some padding
    padding = 0.5
    xi = np.linspace(x_min - padding, x_max + padding, resolution)
    yi = np.linspace(y_min - padding, y_max + padding, resolution)
    xi_grid, yi_grid = np.meshgrid(xi, yi)
    
    # Interpolate values
    zi = griddata(
        node_positions,
        node_values,
        (xi_grid, yi_grid),
        method=method,
        fill_value=0
    )
    
    return xi, yi, zi


def visualize_pressure_map(node_positions, node_values, xi, yi, zi, 
                           timestamp=None, save_path=None):
    """
    Visualize the pressure map with node positions overlaid.
    
    Args:
        node_positions: Array of (x, y) positions for nodes
        node_values: Array of values for each node
        xi, yi, zi: Grid coordinates and interpolated values
        timestamp: Optional timestamp to display
        save_path: Optional path to save the figure
    """
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot the interpolated pressure map
    im = ax.contourf(xi, yi, zi, levels=20, cmap='hot', alpha=0.8)
    ax.contour(xi, yi, zi, levels=20, colors='black', alpha=0.3, linewidths=0.5)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Capacitance (pF)', rotation=270, labelpad=20)
    
    # Plot node positions with values
    scatter = ax.scatter(node_positions[:, 0], node_positions[:, 1], 
                        s=500, c=node_values, cmap='hot', 
                        edgecolors='black', linewidths=2, 
                        vmin=node_values.min(), vmax=node_values.max(),
                        zorder=5)
    
    # Label nodes with their values
    for i, (x, y) in enumerate(node_positions):
        value = node_values[i]
        ax.text(x, y, f'{value:.1f}', ha='center', va='center',
                fontsize=9, fontweight='bold', color='white' if value > node_values.mean() else 'black',
                zorder=6)
    
    ax.set_xlabel('X Position (cm)', fontsize=12)
    ax.set_ylabel('Y Position (cm)', fontsize=12)
    
    title = 'Pressure Map from Capacitance Data'
    if timestamp is not None:
        title += f'\nTime: {timestamp:.2f} s'
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[INFO] Pressure map saved to {save_path}")
    
    plt.show()
    
    return fig


def process_time_series(csv_file, node_positions, output_dir=None):
    """
    Process a time series of capacitance data and create pressure maps.
    
    Args:
        csv_file: Path to CSV file with time series data
        node_positions: Array of (x, y) positions for nodes
        output_dir: Optional directory to save output images
    """
    df = load_capacitance_data(csv_file)
    if df is None:
        return
    
    # Extract channel columns
    channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
    
    if not channel_cols:
        print("[ERROR] No channel columns found in CSV file")
        print(f"[ERROR] Available columns: {list(df.columns)}")
        return
    
    print(f"[INFO] Found {len(channel_cols)} channels: {channel_cols}")
    
    # Check if timestamp column exists
    if 'timestamp' not in df.columns:
        print("[WARNING] No 'timestamp' column found, using row index")
        df['timestamp'] = np.arange(len(df))
    
    # Process each time point (or sample at intervals)
    num_samples = min(10, len(df))  # Process up to 10 time points
    sample_indices = np.linspace(0, len(df) - 1, num_samples, dtype=int)
    
    print(f"[INFO] Processing {num_samples} time points...")
    
    for idx in sample_indices:
        row = df.iloc[idx]
        timestamp = row['timestamp']
        
        # Extract channel values
        channel_data = {col: row[col] for col in channel_cols if col in row}
        
        # Map to nodes
        node_values = map_channels_to_nodes(channel_data)
        
        # Create pressure map
        xi, yi, zi = create_pressure_map(node_positions, node_values)
        
        # Visualize
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.basename(csv_file).replace('.csv', '')
            save_path = os.path.join(output_dir, f'{filename}_t{timestamp:.2f}.png')
        else:
            save_path = None
        
        visualize_pressure_map(node_positions, node_values, xi, yi, zi, 
                              timestamp=timestamp, save_path=save_path)


def demo_single_time_point():
    """
    Demo: Create a pressure map from a single time point with sample data.
    """
    print("\n=== Demo: Single Time Point Pressure Map ===")
    
    # Create mesh
    node_positions, node_ids = create_4x4_mesh(spacing=1.0)
    
    # Create sample capacitance data (simulating pressure)
    np.random.seed(42)
    node_values = np.random.rand(16) * 100 + 50  # Random values between 50-150 pF
    
    # Add a "hot spot" in the center
    center_nodes = [5, 6, 9, 10]  # Center 2x2 region
    for node_id in center_nodes:
        node_values[node_id] += 50
    
    print(f"[INFO] Node values range: {node_values.min():.1f} - {node_values.max():.1f} pF")
    
    # Create pressure map
    xi, yi, zi = create_pressure_map(node_positions, node_values, method='cubic')
    
    # Visualize
    visualize_pressure_map(node_positions, node_values, xi, yi, zi, 
                          timestamp=0.0, save_path=None)
    
    print("[INFO] Demo complete!")


def demo_from_csv(csv_file):
    """
    Demo: Create pressure maps from a CSV file.
    
    Args:
        csv_file: Path to CSV file
    """
    print(f"\n=== Demo: Pressure Map from CSV File ===")
    print(f"[INFO] Processing: {csv_file}")
    
    # Create mesh
    node_positions, node_ids = create_4x4_mesh(spacing=1.0)
    
    # Process the CSV file
    process_time_series(csv_file, node_positions, output_dir=None)


def main():
    """Main function to run the demo."""
    parser = argparse.ArgumentParser(description='Pressure Map Demo Script')
    parser.add_argument('--csv-file', type=str, help='Path to CSV file with capacitance data')
    parser.add_argument('--date-pattern', type=str, help='Date pattern to search for CSV files (e.g., 10122025)')
    parser.add_argument('--demo', action='store_true', help='Run demo with sample data')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Pressure Map Demo Script (Version 3)")
    print("=" * 60)
    
    if args.csv_file:
        # Process specific CSV file
        if os.path.exists(args.csv_file):
            demo_from_csv(args.csv_file)
        else:
            print(f"[ERROR] File not found: {args.csv_file}")
            sys.exit(1)
    
    elif args.date_pattern:
        # Find and process files matching date pattern
        pattern = f"{args.date_pattern}_singleconfig8_pressure_cap*_CH*_CH*.csv"
        files = glob.glob(pattern)
        
        # Filter out processed files
        files = [f for f in files if '_filtered' not in f and '_truncated' not in f]
        
        if files:
            print(f"[INFO] Found {len(files)} files matching pattern")
            # Process the first file as an example
            demo_from_csv(files[0])
        else:
            print(f"[ERROR] No files found matching pattern: {pattern}")
            sys.exit(1)
    
    else:
        # Run default demo with sample data
        demo_single_time_point()


if __name__ == "__main__":
    main()

