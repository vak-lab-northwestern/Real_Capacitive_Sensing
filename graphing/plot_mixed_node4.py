import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_mixed_node4_data():
    # File path
    csv_file = "differential_capacitance_20250917_181435_dipcoated_mixed_node4.csv"
    
    try:
        # Read the CSV file
        print(f"Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"Data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        
        # Check if required columns exist
        if 'timestamp' not in df.columns:
            print("Error: 'timestamp' column not found")
            return
        
        # Create subplots for all channels
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Differential Capacitance - Dipcoated Mixed Node4 (All Channels)', fontsize=16, fontweight='bold')
        
        # Plot each channel
        channels = ['CH0_pF', 'CH1_pF', 'CH2_pF', 'CH3_pF']
        colors = ['blue', 'red', 'green', 'orange']
        
        for i, (channel, color) in enumerate(zip(channels, colors)):
            if channel in df.columns:
                row = i // 2
                col = i % 2
                ax = axes[row, col]
                
                # Plot the data
                ax.plot(df['timestamp'], df[channel], 
                       linewidth=1.5, alpha=0.8, color=color, label=f'{channel}')
                
                # Customize each subplot
                ax.set_xlabel('Time (s)', fontsize=10)
                ax.set_ylabel('Capacitance (pF)', fontsize=10)
                ax.set_title(f'{channel} vs Time', fontsize=12, fontweight='bold')
                ax.legend(fontsize=9)
                ax.grid(True, alpha=0.3)
                
                # Add statistics for this channel
                mean_val = df[channel].mean()
                std_val = df[channel].std()
                min_val = df[channel].min()
                max_val = df[channel].max()
                
                stats_text = f'Mean: {mean_val:.2f}±{std_val:.2f} pF\nMin: {min_val:.2f} pF\nMax: {max_val:.2f} pF'
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                       fontsize=8)
            else:
                print(f"Warning: Column '{channel}' not found in data")
        
        # Adjust layout and show
        plt.tight_layout()
        plt.show()
        
        # Print summary statistics for all channels
        print("\n=== Summary Statistics ===")
        print(f"Data points: {len(df)}")
        print(f"Time range: {df['timestamp'].min():.2f} - {df['timestamp'].max():.2f} seconds")
        print(f"Duration: {df['timestamp'].max() - df['timestamp'].min():.2f} seconds")
        
        # Calculate sampling rate
        time_diff = np.diff(df['timestamp'])
        avg_sample_rate = 1.0 / np.mean(time_diff)
        print(f"Average sampling rate: {avg_sample_rate:.2f} Hz")
        
        print("\nChannel Statistics:")
        for channel in channels:
            if channel in df.columns:
                mean_val = df[channel].mean()
                std_val = df[channel].std()
                min_val = df[channel].min()
                max_val = df[channel].max()
                print(f"{channel}:")
                print(f"  Mean: {mean_val:.2f} pF")
                print(f"  Std:  {std_val:.2f} pF")
                print(f"  Min:  {min_val:.2f} pF")
                print(f"  Max:  {max_val:.2f} pF")
                print(f"  Range: {max_val - min_val:.2f} pF")
        
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
        print("Please make sure the CSV file exists in the current directory.")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    plot_mixed_node4_data()

