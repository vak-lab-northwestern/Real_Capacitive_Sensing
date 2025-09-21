import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_nozzle_node8():
    # File path
    csv_file = "differential_capacitance_20250917_184850_dipcoated_nozzle_node8.csv"
    
    try:
        # Read the CSV file
        print(f"Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"Data shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        
        # Check if required columns exist
        required_cols = ['timestamp', 'CH0_pF', 'CH1_pF', 'CH2_pF', 'CH3_pF']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: '{col}' column not found")
                return
        
        # Create the plot with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
        
        # Colors for each channel
        colors = ['blue', 'red', 'green', 'orange']
        channels = ['CH0_pF', 'CH1_pF', 'CH2_pF', 'CH3_pF']
        labels = ['CH0', 'CH1', 'CH2', 'CH3']
        
        # Plot all channels in the first subplot
        for i, (channel, color, label) in enumerate(zip(channels, colors, labels)):
            ax1.plot(df['timestamp'], df[channel], 
                    linewidth=1.5, alpha=0.8, color=color, label=label)
        
        # Customize the first subplot
        ax1.set_xlabel('Time (s)', fontsize=12)
        ax1.set_ylabel('Capacitance (pF)', fontsize=12)
        ax1.set_title('All Channels - Dipcoated Nozzle Node8', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # Plot individual channels in the second subplot for better visibility
        for i, (channel, color, label) in enumerate(zip(channels, colors, labels)):
            ax2.plot(df['timestamp'], df[channel], 
                    linewidth=1.5, alpha=0.8, color=color, label=label)
        
        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Capacitance (pF)', fontsize=12)
        ax2.set_title('Individual Channels Detail', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=11)
        ax2.grid(True, alpha=0.3)
        
        # Add statistics for all channels
        stats_text = ""
        for i, (channel, label) in enumerate(zip(channels, labels)):
            mean_val = df[channel].mean()
            std_val = df[channel].std()
            stats_text += f'{label}: {mean_val:.2f}±{std_val:.2f} pF\n'
        
        plt.figtext(0.02, 0.02, stats_text, fontsize=10, 
                   bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        # Adjust layout and show
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        plt.show()
        
        # Print summary statistics for all channels
        print("\n=== Summary Statistics for All Channels ===")
        print(f"Data points: {len(df)}")
        print(f"Time range: {df['timestamp'].min():.2f} - {df['timestamp'].max():.2f} seconds")
        print(f"Duration: {df['timestamp'].max() - df['timestamp'].min():.2f} seconds")
        
        for i, (channel, label) in enumerate(zip(channels, labels)):
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
        
        # Calculate sampling rate
        time_diff = np.diff(df['timestamp'])
        avg_sample_rate = 1.0 / np.mean(time_diff)
        print(f"\nAverage sampling rate: {avg_sample_rate:.2f} Hz")
        
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
        print("Please make sure the CSV file exists in the current directory.")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    plot_nozzle_node8()

