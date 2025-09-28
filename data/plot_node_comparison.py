import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

def apply_lowpass_filter(data, cutoff_freq=1.0, sampling_rate=10.0):
    """
    Apply a low-pass filter to remove high frequency noise
    
    Args:
        data: 1D numpy array of data to filter
        cutoff_freq: Cutoff frequency in Hz (default: 1.0 Hz)
        sampling_rate: Sampling rate in Hz (default: 10.0 Hz)
    
    Returns:
        Filtered data
    """
    # Normalize cutoff frequency
    nyquist = sampling_rate / 2.0
    normal_cutoff = cutoff_freq / nyquist
    
    # Design Butterworth filter
    b, a = signal.butter(4, normal_cutoff, btype='low', analog=False)
    
    # Apply filter
    filtered_data = signal.filtfilt(b, a, data)
    
    return filtered_data

def apply_savgol_filter(data, window_length=20, polyorder=1):
    """
    Apply Savitzky-Golay smoothing filter
    
    Args:
        data: 1D numpy array of data to filter
        window_length: Length of the filter window (must be odd)
        polyorder: Order of the polynomial used to fit the samples
    
    Returns:
        Smoothed data
    """
    # Ensure window_length is odd
    if window_length % 2 == 0:
        window_length += 1
    
    # Ensure window_length is not larger than data length
    if window_length > len(data):
        window_length = len(data) if len(data) % 2 == 1 else len(data) - 1
    
    # Apply Savitzky-Golay filter
    smoothed_data = signal.savgol_filter(data, window_length, polyorder)
    
    return smoothed_data

