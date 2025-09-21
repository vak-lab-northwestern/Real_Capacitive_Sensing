import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_node5_data():
    # File path
    csv_file = "differential_capacitance_20250917_182547_dipcoated_mixed_node5.csv"
    
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
        if 'CH0_pF' not in df.columns:
            print("Error: 'CH0_pF' column not found")
            return
        
        # Create the plot
        plt.figure(figsize=(15, 8))
        
        # Plot CH0_pF vs timestamp
        plt.plot(df['timestamp'], df['CH0_pF'], 
                linewidth=1.5, alpha=0.8, color='red', label='CH0 Capacitance')
        
        # Customize the plot
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('Capacitance (pF)', fontsize=12)
        plt.title('Dipcoated Mixed Node5 - CH0 Capacitance vs Time', fontsize=14, fontweight='bold')
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        
        # Add statistics
        mean_val = df['CH0_pF'].mean()
        std_val = df['CH0_pF'].std()
        min_val = df['CH0_pF'].min()
        max_val = df['CH0_pF'].max()
        
        stats_text = f'Mean: {mean_val:.2f}±{std_val:.2f} pF\nMin: {min_val:.2f} pF\nMax: {max_val:.2f} pF'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                 fontsize=10)
        
        # Adjust layout and show
        plt.tight_layout()
        plt.show()
        
        # Print summary statistics
        print("\n=== Summary Statistics ===")
        print(f"Data points: {len(df)}")
        print(f"Time range: {df['timestamp'].min():.2f} - {df['timestamp'].max():.2f} seconds")
        print(f"Duration: {df['timestamp'].max() - df['timestamp'].min():.2f} seconds")
        print(f"Mean CH0_pF: {mean_val:.2f} pF")
        print(f"Std CH0_pF: {std_val:.2f} pF")
        print(f"Min CH0_pF: {min_val:.2f} pF")
        print(f"Max CH0_pF: {max_val:.2f} pF")
        
        # Calculate sampling rate
        time_diff = np.diff(df['timestamp'])
        avg_sample_rate = 1.0 / np.mean(time_diff)
        print(f"Average sampling rate: {avg_sample_rate:.2f} Hz")
        
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
        print("Please make sure the CSV file exists in the current directory.")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    plot_node5_data()

