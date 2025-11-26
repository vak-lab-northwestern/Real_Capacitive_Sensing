#!/usr/bin/env python3
"""
Pressure Map Video Generator (Version 4)
Creates an animated video of pressure maps from capacitance data.

This script:
1. Loads capacitance data from CSV files
2. Creates pressure maps for each time point
3. Generates an animated video
4. Extracts 0-20s segment and saves as GIF

Usage:
    python v4pMap.py
    python v4pMap.py --csv-file <filename>
    python v4pMap.py --csv-file <filename> --start-time 0 --end-time 20 --output-gif
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
from scipy.interpolate import griddata
import os
import argparse
import sys
import subprocess

# Import functions from create_pressure_map.py
try:
    from create_pressure_map import create_4x4_mesh
except ImportError:
    print("[ERROR] Could not import from create_pressure_map.py")
    print("[ERROR] Make sure create_pressure_map.py is in the same directory")
    sys.exit(1)


# ============================
# CONFIG
# ============================
DEFAULT_CSV = "10122025_singleconfig8_pressure_cap_CH0_CH7.csv"
OUTPUT_VIDEO = "pressure_map_video.mp4"
OUTPUT_GIF = "pressure_map_0_20s.gif"
FPS = 20
INTERP_METHOD = 'cubic'
RESOLUTION = 100
TIME_START = 0.0
TIME_END = 20.0


def load_capacitance_data(csv_file):
    """Load capacitance data from CSV file."""
    try:
        df = pd.read_csv(csv_file)
        print(f"[INFO] Loaded data from {os.path.basename(csv_file)}")
        print(f"[INFO] Data shape: {df.shape}")
        
        # Check for timestamp column
        if 'timestamp' not in df.columns:
            print("[WARNING] No 'timestamp' column found, using row index")
            df['timestamp'] = np.arange(len(df)) * 0.1  # Assume 0.1s intervals
        
        # Extract channel columns
        channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
        if not channel_cols:
            print("[ERROR] No channel columns found (expected CH*_pF format)")
            return None, None
        
        print(f"[INFO] Found {len(channel_cols)} channels: {channel_cols}")
        return df, channel_cols
    except Exception as e:
        print(f"[ERROR] Failed to load {csv_file}: {e}")
        return None, None


def map_channels_to_nodes(row_data, channel_cols):
    """
    Map capacitance channel data to 4x4 mesh nodes.
    Simple mapping: CH0->Node0, CH1->Node1, etc.
    """
    node_values = np.zeros(16)  # 4x4 = 16 nodes
    
    for i, ch_col in enumerate(channel_cols):
        if ch_col in row_data and i < 16:
            node_values[i] = row_data[ch_col]
    
    return node_values


def create_pressure_map_frame(node_positions, node_values, method='cubic', resolution=100):
    """Create an interpolated pressure map from node values."""
    # Create a fine grid for interpolation
    x_min, x_max = node_positions[:, 0].min(), node_positions[:, 0].max()
    y_min, y_max = node_positions[:, 1].min(), node_positions[:, 1].max()
    
    # Add padding
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


def create_video(df, channel_cols, node_positions, output_file, 
                 time_start=None, time_end=None, fps=20):
    """
    Create an animated video of pressure maps.
    
    Args:
        df: DataFrame with capacitance data
        channel_cols: List of channel column names
        node_positions: Array of (x, y) positions for nodes
        output_file: Output video file path
        time_start: Start time in seconds (None = beginning)
        time_end: End time in seconds (None = end)
        fps: Frames per second
    """
    # Get actual time range
    actual_start = df['timestamp'].min()
    actual_end = df['timestamp'].max()
    print(f"[INFO] Data time range: {actual_start:.2f}s - {actual_end:.2f}s")
    
    # Adjust requested time range to available data
    if time_start is not None:
        if time_start < actual_start:
            print(f"[WARNING] Requested start time {time_start}s is before data start {actual_start:.2f}s, using {actual_start:.2f}s")
            time_start = actual_start
        df = df[df['timestamp'] >= time_start].copy()
    else:
        time_start = actual_start
    
    if time_end is not None:
        if time_end > actual_end:
            print(f"[WARNING] Requested end time {time_end}s is after data end {actual_end:.2f}s, using {actual_end:.2f}s")
            time_end = actual_end
        df = df[df['timestamp'] <= time_end].copy()
    else:
        time_end = actual_end
    
    if len(df) == 0:
        print(f"[ERROR] No data in time range {time_start}-{time_end}")
        return False
    
    print(f"[INFO] Processing {len(df)} frames from {df['timestamp'].min():.2f}s to {df['timestamp'].max():.2f}s")
    
    # Sample frames if too many
    max_frames = fps * 60  # Max 60 seconds at specified fps
    if len(df) > max_frames:
        step = len(df) // max_frames
        df = df.iloc[::step].copy()
        print(f"[INFO] Downsampled to {len(df)} frames")
    
    # Pre-compute all frames
    print("[INFO] Pre-computing pressure map frames...")
    frames_data = []
    for idx, row in df.iterrows():
        node_values = map_channels_to_nodes(row, channel_cols)
        xi, yi, zi = create_pressure_map_frame(node_positions, node_values, 
                                              method=INTERP_METHOD, resolution=RESOLUTION)
        frames_data.append({
            'timestamp': row['timestamp'],
            'xi': xi,
            'yi': yi,
            'zi': zi,
            'node_values': node_values
        })
    
    # Get global value range for consistent colormap
    all_values = np.concatenate([f['zi'] for f in frames_data])
    vmin = np.percentile(all_values, 5)  # Use 5th percentile to avoid outliers
    vmax = np.percentile(all_values, 95)  # Use 95th percentile
    
    print(f"[INFO] Value range: {vmin:.2f} - {vmax:.2f} pF")
    
    # Setup figure
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Create initial frame
    frame0 = frames_data[0]
    im = ax.contourf(frame0['xi'], frame0['yi'], frame0['zi'], 
                    levels=20, cmap='hot', vmin=vmin, vmax=vmax, alpha=0.8)
    ax.contour(frame0['xi'], frame0['yi'], frame0['zi'], 
              levels=20, colors='black', alpha=0.3, linewidths=0.5)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Capacitance (pF)', rotation=270, labelpad=20)
    
    # Plot node positions
    scatter = ax.scatter(node_positions[:, 0], node_positions[:, 1],
                        s=300, c=frame0['node_values'], cmap='hot',
                        edgecolors='black', linewidths=2,
                        vmin=vmin, vmax=vmax, zorder=5)
    
    # Add timestamp text
    time_text = ax.text(0.5, 0.98, f"t = {frame0['timestamp']:.2f}s",
                       transform=ax.transAxes, ha='center', va='top',
                       fontsize=14, fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax.set_xlabel('X Position (cm)', fontsize=12)
    ax.set_ylabel('Y Position (cm)', fontsize=12)
    ax.set_title('Pressure Map Animation', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    # Update function
    def update(frame_idx):
        frame = frames_data[frame_idx]
        
        # Clear and redraw
        ax.clear()
        
        # Redraw contour
        im = ax.contourf(frame['xi'], frame['yi'], frame['zi'],
                        levels=20, cmap='hot', vmin=vmin, vmax=vmax, alpha=0.8)
        ax.contour(frame['xi'], frame['yi'], frame['zi'],
                  levels=20, colors='black', alpha=0.3, linewidths=0.5)
        
        # Redraw nodes
        ax.scatter(node_positions[:, 0], node_positions[:, 1],
                  s=300, c=frame['node_values'], cmap='hot',
                  edgecolors='black', linewidths=2,
                  vmin=vmin, vmax=vmax, zorder=5)
        
        # Update timestamp
        time_text = ax.text(0.5, 0.98, f"t = {frame['timestamp']:.2f}s",
                           transform=ax.transAxes, ha='center', va='top',
                           fontsize=14, fontweight='bold',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.set_xlabel('X Position (cm)', fontsize=12)
        ax.set_ylabel('Y Position (cm)', fontsize=12)
        ax.set_title('Pressure Map Animation', fontsize=14, fontweight='bold')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        return []
    
    # Create animation
    print(f"[INFO] Creating animation with {len(frames_data)} frames at {fps} fps...")
    ani = FuncAnimation(fig, update, frames=len(frames_data),
                       interval=1000/fps, blit=False, repeat=False)
    
    # Save video
    print(f"[INFO] Saving video to {output_file}...")
    try:
        writer = FFMpegWriter(fps=fps, codec='h264')
        ani.save(output_file, writer=writer, dpi=150)
        print(f"[INFO] Video saved: {output_file}")
        plt.close(fig)
        return True
    except Exception as e:
        print(f"[WARNING] Failed to save video with FFMpegWriter: {e}")
        print("[INFO] Trying PillowWriter for GIF instead...")
        try:
            writer = PillowWriter(fps=fps)
            # If output is MP4, change to GIF; otherwise use as-is
            if output_file.endswith('.mp4'):
                gif_file = output_file.replace('.mp4', '.gif')
            else:
                gif_file = output_file
            ani.save(gif_file, writer=writer, dpi=150)
            print(f"[INFO] GIF saved: {gif_file}")
            plt.close(fig)
            return gif_file  # Return the actual file created
        except Exception as e2:
            print(f"[ERROR] Failed to save GIF: {e2}")
            plt.close(fig)
            return False


def extract_gif_from_video(video_file, output_gif, start_time=0, end_time=20):
    """
    Extract a segment from video and convert to GIF using ffmpeg.
    
    Args:
        video_file: Input video file
        output_gif: Output GIF file
        start_time: Start time in seconds
        end_time: End time in seconds
    """
    if not os.path.exists(video_file):
        print(f"[ERROR] Video file not found: {video_file}")
        return False
    
    duration = end_time - start_time
    
    print(f"[INFO] Extracting {duration}s segment ({start_time}s - {end_time}s) from video...")
    
    # Use ffmpeg to extract segment and convert to GIF
    try:
        # First, extract segment as temporary video
        temp_video = output_gif.replace('.gif', '_temp.mp4')
        cmd1 = [
            'ffmpeg', '-y', '-i', video_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:v', 'libx264', '-preset', 'fast',
            temp_video
        ]
        
        print(f"[INFO] Running: {' '.join(cmd1)}")
        result = subprocess.run(cmd1, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] ffmpeg extraction failed: {result.stderr}")
            return False
        
        # Convert to GIF with palette
        palette_file = output_gif.replace('.gif', '_palette.png')
        cmd2 = [
            'ffmpeg', '-y', '-i', temp_video,
            '-vf', 'fps=10,scale=640:-1:flags=lanczos,palettegen',
            palette_file
        ]
        
        print(f"[INFO] Generating palette...")
        result = subprocess.run(cmd2, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[WARNING] Palette generation failed: {result.stderr}")
            # Try simpler conversion
            cmd3 = [
                'ffmpeg', '-y', '-i', temp_video,
                '-vf', 'fps=10,scale=640:-1',
                output_gif
            ]
            result = subprocess.run(cmd3, capture_output=True, text=True)
        else:
            # Use palette to create GIF
            cmd3 = [
                'ffmpeg', '-y', '-i', temp_video, '-i', palette_file,
                '-lavfi', 'fps=10,scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse',
                output_gif
            ]
            result = subprocess.run(cmd3, capture_output=True, text=True)
        
        # Cleanup
        if os.path.exists(temp_video):
            os.remove(temp_video)
        if os.path.exists(palette_file):
            os.remove(palette_file)
        
        if result.returncode == 0:
            print(f"[INFO] GIF saved: {output_gif}")
            return True
        else:
            print(f"[ERROR] GIF conversion failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("[ERROR] ffmpeg not found. Please install ffmpeg to convert video to GIF.")
        print("[INFO] Video file created, but GIF conversion skipped.")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to convert to GIF: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Pressure Map Video Generator')
    parser.add_argument('--csv-file', type=str, default=DEFAULT_CSV,
                       help='Path to CSV file with capacitance data')
    parser.add_argument('--output-video', type=str, default=OUTPUT_VIDEO,
                       help='Output video file path')
    parser.add_argument('--output-gif', type=str, default=OUTPUT_GIF,
                       help='Output GIF file path')
    parser.add_argument('--start-time', type=float, default=TIME_START,
                       help='Start time in seconds (default: 0)')
    parser.add_argument('--end-time', type=float, default=TIME_END,
                       help='End time in seconds (default: 20)')
    parser.add_argument('--fps', type=int, default=FPS,
                       help='Frames per second (default: 20)')
    parser.add_argument('--gif-only', action='store_true',
                       help='Only create GIF, skip full video')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Pressure Map Video Generator (Version 4)")
    print("=" * 60)
    
    # Check if CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"[ERROR] CSV file not found: {args.csv_file}")
        print(f"[INFO] Looking for alternative files...")
        # Try to find similar files
        csv_dir = os.path.dirname(args.csv_file) or '.'
        pattern = os.path.basename(args.csv_file).split('_')[0] + '*pressure*.csv'
        import glob
        matches = glob.glob(os.path.join(csv_dir, pattern))
        if matches:
            args.csv_file = matches[0]
            print(f"[INFO] Using: {args.csv_file}")
        else:
            sys.exit(1)
    
    # Load data
    df, channel_cols = load_capacitance_data(args.csv_file)
    if df is None:
        sys.exit(1)
    
    # Create mesh
    node_positions, node_ids = create_4x4_mesh(spacing=1.0)
    
    # If user wants 0-20s, interpret as first 20 seconds of available data
    if args.start_time == 0.0 and args.end_time == 20.0:
        actual_start = df['timestamp'].min()
        actual_end = actual_start + 20.0
        print(f"[INFO] Interpreting 0-20s as first 20 seconds of data: {actual_start:.2f}s - {actual_end:.2f}s")
        args.start_time = actual_start
        args.end_time = min(actual_end, df['timestamp'].max())
    
    # Create video/GIF for the specified time range
    result = create_video(df, channel_cols, node_positions,
                         args.output_video,
                         time_start=args.start_time,
                         time_end=args.end_time,
                         fps=args.fps)
    
    if result:
        # If result is a string, it's the GIF file that was created
        if isinstance(result, str) and result.endswith('.gif'):
            # Rename to desired output name if different
            if result != args.output_gif and os.path.exists(result):
                import shutil
                shutil.move(result, args.output_gif)
                print(f"[INFO] Renamed GIF to: {args.output_gif}")
        elif not args.gif_only and os.path.exists(args.output_video):
            # Extract GIF from video if video was created
            extract_gif_from_video(args.output_video, args.output_gif,
                                  start_time=0, end_time=args.end_time - args.start_time)
    
    print("\n[INFO] Done!")


if __name__ == "__main__":
    main()