def plot_node_comparison(plot_mode='raw'):
    """
    Plot node comparison data
    
    Args:
        plot_mode (str): 'raw' for individual test data, 'mean' for mean with min-max shading
    """
    # File paths
    file1 = "09212025_node2_node_5_node1_node6_test1.csv"
    file2 = "09212025_node2_node_5_node1_node6_test2.csv"
    file3 = "09212025_node2_node_5_node1_node6_test3.csv"
    
    try:
        # Read the CSV files
        print(f"Reading {file1}...")
        df1 = pd.read_csv(file1)
        print(f"Data1 shape: {df1.shape}")
        print(f"Data1 columns: {df1.columns.tolist()}")
        
        print(f"Reading {file2}...")
        df2 = pd.read_csv(file2)
        print(f"Data2 shape: {df2.shape}")
        print(f"Data2 columns: {df2.columns.tolist()}")
        
        print(f"Reading {file3}...")
        df3 = pd.read_csv(file3)
        print(f"Data3 shape: {df3.shape}")
        print(f"Data3 columns: {df3.columns.tolist()}")
        
        # Check if required columns exist
        required_cols = ['timestamp', 'CH0_pF', 'CH3_pF']
        for col in required_cols:
            if col not in df1.columns:
                print(f"Error: '{col}' column not found in {file1}")
                return
            if col not in df2.columns:
                print(f"Error: '{col}' column not found in {file2}")
                return
            if col not in df3.columns:
                print(f"Error: '{col}' column not found in {file3}")
                return
        
        # Offset timestamps to start from 0 for all datasets
        df1_offset = df1.copy()
        df2_offset = df2.copy()
        df3_offset = df3.copy()
        
        df1_offset['timestamp'] = df1_offset['timestamp'] - df1_offset['timestamp'].min()
        df2_offset['timestamp'] = df2_offset['timestamp'] - df2_offset['timestamp'].min()
        df3_offset['timestamp'] = df3_offset['timestamp'] - df3_offset['timestamp'].min()
        
        # Calculate sampling rates for all datasets
        test1_duration = df1_offset['timestamp'].max()
        test1_samples = len(df1_offset)
        sampling_rate1 = test1_samples / test1_duration if test1_duration > 0 else 10.0
        
        test2_duration = df2_offset['timestamp'].max()
        test2_samples = len(df2_offset)
        sampling_rate2 = test2_samples / test2_duration if test2_duration > 0 else 10.0
        
        test3_duration = df3_offset['timestamp'].max()
        test3_samples = len(df3_offset)
        sampling_rate3 = test3_samples / test3_duration if test3_duration > 0 else 10.0
        
        # Apply low-pass filter to all datasets
        print(f"Applying low-pass filter to all datasets (cutoff: 1.0 Hz)")
        print(f"  Test1 sampling rate: {sampling_rate1:.2f} Hz")
        print(f"  Test2 sampling rate: {sampling_rate2:.2f} Hz") 
        print(f"  Test3 sampling rate: {sampling_rate3:.2f} Hz")
        
        # Test1 filtering
        df1_offset['CH0_pF_filtered'] = apply_lowpass_filter(df1_offset['CH0_pF'].values, 
                                                             cutoff_freq=1.0, sampling_rate=sampling_rate1)
        df1_offset['CH3_pF_filtered'] = apply_lowpass_filter(df1_offset['CH3_pF'].values, 
                                                             cutoff_freq=1.0, sampling_rate=sampling_rate1)
        
        # Test2 filtering
        df2_offset['CH0_pF_filtered'] = apply_lowpass_filter(df2_offset['CH0_pF'].values, 
                                                             cutoff_freq=1.0, sampling_rate=sampling_rate2)
        df2_offset['CH3_pF_filtered'] = apply_lowpass_filter(df2_offset['CH3_pF'].values, 
                                                             cutoff_freq=1.0, sampling_rate=sampling_rate2)
        
        # Test3 filtering
        df3_offset['CH0_pF_filtered'] = apply_lowpass_filter(df3_offset['CH0_pF'].values, 
                                                             cutoff_freq=1.0, sampling_rate=sampling_rate3)
        df3_offset['CH3_pF_filtered'] = apply_lowpass_filter(df3_offset['CH3_pF'].values, 
                                                             cutoff_freq=1.0, sampling_rate=sampling_rate3)
        
        # Compute mean and standard deviation across the three tests
        print("Computing mean and standard deviation across the three tests...")
        
        # Find common time points (interpolate to common time grid)
        min_time = max(df1_offset['timestamp'].min(), df2_offset['timestamp'].min(), df3_offset['timestamp'].min())
        max_time = min(df1_offset['timestamp'].max(), df2_offset['timestamp'].max(), df3_offset['timestamp'].max())
        common_time = np.linspace(min_time, max_time, 1000)  # 1000 points for smooth interpolation
        
        # Interpolate all datasets to common time grid
        from scipy.interpolate import interp1d
        
        # CH0 interpolation
        f1_ch0 = interp1d(df1_offset['timestamp'], df1_offset['CH0_pF_filtered'], kind='linear', 
                         bounds_error=False, fill_value='extrapolate')
        f2_ch0 = interp1d(df2_offset['timestamp'], df2_offset['CH0_pF_filtered'], kind='linear', 
                         bounds_error=False, fill_value='extrapolate')
        f3_ch0 = interp1d(df3_offset['timestamp'], df3_offset['CH0_pF_filtered'], kind='linear', 
                         bounds_error=False, fill_value='extrapolate')
        
        ch0_test1_interp = f1_ch0(common_time)
        ch0_test2_interp = f2_ch0(common_time)
        ch0_test3_interp = f3_ch0(common_time)
        
        # CH3 interpolation
        f1_ch3 = interp1d(df1_offset['timestamp'], df1_offset['CH3_pF_filtered'], kind='linear', 
                         bounds_error=False, fill_value='extrapolate')
        f2_ch3 = interp1d(df2_offset['timestamp'], df2_offset['CH3_pF_filtered'], kind='linear', 
                         bounds_error=False, fill_value='extrapolate')
        f3_ch3 = interp1d(df3_offset['timestamp'], df3_offset['CH3_pF_filtered'], kind='linear', 
                         bounds_error=False, fill_value='extrapolate')
        
        ch3_test1_interp = f1_ch3(common_time)
        ch3_test2_interp = f2_ch3(common_time)
        ch3_test3_interp = f3_ch3(common_time)
        
        # Compute mean, min, and max across the three tests
        ch0_mean = np.mean([ch0_test1_interp, ch0_test2_interp, ch0_test3_interp], axis=0)
        ch0_min = np.min([ch0_test1_interp, ch0_test2_interp, ch0_test3_interp], axis=0)
        ch0_max = np.max([ch0_test1_interp, ch0_test2_interp, ch0_test3_interp], axis=0)
        
        ch3_mean = np.mean([ch3_test1_interp, ch3_test2_interp, ch3_test3_interp], axis=0)
        ch3_min = np.min([ch3_test1_interp, ch3_test2_interp, ch3_test3_interp], axis=0)
        ch3_max = np.max([ch3_test1_interp, ch3_test2_interp, ch3_test3_interp], axis=0)
        
        print(f"Timestamp offsets applied:")
        print(f"Test1: starts at 0, ends at {df1_offset['timestamp'].max():.2f} seconds")
        print(f"Test2: starts at 0, ends at {df2_offset['timestamp'].max():.2f} seconds")
        print(f"Test3: starts at 0, ends at {df3_offset['timestamp'].max():.2f} seconds")
        
        # Create the plot
        plt.figure(figsize=(15, 10))
        
        # Nature color palette optimized for color-blind individuals
        # Colors from: https://github.com/atsuyaw/NatureColorPalette
        nature_colors = {
            'blue': '#1976d2',  # Blue
            'lightblue': '#03a9f4',  # Light blue
            'darkblue': '#01579b',  # Dark blue
            'purple': '#9c27b0',  # Purple  
            'red': '#d32f2f',  # Red
            'orange': '#ed6c02',  # Orange
            'lightorange': '#ff9800',  # Light orange
            'darkorange': '#e65100',  # Dark orange
            'green': '#2e7d32' # Green
        }
        
        # Choose plotting mode
        if plot_mode == 'raw':
            # Plot CH0 from all files (Node 2 and Node 5) - filtered raw data
            plt.plot(df1_offset['timestamp'], df1_offset['CH0_pF_filtered'], 
                    linewidth=2, alpha=0.8, color=nature_colors['blue'], 
                    label='CH0 - Node 2&5 (Test1, filtered)')
            
            plt.plot(df2_offset['timestamp'], df2_offset['CH0_pF_filtered'], 
                    linewidth=2, alpha=0.8, color=nature_colors['lightblue'], linestyle='--',
                    label='CH0 - Node 2&5 (Test2, filtered)')
            
            plt.plot(df3_offset['timestamp'], df3_offset['CH0_pF_filtered'], 
                    linewidth=2, alpha=0.8, color=nature_colors['darkblue'], linestyle=':',
                    label='CH0 - Node 2&5 (Test3, filtered)')
            
            # Plot CH3 from all files (Node 1 and Node 6) - filtered raw data
            plt.plot(df1_offset['timestamp'], df1_offset['CH3_pF_filtered'], 
                    linewidth=2, alpha=0.8, color=nature_colors['red'], 
                    label='CH3 - Node 1&6 (Test1, filtered)')
            
            plt.plot(df2_offset['timestamp'], df2_offset['CH3_pF_filtered'], 
                    linewidth=2, alpha=0.8, color=nature_colors['orange'], linestyle='--',
                    label='CH3 - Node 1&6 (Test2, filtered)')
            
            plt.plot(df3_offset['timestamp'], df3_offset['CH3_pF_filtered'], 
                    linewidth=2, alpha=0.8, color=nature_colors['darkorange'], linestyle=':',
                    label='CH3 - Node 1&6 (Test3, filtered)')
            
        elif plot_mode == 'mean':
            # Plot CH0 mean with min-max shading (Node 2 and Node 5)
            plt.fill_between(common_time, ch0_min, ch0_max, 
                            color=nature_colors['green'], alpha=0.3, label='CH0 - Node 2&5 (Min-Max)')
            plt.plot(common_time, ch0_mean, linewidth=3, color=nature_colors['green'], 
                    label='CH0 - Node 2&5 (Mean)')
            
            # Plot CH3 mean with min-max shading (Node 1 and Node 6)
            plt.fill_between(common_time, ch3_min, ch3_max, 
                            color=nature_colors['orange'], alpha=0.3, label='CH3 - Node 1&6 (Min-Max)')
            plt.plot(common_time, ch3_mean, linewidth=3, color=nature_colors['orange'], 
                    label='CH3 - Node 1&6 (Mean)')
        
        else:
            raise ValueError("plot_mode must be 'raw' or 'mean'")
        
        # Set font to Arial
        plt.rcParams['font.family'] = 'Arial'
        
        # Customize the plot
        plt.xlim(0,120)
        plt.ylim(800,2400)
        plt.xlabel('Time (s)', fontsize=24)
        plt.ylabel('Capacitance (pF)', fontsize=24)
        #plt.title('Multi-Node Pose Sensing: CH0 (Node 2&5) vs CH3 (Node 1&6)', fontsize=24, fontweight='bold')
        plt.legend(fontsize=24, loc='upper left')
        plt.grid(True, alpha=0.3)
        
        # Set tick label font size
        plt.xticks(fontsize=24)
        plt.yticks(fontsize=24)
        
        # Add statistics box in the upper left
        stats_text = ""
        if plot_mode == 'raw':
            stats_text += f"CH0 (Node 2&5):\n"
            stats_text += f"  Test1: {df1_offset['CH0_pF_filtered'].mean():.2f}±{df1_offset['CH0_pF_filtered'].std():.2f} pF\n"
            stats_text += f"  Test2: {df2_offset['CH0_pF_filtered'].mean():.2f}±{df2_offset['CH0_pF_filtered'].std():.2f} pF\n"
            stats_text += f"  Test3: {df3_offset['CH0_pF_filtered'].mean():.2f}±{df3_offset['CH0_pF_filtered'].std():.2f} pF\n"
            stats_text += f"CH3 (Node 1&6):\n"
            stats_text += f"  Test1: {df1_offset['CH3_pF_filtered'].mean():.2f}±{df1_offset['CH3_pF_filtered'].std():.2f} pF\n"
            stats_text += f"  Test2: {df2_offset['CH3_pF_filtered'].mean():.2f}±{df2_offset['CH3_pF_filtered'].std():.2f} pF\n"
            stats_text += f"  Test3: {df3_offset['CH3_pF_filtered'].mean():.2f}±{df3_offset['CH3_pF_filtered'].std():.2f} pF"
        elif plot_mode == 'mean':
            stats_text += f"CH0 (Node 2&5, n=3):\n"
            stats_text += f"  Mean: {ch0_mean.mean():.2f} pF\n"
            stats_text += f"  Min-Max Range: {ch0_min.min():.0f}-{ch0_max.max():.0f} pF\n"
            stats_text += f"  Mean Range: {ch0_mean.min():.0f}-{ch0_mean.max():.0f} pF\n"
            stats_text += f"CH3 (Node 1&6, n=3):\n"
            stats_text += f"  Mean: {ch3_mean.mean():.2f} pF\n"
            stats_text += f"  Min-Max Range: {ch3_min.min():.0f}-{ch3_max.max():.0f} pF\n"
            stats_text += f"  Mean Range: {ch3_mean.min():.0f}-{ch3_mean.max():.0f} pF"
        
 #       plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
 #                verticalalignment='top', horizontalalignment='left',
 #                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
 #                fontsize=24)
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save the plot as high-quality PNG
        output_filename = f"0921_pose_brandon_{plot_mode}.png"
        plt.savefig(output_filename, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', format='png')
        print(f"Plot saved as: {output_filename}")
        
        plt.show()
        
        # Print summary statistics
        print("\n=== Summary Statistics (Time-offset data) ===")
        print(f"Test1 data points: {len(df1_offset)}")
        print(f"Test1 duration: {df1_offset['timestamp'].max():.2f} seconds")
        print(f"Test2 data points: {len(df2_offset)}")
        print(f"Test2 duration: {df2_offset['timestamp'].max():.2f} seconds")
        print(f"Test3 data points: {len(df3_offset)}")
        print(f"Test3 duration: {df3_offset['timestamp'].max():.2f} seconds")
        
        if plot_mode == 'raw':
            print(f"\n=== Individual Test Statistics (Raw Filtered Data) ===")
            print(f"CH0 (Node 2&5):")
            print(f"  Test1: {df1_offset['CH0_pF_filtered'].mean():.2f}±{df1_offset['CH0_pF_filtered'].std():.2f} pF")
            print(f"  Test2: {df2_offset['CH0_pF_filtered'].mean():.2f}±{df2_offset['CH0_pF_filtered'].std():.2f} pF")
            print(f"  Test3: {df3_offset['CH0_pF_filtered'].mean():.2f}±{df3_offset['CH0_pF_filtered'].std():.2f} pF")
            
            print(f"\nCH3 (Node 1&6):")
            print(f"  Test1: {df1_offset['CH3_pF_filtered'].mean():.2f}±{df1_offset['CH3_pF_filtered'].std():.2f} pF")
            print(f"  Test2: {df2_offset['CH3_pF_filtered'].mean():.2f}±{df2_offset['CH3_pF_filtered'].std():.2f} pF")
            print(f"  Test3: {df3_offset['CH3_pF_filtered'].mean():.2f}±{df3_offset['CH3_pF_filtered'].std():.2f} pF")
            
        elif plot_mode == 'mean':
            print(f"\n=== Mean and Min-Max Range Across Three Tests ===")
            print(f"CH0 (Node 2&5, n=3):")
            print(f"  Overall Mean: {ch0_mean.mean():.2f} pF")
            print(f"  Min-Max Range: {ch0_min.min():.2f} - {ch0_max.max():.2f} pF")
            print(f"  Mean Range:   {ch0_mean.min():.2f} - {ch0_mean.max():.2f} pF")
            
            print(f"\nCH3 (Node 1&6, n=3):")
            print(f"  Overall Mean: {ch3_mean.mean():.2f} pF")
            print(f"  Min-Max Range: {ch3_min.min():.2f} - {ch3_max.max():.2f} pF")
            print(f"  Mean Range:   {ch3_mean.min():.2f} - {ch3_mean.max():.2f} pF")
        
        print(f"\n=== Individual Test Statistics (for reference) ===")
        print(f"Test1 - CH0: {df1_offset['CH0_pF_filtered'].mean():.2f}±{df1_offset['CH0_pF_filtered'].std():.2f} pF")
        print(f"Test2 - CH0: {df2_offset['CH0_pF_filtered'].mean():.2f}±{df2_offset['CH0_pF_filtered'].std():.2f} pF")
        print(f"Test3 - CH0: {df3_offset['CH0_pF_filtered'].mean():.2f}±{df3_offset['CH0_pF_filtered'].std():.2f} pF")
        print(f"Test1 - CH3: {df1_offset['CH3_pF_filtered'].mean():.2f}±{df1_offset['CH3_pF_filtered'].std():.2f} pF")
        print(f"Test2 - CH3: {df2_offset['CH3_pF_filtered'].mean():.2f}±{df2_offset['CH3_pF_filtered'].std():.2f} pF")
        print(f"Test3 - CH3: {df3_offset['CH3_pF_filtered'].mean():.2f}±{df3_offset['CH3_pF_filtered'].std():.2f} pF")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure both CSV files exist in the current directory.")
    except Exception as e:
        print(f"Error reading files: {e}")

if __name__ == "__main__":
    # Choose plotting mode: 'raw' for individual test data, 'mean' for mean with min-max shading
    mode = 'mean'  # Change to 'mean' for mean data with min-max shading
    print(f"Running plot in '{mode}' mode...")
    plot_node_comparison(plot_mode=mode)
