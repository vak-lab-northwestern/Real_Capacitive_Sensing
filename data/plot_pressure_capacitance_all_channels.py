#!/usr/bin/env python3
"""
Pressure Capacitance Plotting Script for 09282025 Data
Automatically discovers and plots all pressure capacitance CSV files from 09282025

Usage Examples:
    # Plot all 09282025 pressure capacitance data
    python plot_pressure_capacitance_all_channels.py
    
    # Batch post-process with noise filtering, response truncation, and consistent y-limits
    batch_post_process_data(cutoff_freq=2.0, save_filtered=True, ylim_consistency=True, 
                           truncate_response=True, response_threshold=0.1)
    
    # Plot specific pressure capacitance files
    plot_specific_pressure_files(["09282025_singleconfig8_pressure_capacitance_CH0_CH7.csv"])
    
    # Plot all files of a specific channel pair
    plot_by_channel_pair("CH0-CH7")
    plot_by_channel_pair("CH1-CH5")
    plot_by_channel_pair("CH2-CH6")
    
Features:
- Automatic discovery of pressure capacitance files (09282025_singleconfig8_pressure_*.csv)
- Automatic channel detection (CH0-CH7)
- Automatic channel pair extraction from filenames
- Batch post-processing with high-frequency noise filtering
- Consistent y-axis limits based on CH1_CH5 data range
- Low-pass filtering for noise reduction (configurable cutoff frequency)
- Individual plots for each file with channel pair identification
- Summary statistics and overview plots
- Colorblind-friendly color palette (wong palette) for accessibility
- Channel pair comparison capabilities
- Save filtered data to new CSV files
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
import matplotlib.colors as mcolors
import glob
import os
from pathlib import Path

def discover_pressure_capacitance_files():
    """Discover all pressure capacitance CSV files from 09282025"""
    data_files = []
    
    # Search for pressure capacitance files specifically (only original files, not processed ones)
    search_patterns = [
        "09282025_singleconfig8_pressure_capacitance_CH*_CH*.csv",
        "../data/09282025_singleconfig8_pressure_capacitance_CH*_CH*.csv"
    ]
    
    for pattern in search_patterns:
        files = glob.glob(pattern)
        data_files.extend(files)
    
    # Filter out already processed files (those with _filtered or _truncated in the name)
    original_files = []
    for file in data_files:
        if '_filtered' not in file and '_truncated' not in file:
            original_files.append(file)
    
    # Remove duplicates and sort
    data_files = sorted(list(set(original_files)))
    
    print(f"Found {len(data_files)} pressure capacitance CSV files:")
    for i, file in enumerate(data_files, 1):
        print(f"  {i}. {file}")
    
    return data_files

def analyze_pressure_file_structure(filename):
    """Analyze the structure of a pressure capacitance CSV file to determine channels and configuration"""
    try:
        df = pd.read_csv(filename, nrows=5)  # Read just a few rows to analyze structure
        columns = list(df.columns)
        
        # Extract channel columns
        channel_cols = [col for col in columns if col.startswith('CH') and col.endswith('_pF')]
        num_channels = len(channel_cols)
        
        # Extract channel pair information from filename
        # Expected format: 09282025_singleconfig8_pressure_capacitance_CH0_CH7.csv
        basename = os.path.basename(filename)
        if '_CH' in basename and '_CH' in basename.split('_CH')[1:]:
            # Extract channel pair from filename
            parts = basename.split('_')
            ch_parts = [part for part in parts if part.startswith('CH')]
            if len(ch_parts) >= 2:
                channel_pair = f"{ch_parts[0]}-{ch_parts[1]}"
            else:
                channel_pair = f"CH0-CH{num_channels-1}"
        else:
            channel_pair = "All Channels"
        
        # Determine if this is a specific channel pair or all channels
        if 'CH0_CH7' in basename or 'CH0_CH4' in basename or 'CH0_CH5' in basename or 'CH0_CH6' in basename:
            test_type = f"Pressure Capacitance ({channel_pair})"
        else:
            test_type = f"Pressure Capacitance ({channel_pair})"
        
        return {
            'filename': filename,
            'test_type': test_type,
            'channel_pair': channel_pair,
            'channels': channel_cols,
            'num_channels': num_channels,
            'columns': columns,
            'basename': basename
        }
    except Exception as e:
        print(f"Error analyzing {filename}: {e}")
        return None

def plot_single_file(file_info, cutoff_freq=2.0):
    """Plot a single CSV file with all available channels"""
    filename = file_info['filename']
    test_type = file_info['test_type']
    channels = file_info['channels']
    num_channels = file_info['num_channels']
    
    print(f"\n=== Processing {filename} ===")
    print(f"Test Type: {test_type}")
    print(f"Channels: {num_channels} ({', '.join(channels)})")
    
    try:
        df = pd.read_csv(filename)
        print(f"Data shape: {df.shape}")
        
        # Calculate sampling rate
        duration = df['timestamp'].max() - df['timestamp'].min()
        sampling_rate = len(df) / duration
        print(f"Sampling rate: {sampling_rate:.2f} Hz")
        
        # Apply low-pass filter if we have enough data
        if sampling_rate > 4:  # Only filter if sampling rate is reasonable
            nyquist_freq = sampling_rate / 2
            normalized_cutoff = cutoff_freq / nyquist_freq
            
            # Create low-pass Butterworth filter
            from scipy.signal import butter, filtfilt
            b, a = butter(4, normalized_cutoff, btype='low', analog=False)
        
            print(f"Applying low-pass filter (cutoff: {cutoff_freq} Hz)...")
            
            # Apply filter to all channels
            for ch_col in channels:
                if ch_col in df.columns:
                    df[f'{ch_col}_filtered'] = filtfilt(b, a, df[ch_col])
                    print(f"  Filtered {ch_col}")
            
            # Use filtered data for plotting
            plot_columns = [f'{ch}_filtered' for ch in channels if f'{ch}_filtered' in df.columns]
            filter_suffix = "_filtered"
        else:
            print("Sampling rate too low for filtering, using raw data")
            plot_columns = channels
            filter_suffix = ""
        
        # Create the plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
        
        # Wong colorblind-friendly palette for up to 8 channels
        # Based on Bang Wong's colorblind-friendly palette
        colors = [
            '#000000',  # CH0: Black
            '#E69F00',  # CH1: Orange
            '#56B4E9',  # CH2: Sky Blue
            '#009E73',  # CH3: Bluish Green
            '#F0E442',  # CH4: Yellow
            '#0072B2',  # CH5: Blue
            '#D55E00',  # CH6: Vermilion
            '#CC79A7'   # CH7: Reddish Purple
        ]
        
        # Plot all channels
        for i, ch_col in enumerate(plot_columns):
            if ch_col in df.columns:
                color = colors[i % len(colors)]
                channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                ax1.plot(df['timestamp'], df[ch_col], 
                        linewidth=1.5, color=color, alpha=0.8, label=channel_name)
        
        # Customize the main plot
        filter_suffix = " (Filtered)" if 'filtered' in plot_columns[0] else ""
        ax1.set_title(f'{test_type} - All Channels{filter_suffix}\n{os.path.basename(filename)}', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Time (s)', fontsize=14)
        ax1.set_ylabel('Capacitance (pF)', fontsize=14)
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Create a zoomed-in view (first 60 seconds or full duration if shorter)
        zoom_duration = min(60, duration)
        for i, ch_col in enumerate(plot_columns):
            if ch_col in df.columns:
                color = colors[i % len(colors)]
                channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                mask = df['timestamp'] <= zoom_duration
                ax2.plot(df.loc[mask, 'timestamp'], df.loc[mask, ch_col], 
                        linewidth=1.5, color=color, alpha=0.8, label=channel_name)
        
        ax2.set_title(f'Zoomed View - First {zoom_duration:.0f} seconds', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Capacitance (pF)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Set font to Arial
        plt.rcParams['font.family'] = 'Arial'
        
        # Add statistics text box
        stats_text = f"Channel Statistics:\n"
        for ch_col in plot_columns:
            if ch_col in df.columns:
                channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                mean_val = df[ch_col].mean()
                std_val = df[ch_col].std()
                stats_text += f"{channel_name}: {mean_val:.1f}±{std_val:.1f} pF\n"
        
        ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
                verticalalignment='top', horizontalalignment='left',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                fontsize=9)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        base_name = os.path.splitext(os.path.basename(filename))[0]
        output_filename = f"{base_name}_plot.png"
        plt.savefig(output_filename, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', format='png')
        print(f"Plot saved as: {output_filename}")
        
        plt.show()
        
        return True
        
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return False

def create_pressure_summary_plot(file_info_list):
    """Create a summary plot showing statistics from all pressure capacitance files"""
    print("\n=== Creating Pressure Capacitance Summary Plot ===")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    # Collect statistics from all files
    channel_pairs = []
    channel_counts = []
    file_names = []
    
    for file_info in file_info_list:
        channel_pairs.append(file_info['channel_pair'])
        channel_counts.append(file_info['num_channels'])
        file_names.append(os.path.basename(file_info['filename']))
    
    # Plot channel pair distribution using wong colorblind-friendly palette
    unique_pairs, counts = np.unique(channel_pairs, return_counts=True)
    wong_colors = ['#000000', '#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7']
    # Set font to Arial with minimum size 16
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['font.size'] = 16
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['xtick.labelsize'] = 16
    plt.rcParams['ytick.labelsize'] = 16
    
    ax1.bar(unique_pairs, counts, color=wong_colors[:len(unique_pairs)])
    ax1.set_title('Distribution of Channel Pairs (09282025 Pressure Data)', fontsize=18, fontweight='bold')
    ax1.set_ylabel('Number of Files', fontsize=16)
    ax1.tick_params(axis='x', rotation=45, labelsize=16)
    ax1.tick_params(axis='y', labelsize=16)
    
    # Plot channel count distribution using wong colorblind-friendly palette
    unique_channels, ch_counts = np.unique(channel_counts, return_counts=True)
    ax2.bar(unique_channels, ch_counts, color=wong_colors[:len(unique_channels)])
    ax2.set_title('Channel Count Distribution (09282025 Pressure Data)', fontsize=18, fontweight='bold')
    ax2.set_xlabel('Number of Channels', fontsize=16)
    ax2.set_ylabel('Number of Files', fontsize=16)
    ax2.tick_params(axis='x', labelsize=16)
    ax2.tick_params(axis='y', labelsize=16)
    
    plt.tight_layout()
    
    # Save summary plot
    output_filename = "09282025_pressure_capacitance_summary.png"
    plt.savefig(output_filename, dpi=300, bbox_inches='tight', 
               facecolor='white', edgecolor='none', format='png')
    print(f"Summary plot saved as: {output_filename}")
    
    plt.show()

def plot_all_pressure_capacitance_data():
    """Main function to discover and plot all 09282025 pressure capacitance data"""
    print("=== Pressure Capacitance Plotting Script for 09282025 Data ===")
    
    # Discover all pressure capacitance files
    files = discover_pressure_capacitance_files()
    
    if not files:
        print("No 09282025 pressure capacitance CSV files found!")
        return
    
    # Analyze file structures
    file_info_list = []
    for filename in files:
        info = analyze_pressure_file_structure(filename)
        if info:
            file_info_list.append(info)
    
    # Create summary
    create_pressure_summary_plot(file_info_list)
    
    # Plot each file
    successful_plots = 0
    for file_info in file_info_list:
        if plot_single_file(file_info):
            successful_plots += 1
    
    print(f"\n=== Summary ===")
    print(f"Total pressure capacitance files found: {len(files)}")
    print(f"Files analyzed: {len(file_info_list)}")
    print(f"Plots created successfully: {successful_plots}")
    
    # Print file summary
    print(f"\n=== Pressure Capacitance File Summary ===")
    for info in file_info_list:
        print(f"{info['basename']}: {info['channel_pair']} - {info['num_channels']} channels")

def plot_specific_pressure_files(filenames, cutoff_freq=2.0):
    """Plot specific pressure capacitance CSV files by providing their names"""
    print(f"=== Plotting Specific Pressure Capacitance Files ===")
    
    for filename in filenames:
        info = analyze_pressure_file_structure(filename)
        if info:
            plot_single_file(info, cutoff_freq)
        else:
            print(f"Could not analyze {filename}")

def plot_by_channel_pair(channel_pair, cutoff_freq=2.0):
    """Plot all files of a specific channel pair"""
    print(f"=== Plotting {channel_pair} Channel Pair Files ===")
    
    files = discover_pressure_capacitance_files()
    file_info_list = []
    
    for filename in files:
        info = analyze_pressure_file_structure(filename)
        if info and info['channel_pair'] == channel_pair:
            file_info_list.append(info)
    
    if not file_info_list:
        print(f"No files found for channel pair: {channel_pair}")
        return
    
    for file_info in file_info_list:
        plot_single_file(file_info, cutoff_freq)

def detect_response_time(df, channel_cols, threshold=0.1, window_size=10):
    """
    Detect when any channel starts to show meaningful changes above threshold
    
    Parameters:
    - df: DataFrame with timestamp and channel data
    - channel_cols: List of channel column names
    - threshold: Minimum change in pF to consider as meaningful (default: 0.1 pF)
    - window_size: Window size for rolling mean calculation
    
    Returns:
    - response_time: Time in seconds when response starts
    - response_index: Index in DataFrame when response starts
    """
    response_index = 0
    
    for ch_col in channel_cols:
        if ch_col in df.columns:
            # Calculate rolling mean to smooth out noise
            rolling_mean = df[ch_col].rolling(window=window_size, center=True).mean()
            
            # Calculate the difference from the initial value
            initial_value = rolling_mean.iloc[window_size//2] if not rolling_mean.isna().iloc[window_size//2] else df[ch_col].iloc[0]
            diff_from_initial = rolling_mean - initial_value
            
            # Find first point where absolute change exceeds threshold
            threshold_exceeded = np.abs(diff_from_initial) >= threshold
            first_change_idx = threshold_exceeded.idxmax() if threshold_exceeded.any() else None
            
            if first_change_idx is not None and not threshold_exceeded.iloc[first_change_idx]:
                # idxmax() returns first False if no True found, so we need to find actual first True
                true_indices = np.where(threshold_exceeded)[0]
                if len(true_indices) > 0:
                    first_change_idx = true_indices[0]
            
            # Update response_index to the earliest meaningful change across all channels
            if first_change_idx is not None and first_change_idx > response_index:
                response_index = first_change_idx
    
    # Convert index to time
    response_time = df['timestamp'].iloc[response_index] if response_index < len(df) else df['timestamp'].iloc[-1]
    
    return response_time, response_index

def batch_post_process_data(cutoff_freq=2.0, save_filtered=True, ylim_consistency=True, truncate_response=True, response_threshold=0.1):
    """
    Batch post-process all pressure capacitance data with noise filtering and consistent y-limits
    
    Parameters:
    - cutoff_freq: Low-pass filter cutoff frequency in Hz
    - save_filtered: Whether to save filtered data to new CSV files
    - ylim_consistency: Whether to use consistent y-axis limits based on CH1_CH5 data
    - truncate_response: Whether to truncate initial response time until meaningful changes occur
    - response_threshold: Minimum change in pF to consider as meaningful response (default: 0.1 pF)
    """
    print("=== Batch Post-Processing Pressure Capacitance Data ===")
    
    # Discover all files
    files = discover_pressure_capacitance_files()
    
    if not files:
        print("No pressure capacitance files found!")
        return
    
    # First pass: analyze all files and determine y-axis limits
    all_data_stats = {}
    ch1_ch5_limits = None
    
    if ylim_consistency:
        print("Analyzing data ranges for consistent y-axis limits...")
        ch1_ch5_files = [f for f in files if 'CH1_CH5' in f]
        
        if ch1_ch5_files:
            # Calculate y-axis limits from CH1_CH5 data
            min_vals, max_vals = [], []
            for filename in ch1_ch5_files:
                try:
                    df = pd.read_csv(filename)
                    channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
                    for col in channel_cols:
                        min_vals.append(df[col].min())
                        max_vals.append(df[col].max())
                except Exception as e:
                    print(f"Error analyzing {filename}: {e}")
            
            if min_vals and max_vals:
                # Add 5% margin to the range
                margin = (max(max_vals) - min(min_vals)) * 0.05
                ch1_ch5_limits = (min(min_vals) - margin, max(max_vals) + margin)
                print(f"CH1_CH5 y-axis limits set to: {ch1_ch5_limits[0]:.1f} - {ch1_ch5_limits[1]:.1f} pF")
        else:
            print("No CH1_CH5 files found for y-axis limit reference")
    
    # Second pass: process each file
    successful_processing = 0
    
    for filename in files:
        print(f"\n=== Processing {os.path.basename(filename)} ===")
        
        try:
            # Read the data
            df = pd.read_csv(filename)
            print(f"Data shape: {df.shape}")
            
            # Calculate sampling rate
            duration = df['timestamp'].max() - df['timestamp'].min()
            sampling_rate = len(df) / duration
            print(f"Sampling rate: {sampling_rate:.2f} Hz")
            
            # Extract channel columns
            channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
            
            # Detect and truncate initial response time if requested
            response_time = None
            response_index = 0
            if truncate_response:
                response_time, response_index = detect_response_time(df, channel_cols, response_threshold)
                print(f"Response time detected at: {response_time:.2f} seconds (index: {response_index})")
                
                # Truncate data from response time onwards
                df = df.iloc[response_index:].copy()
                df = df.reset_index(drop=True)
                
                # Adjust timestamp to start from zero
                df['timestamp'] = df['timestamp'] - df['timestamp'].iloc[0]
                print(f"Data truncated. New data shape: {df.shape}")
            
            # Apply noise filtering
            if sampling_rate > 4:  # Only filter if sampling rate is reasonable
                nyquist_freq = sampling_rate / 2
                normalized_cutoff = cutoff_freq / nyquist_freq
                
                # Create low-pass Butterworth filter
                from scipy.signal import butter, filtfilt
                b, a = butter(4, normalized_cutoff, btype='low', analog=False)
                
                print(f"Applying low-pass filter (cutoff: {cutoff_freq} Hz)...")
                
                # Apply filter to all channels
                for ch_col in channel_cols:
                    if ch_col in df.columns:
                        df[f'{ch_col}_filtered'] = filtfilt(b, a, df[ch_col])
                        print(f"  Filtered {ch_col}")
                
                # Use filtered data for plotting
                plot_columns = [f'{ch}_filtered' for ch in channel_cols if f'{ch}_filtered' in df.columns]
                filter_suffix = "_filtered"
            else:
                print("Sampling rate too low for filtering, using raw data")
                plot_columns = channel_cols
                filter_suffix = ""
            
            # Save filtered data if requested
            if save_filtered and (filter_suffix or (truncate_response and response_time)):
                base_name = os.path.splitext(os.path.basename(filename))[0]
                truncate_suffix = "_truncated" if truncate_response and response_time else ""
                filtered_filename = f"{base_name}{filter_suffix}{truncate_suffix}.csv"
                df_to_save = df[['timestamp'] + plot_columns].copy()
                df_to_save.to_csv(filtered_filename, index=False)
                print(f"Processed data saved as: {filtered_filename}")
            
            # Create the plot with consistent y-axis limits
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
            
            # Wong colorblind-friendly palette
            colors = [
                '#000000',  # CH0: Black
                '#E69F00',  # CH1: Orange
                '#56B4E9',  # CH2: Sky Blue
                '#009E73',  # CH3: Bluish Green
                '#F0E442',  # CH4: Yellow
                '#0072B2',  # CH5: Blue
                '#D55E00',  # CH6: Vermilion
                '#CC79A7'   # CH7: Reddish Purple
            ]
            
            # Plot all channels
            for i, ch_col in enumerate(plot_columns):
                if ch_col in df.columns:
                    color = colors[i % len(colors)]
                    channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                    ax1.plot(df['timestamp'], df[ch_col], 
                            linewidth=1.5, color=color, alpha=0.8, label=channel_name)
            
            # Set y-axis limits if consistency is requested
            if ylim_consistency and ch1_ch5_limits:
                ax1.set_ylim(ch1_ch5_limits)
                # For zoomed view, calculate individual y-limits based on data in first 60 seconds
                zoom_mask = df['timestamp'] <= 120
                if zoom_mask.any():
                    zoom_data = df.loc[zoom_mask, plot_columns]
                    min_val = zoom_data.min().min()
                    max_val = zoom_data.max().max()
                    margin = (max_val - min_val) * 0.1  # 10% margin
                    ax2.set_ylim([min_val - margin, max_val + margin])
                else:
                    ax2.set_ylim(ch1_ch5_limits)
            else:
                # If no consistent limits, use individual limits for both plots
                all_data = df[plot_columns]
                min_val = all_data.min().min()
                max_val = all_data.max().max()
                margin = (max_val - min_val) * 0.1  # 10% margin
                ax1.set_ylim([min_val - margin, max_val + margin])
                
                # For zoomed view, calculate individual y-limits based on data in first 60 seconds
                zoom_mask = df['timestamp'] <= 120
                if zoom_mask.any():
                    zoom_data = df.loc[zoom_mask, plot_columns]
                    min_val_zoom = zoom_data.min().min()
                    max_val_zoom = zoom_data.max().max()
                    margin_zoom = (max_val_zoom - min_val_zoom) * 0.1  # 10% margin
                    ax2.set_ylim([min_val_zoom - margin_zoom, max_val_zoom + margin_zoom])
                else:
                    ax2.set_ylim([min_val - margin, max_val + margin])
            
            # Set x-axis limits
            ax1.set_xlim([0, 500])  # Main plot: 0-500 seconds
            ax2.set_xlim([0, 120])  # Zoomed view: 0-120 seconds
            
            # Customize the main plot
            ax1.set_title(f'{os.path.basename(filename)}', 
                         fontsize=18, fontweight='bold')
            ax1.set_xlabel('Time (s)', fontsize=16)
            ax1.set_ylabel('Capacitance (pF)', fontsize=16)
            ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=16)
            ax1.grid(True, alpha=0.3)
            
            # Create a zoomed-in view (first 120 seconds)
            zoom_duration = 120
            for i, ch_col in enumerate(plot_columns):
                if ch_col in df.columns:
                    color = colors[i % len(colors)]
                    channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                    mask = df['timestamp'] <= zoom_duration
                    ax2.plot(df.loc[mask, 'timestamp'], df.loc[mask, ch_col], 
                            linewidth=1.5, color=color, alpha=0.8, label=channel_name)
            
            ax2.set_title('Zoomed View - First 120 seconds', 
                         fontsize=18, fontweight='bold')
            ax2.set_xlabel('Time (s)', fontsize=16)
            ax2.set_ylabel('Capacitance (pF)', fontsize=16)
            ax2.grid(True, alpha=0.3)
            
            # Set font to Arial with minimum size 16
            plt.rcParams['font.family'] = 'Arial'
            plt.rcParams['font.size'] = 16
            plt.rcParams['axes.titlesize'] = 16
            plt.rcParams['axes.labelsize'] = 16
            plt.rcParams['xtick.labelsize'] = 16
            plt.rcParams['ytick.labelsize'] = 16
            plt.rcParams['legend.fontsize'] = 16
            
            # Add statistics text box
            stats_text = "Channel Statistics:\n"
            for ch_col in plot_columns:
                if ch_col in df.columns:
                    channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                    mean_val = df[ch_col].mean()
                    std_val = df[ch_col].std()
                    stats_text += f"{channel_name}: {mean_val:.1f}±{std_val:.1f} pF\n"
            
            if truncate_response and response_time:
                stats_text += f"\nResponse time: {response_time:.2f}s (truncated)"
            
            if ylim_consistency and ch1_ch5_limits:
                stats_text += f"\nY-limits: {ch1_ch5_limits[0]:.1f} - {ch1_ch5_limits[1]:.1f} pF"
            
            ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, 
                    verticalalignment='top', horizontalalignment='left',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                    fontsize=16)
            
            # Adjust layout
            plt.tight_layout()
            
            # Save the plot
            base_name = os.path.splitext(os.path.basename(filename))[0]
            truncate_suffix = "_truncated" if truncate_response and response_time else ""
            output_suffix = f"{filter_suffix}{truncate_suffix}_processed"
            output_filename = f"{base_name}{output_suffix}.png"
            plt.savefig(output_filename, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none', format='png')
            print(f"Processed plot saved as: {output_filename}")
            
            plt.show()
            
            successful_processing += 1
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    print(f"\n=== Batch Processing Summary ===")
    print(f"Total files processed: {successful_processing}/{len(files)}")
    print(f"Filter cutoff frequency: {cutoff_freq} Hz")
    print(f"Response truncation: {'Enabled' if truncate_response else 'Disabled'}")
    if truncate_response:
        print(f"Response threshold: {response_threshold} pF")
    print(f"Y-axis consistency: {'Enabled' if ylim_consistency else 'Disabled'}")
    if ylim_consistency and ch1_ch5_limits:
        print(f"Y-axis limits: {ch1_ch5_limits[0]:.1f} - {ch1_ch5_limits[1]:.1f} pF")
    print(f"Processed data saved: {'Yes' if save_filtered else 'No'}")

if __name__ == "__main__":
    # Run batch post-processing with noise filtering, response truncation, and consistent y-limits
    batch_post_process_data(cutoff_freq=2.0, save_filtered=True, ylim_consistency=True, 
                           truncate_response=True, response_threshold=0.1)
    
    # Alternatively, run the standard plotting function
    # plot_all_pressure_capacitance_data()
