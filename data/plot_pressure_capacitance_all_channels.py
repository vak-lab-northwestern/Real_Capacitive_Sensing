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

def discover_pressure_capacitance_files(date_pattern="10142025"):
    """Discover all pressure capacitance CSV files from specified date"""
    data_files = []
    
    # Search for pressure capacitance files specifically (only original files, not processed ones)
    search_patterns = [
        f"{date_pattern}_singleconfig8_pressure_cap*_CH*_CH*.csv",
        f"../{date_pattern}_singleconfig8_pressure_cap*_CH*_CH*.csv"
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

def plot_all_pressure_capacitance_data(date_pattern="09282025"):
    """Main function to discover and plot all pressure capacitance data"""
    print(f"=== Pressure Capacitance Plotting Script for {date_pattern} Data ===")
    
    # Discover all pressure capacitance files
    files = discover_pressure_capacitance_files(date_pattern)
    
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

def plot_by_channel_pair(channel_pair, cutoff_freq=2.0, date_pattern="09282025"):
    """Plot all files of a specific channel pair"""
    print(f"=== Plotting {channel_pair} Channel Pair Files ===")
    
    files = discover_pressure_capacitance_files(date_pattern)
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

def detect_first_significant_change(df, channel_cols, change_threshold=0.01):
    """
    Detect the first row where any channel shows a sustained change exceeding the threshold from initial baseline
    Forces truncation by using a very small initial baseline window (first 5 samples only)
    
    Parameters:
    - df: DataFrame with timestamp and channel data
    - channel_cols: List of channel column names
    - change_threshold: Minimum change in pF from baseline to consider significant (default: 0.01 pF)
    
    Returns:
    - first_change_time: Time in seconds when first significant change appears
    - first_change_index: Index in DataFrame when first significant change appears
    """
    # Use only first 5 samples as baseline - ensures we find changes even if they start early
    baseline_window = min(5, len(df))
    baselines = {}
    
    for ch_col in channel_cols:
        if ch_col in df.columns:
            baseline_values = df[ch_col].iloc[:baseline_window]
            # Filter out any NaN or zero values
            valid_baseline = baseline_values[~pd.isna(baseline_values) & (baseline_values != 0)]
            if len(valid_baseline) > 0:
                baselines[ch_col] = valid_baseline.mean()
            else:
                baselines[ch_col] = 0
    
    # Find the first row AFTER baseline window where any channel shows sustained change beyond threshold
    # Start searching from after the baseline window
    consecutive_threshold = 3  # Need 3 consecutive points above threshold
    consecutive_counts = {ch_col: 0 for ch_col in channel_cols}
    
    # Start searching from after baseline window to ensure we always find something to truncate
    for idx in range(baseline_window, len(df)):
        for ch_col in channel_cols:
            if ch_col in df.columns and ch_col in baselines:
                value = df[ch_col].iloc[idx]
                if not pd.isna(value) and value != 0:
                    change = abs(value - baselines[ch_col])
                    
                    # Check if change exceeds threshold
                    if change >= change_threshold:
                        consecutive_counts[ch_col] += 1
                        
                        # If we have sustained change, this is our truncation point
                        if consecutive_counts[ch_col] >= consecutive_threshold:
                            first_change_index = max(0, idx - consecutive_threshold + 1)
                            first_change_time = df['timestamp'].iloc[first_change_index]
                            return first_change_time, first_change_index
                    else:
                        consecutive_counts[ch_col] = 0
    
    # If no significant change found even after baseline, truncate at baseline window end
    # This ensures all datasets get some truncation
    if baseline_window < len(df):
        first_change_time = df['timestamp'].iloc[baseline_window]
        return first_change_time, baseline_window
    
    # Fallback - return start of data
    first_change_time = df['timestamp'].iloc[0]
    return first_change_time, 0

def batch_post_process_data(cutoff_freq=2.0, save_filtered=True, ylim_consistency=True, truncate_response=True, response_threshold=0.1, date_pattern="09282025"):
    """
    Batch post-process all pressure capacitance data with noise filtering and consistent y-limits
    
    Parameters:
    - cutoff_freq: Low-pass filter cutoff frequency in Hz
    - save_filtered: Whether to save filtered data to new CSV files
    - ylim_consistency: Whether to use consistent y-axis limits based on CH1_CH5 data
    - truncate_response: Whether to truncate initial response time until meaningful changes occur
    - response_threshold: Minimum change in pF to consider as meaningful response (default: 0.1 pF)
    - date_pattern: Date pattern to search for (e.g., "09282025" or "10082025")
    """
    print(f"=== Batch Post-Processing Pressure Capacitance Data ({date_pattern}) ===")
    
    # Discover all files
    files = discover_pressure_capacitance_files(date_pattern)
    
    if not files:
        print("No pressure capacitance files found!")
        return
    
    # First pass: analyze all files and determine y-axis limits and max duration
    all_data_stats = {}
    ch1_ch5_limits = None
    max_duration_after_truncation = 0
    
    if ylim_consistency:
        print("Setting consistent y-axis limits [275, 300] pF for all files...")
        # Use fixed y-axis limits
        ch1_ch5_limits = (275, 300)
        
        # Calculate max duration if truncate_response is enabled
        if truncate_response:
            for filename in files:
                try:
                    # Force read with all 8 channels
                    with open(filename, 'r') as f:
                        first_line = f.readline()
                        second_line = f.readline()
                        num_values = len(second_line.split(','))
                    
                    if num_values == 9:
                        df = pd.read_csv(filename, names=['timestamp', 'CH0_pF', 'CH1_pF', 'CH2_pF', 'CH3_pF', 'CH4_pF', 'CH5_pF', 'CH6_pF', 'CH7_pF'], header=0)
                    else:
                        df = pd.read_csv(filename)
                    
                    channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
                    first_change_time, first_change_index = detect_first_significant_change(df, channel_cols, change_threshold=0.01)
                    df_truncated = df.iloc[first_change_index:].copy()
                    duration_after_truncation = df_truncated['timestamp'].max() - df_truncated['timestamp'].iloc[0]
                    max_duration_after_truncation = max(max_duration_after_truncation, duration_after_truncation)
                except Exception as e:
                    print(f"Error analyzing {filename}: {e}")
            
            if max_duration_after_truncation > 0:
                print(f"Max duration after truncation: {max_duration_after_truncation:.1f} seconds")
    
    # Second pass: process each file
    successful_processing = 0
    
    for filename in files:
        print(f"\n=== Processing {os.path.basename(filename)} ===")
        
        try:
            # Read the data - force all files to have 9 columns (timestamp + 8 channels)
            # First, read raw to check actual number of values per row
            with open(filename, 'r') as f:
                first_line = f.readline()
                second_line = f.readline()
                num_values = len(second_line.split(','))
            
            if num_values == 9:
                # Force read with all 8 channel names regardless of what header says
                df = pd.read_csv(filename, names=['timestamp', 'CH0_pF', 'CH1_pF', 'CH2_pF', 'CH3_pF', 'CH4_pF', 'CH5_pF', 'CH6_pF', 'CH7_pF'], header=0)
            else:
                # If genuinely fewer columns, read normally
                df = pd.read_csv(filename)
            
            print(f"Data shape: {df.shape}")
            
            # Calculate sampling rate
            duration = df['timestamp'].max() - df['timestamp'].min()
            sampling_rate = len(df) / duration
            print(f"Sampling rate: {sampling_rate:.2f} Hz")
            
            # Extract channel columns
            channel_cols = [col for col in df.columns if col.startswith('CH') and col.endswith('_pF')]
            
            # Extract the specific channel pair from filename for zoomed view
            # Expected format: 10082025_singleconfig8_pressure_cap_CH1_CH6.csv
            basename = os.path.basename(filename)
            specific_channels = []
            try:
                # Extract channel numbers from filename
                import re
                ch_matches = re.findall(r'_CH(\d+)', basename)
                if len(ch_matches) >= 2:
                    specific_channels = [f'CH{ch_matches[0]}_pF', f'CH{ch_matches[1]}_pF']
                    print(f"Specific channels for zoomed view: {specific_channels}")
            except:
                pass
            
            # Detect and truncate initial baseline period before significant changes if requested
            first_change_time = None
            first_change_index = 0
            if truncate_response:
                first_change_time, first_change_index = detect_first_significant_change(df, channel_cols, change_threshold=0.01)
                if first_change_index > 0:
                    print(f"First significant change (>0.01 pF) at: {first_change_time:.2f} seconds (index: {first_change_index})")
                    
                    # Truncate data from first significant change onwards
                    df = df.iloc[first_change_index:].copy()
                    df = df.reset_index(drop=True)
                    
                    # Adjust timestamp to start from zero
                    df['timestamp'] = df['timestamp'] - df['timestamp'].iloc[0]
                    print(f"Data truncated. New data shape: {df.shape}")
                else:
                    print(f"Significant changes present from start - no truncation needed")
            
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
            if save_filtered and (filter_suffix or (truncate_response and first_change_time and first_change_index > 0)):
                base_name = os.path.splitext(os.path.basename(filename))[0]
                truncate_suffix = "_truncated" if truncate_response and first_change_time and first_change_index > 0 else ""
                filtered_filename = f"{base_name}{filter_suffix}{truncate_suffix}.csv"
                df_to_save = df[['timestamp'] + plot_columns].copy()
                df_to_save.to_csv(filtered_filename, index=False)
                print(f"Processed data saved as: {filtered_filename}")
            
            # Set font to Arial with minimum size 16 BEFORE creating plots
            plt.rcParams['font.family'] = 'Arial'
            plt.rcParams['font.size'] = 16
            plt.rcParams['axes.titlesize'] = 18
            plt.rcParams['axes.labelsize'] = 16
            plt.rcParams['xtick.labelsize'] = 16
            plt.rcParams['ytick.labelsize'] = 16
            plt.rcParams['legend.fontsize'] = 16
            
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
            
            # Set y-axis limits
            if ylim_consistency and ch1_ch5_limits:
                # Main plot uses consistent limits
                ax1.set_ylim(ch1_ch5_limits)
                # Zoomed plot will be normalized (ΔC/C₀), so it will auto-scale
            else:
                # If no consistent limits, use individual limits for main plot
                all_data = df[plot_columns]
                min_val = all_data.min().min()
                max_val = all_data.max().max()
                margin = (max_val - min_val) * 0.1  # 10% margin
                ax1.set_ylim([min_val - margin, max_val + margin])
                # Zoomed plot will be normalized (ΔC/C₀), so it will auto-scale
            
            # Set x-axis limits - consistent [0, 700] for main plot
            ax1.set_xlim([0, 700])  # Main plot: 0-700 seconds
            
            # Set zoomed view x-limits - custom for specific datasets
            basename = os.path.basename(filename)
            if 'CH0_CH4' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH0_CH4: 0-270 seconds
            elif 'CH0_CH5' in basename:
                ax2.set_xlim([0, 240])  # Zoomed view for CH0_CH5: 0-240 seconds
            elif 'CH0_CH6' in basename:
                ax2.set_xlim([0, 180])  # Zoomed view for CH0_CH6: 0-180 seconds
            elif 'CH0_CH7' in basename:
                ax2.set_xlim([0, 360])  # Zoomed view for CH0_CH7: 0-360 seconds
            elif 'CH1_CH4' in basename:
                ax2.set_xlim([0, 300])  # Zoomed view for CH1_CH4: 0-300 seconds
            elif 'CH1_CH5' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH1_CH5: 0-270 seconds
            elif 'CH1_CH6' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH1_CH6: 0-270 seconds
            elif 'CH1_CH7' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH1_CH7: 0-270 seconds
            elif 'CH2_CH4' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH2_CH4: 0-270 seconds
            elif 'CH2_CH5' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH2_CH5: 0-270 seconds
            elif 'CH2_CH6' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH2_CH6: 0-270 seconds
            elif 'CH2_CH7' in basename:
                ax2.set_xlim([0, 240])  # Zoomed view for CH2_CH7: 0-240 seconds
            elif 'CH3_CH4' in basename:
                ax2.set_xlim([0, 240])  # Zoomed view for CH3_CH4: 0-240 seconds
            elif 'CH3_CH5' in basename:
                ax2.set_xlim([0, 240])  # Zoomed view for CH3_CH5: 0-240 seconds
            elif 'CH3_CH6' in basename:
                ax2.set_xlim([0, 240])  # Zoomed view for CH3_CH6: 0-240 seconds
            elif 'CH3_CH7' in basename:
                ax2.set_xlim([0, 270])  # Zoomed view for CH3_CH7: 0-270 seconds
            else:
                ax2.set_xlim([0, 120])  # Zoomed view for others: 0-120 seconds
            
            # Customize the main plot
            ax1.set_title(f'{os.path.basename(filename)}', 
                         fontsize=18, fontweight='bold')
            ax1.set_xlabel('Time (s)', fontsize=16)
            ax1.set_ylabel('Capacitance (pF)', fontsize=16)
            ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=16)
            ax1.grid(True, alpha=0.3)
            
            # Create a zoomed-in view - only plot specific channels from filename
            # Custom durations for specific datasets
            basename = os.path.basename(filename)
            if 'CH0_CH4' in basename:
                zoom_duration = 270
            elif 'CH0_CH5' in basename:
                zoom_duration = 240
            elif 'CH0_CH6' in basename:
                zoom_duration = 180
            elif 'CH0_CH7' in basename:
                zoom_duration = 360
            elif 'CH1_CH4' in basename:
                zoom_duration = 300
            elif 'CH1_CH5' in basename:
                zoom_duration = 270
            elif 'CH1_CH6' in basename:
                zoom_duration = 270
            elif 'CH1_CH7' in basename:
                zoom_duration = 270
            elif 'CH2_CH4' in basename:
                zoom_duration = 270
            elif 'CH2_CH5' in basename:
                zoom_duration = 270
            elif 'CH2_CH6' in basename:
                zoom_duration = 270
            elif 'CH2_CH7' in basename:
                zoom_duration = 240
            elif 'CH3_CH4' in basename:
                zoom_duration = 240
            elif 'CH3_CH5' in basename:
                zoom_duration = 240
            elif 'CH3_CH6' in basename:
                zoom_duration = 240
            elif 'CH3_CH7' in basename:
                zoom_duration = 270
            else:
                zoom_duration = 120
            
            # Determine which columns to plot in zoom view
            if specific_channels:
                # Create filtered versions if needed
                zoom_plot_columns = []
                for ch in specific_channels:
                    if filter_suffix:
                        zoom_ch = ch.replace('_pF', '_pF_filtered')
                        if zoom_ch in df.columns:
                            zoom_plot_columns.append(zoom_ch)
                    else:
                        if ch in df.columns:
                            zoom_plot_columns.append(ch)
            else:
                # If no specific channels found, use all
                zoom_plot_columns = plot_columns
            
            # Calculate initial C0 values for normalization (average of first 5 points)
            c0_values = {}
            for ch_col in zoom_plot_columns:
                if ch_col in df.columns:
                    initial_window = min(5, len(df))
                    c0_values[ch_col] = df[ch_col].iloc[:initial_window].mean()
            
            # Plot normalized change (ΔC/C₀) for zoomed view
            for ch_col in zoom_plot_columns:
                if ch_col in df.columns and ch_col in c0_values and c0_values[ch_col] != 0:
                    # Get channel number to determine color
                    ch_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                    ch_num = int(ch_name.replace('CH', ''))
                    color = colors[ch_num % len(colors)]
                    channel_name = ch_name
                    mask = df['timestamp'] <= zoom_duration
                    
                    # Calculate normalized change: (C - C0) / C0
                    normalized_change = (df.loc[mask, ch_col] - c0_values[ch_col]) / c0_values[ch_col]
                    
                    ax2.plot(df.loc[mask, 'timestamp'], normalized_change, 
                            linewidth=2.0, color=color, alpha=0.8, label=channel_name)
            
            ax2.set_title(f'Zoomed View - First {zoom_duration} seconds (ΔC/C0)', 
                         fontsize=18, fontweight='bold')
            ax2.set_xlabel('Time (s)', fontsize=16)
            ax2.set_ylabel('ΔC/C0 (Normalized Change)', fontsize=16)
            ax2.legend(loc='best', fontsize=16)
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)  # Add zero reference line
            
            # Add statistics text box
            stats_text = "Channel Statistics:\n"
            for ch_col in plot_columns:
                if ch_col in df.columns:
                    channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                    mean_val = df[ch_col].mean()
                    std_val = df[ch_col].std()
                    stats_text += f"{channel_name}: {mean_val:.1f}±{std_val:.1f} pF\n"
            
            # Add C₀ values for zoomed channels
            if zoom_plot_columns and c0_values:
                stats_text += f"\nC0 (baseline) for zoom:\n"
                for ch_col in zoom_plot_columns:
                    if ch_col in c0_values:
                        channel_name = ch_col.replace('_pF_filtered', '').replace('_pF', '')
                        stats_text += f"{channel_name}: {c0_values[ch_col]:.2f} pF\n"
            
            if truncate_response and first_change_time and first_change_index > 0:
                stats_text += f"\nTruncated: {first_change_time:.2f}s removed"
            
            if ylim_consistency and ch1_ch5_limits:
                stats_text += f"\nY-limits: {ch1_ch5_limits[0]:.1f} - {ch1_ch5_limits[1]:.1f} pF"
            
            # Note: X-limits are [0, 700] seconds for all plots
            stats_text += f"\nX-limits: 0 - 700 s"
            
            # Position statistics box outside the second subplot (ax2), aligned with it
            # Place it on the right side at the same height as ax2
            ax2.text(1.05, 0.5, stats_text, transform=ax2.transAxes, 
                    verticalalignment='center', horizontalalignment='left',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                    fontsize=14)
            
            # Adjust layout
            plt.tight_layout()
            
            # Save the plot
            base_name = os.path.splitext(os.path.basename(filename))[0]
            truncate_suffix = "_truncated" if truncate_response and first_change_time and first_change_index > 0 else ""
            output_suffix = f"{filter_suffix}{truncate_suffix}_processed" if filter_suffix or truncate_suffix else "_processed"
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
    print(f"Baseline truncation: {'Enabled' if truncate_response else 'Disabled'}")
    if truncate_response:
        print(f"Change threshold: 0.01 pF (truncates until change exceeds this value)")
    print(f"X-axis limits: 0 - 700 seconds (consistent across all plots)")
    print(f"Y-axis consistency: {'Enabled' if ylim_consistency else 'Disabled'}")
    if ylim_consistency and ch1_ch5_limits:
        print(f"Y-axis limits: {ch1_ch5_limits[0]:.1f} - {ch1_ch5_limits[1]:.1f} pF (consistent across all plots)")
    print(f"Processed data saved: {'Yes' if save_filtered else 'No'}")

if __name__ == "__main__":
    # Run batch post-processing with noise filtering, truncate only initial no-reading period
    # For 10082025 data
    batch_post_process_data(cutoff_freq=2.0, save_filtered=True, ylim_consistency=False, 
                           truncate_response=True, response_threshold=1.0, date_pattern="10142025")
    
    # For 09282025 data (original):
    # batch_post_process_data(cutoff_freq=2.0, save_filtered=True, ylim_consistency=True, 
    #                        truncate_response=False, response_threshold=0.1, date_pattern="09282025")
    
    # Alternatively, run the standard plotting function
    # plot_all_pressure_capacitance_data(date_pattern="10082025")
