import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_node_comparison():
    # File paths
    file1 = "09212025_node2_node_5_node1_node6_test1.csv"
    file2 = "09212025_node2_node_5_node1_node6_test2.csv"
    
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
        
        # Check if required columns exist
        required_cols = ['timestamp', 'CH0_pF', 'CH3_pF']
        for col in required_cols:
            if col not in df1.columns:
                print(f"Error: '{col}' column not found in {file1}")
                return
            if col not in df2.columns:
                print(f"Error: '{col}' column not found in {file2}")
                return
        
        # Offset timestamps to start from 0 for both datasets
        df1_offset = df1.copy()
        df2_offset = df2.copy()
        
        df1_offset['timestamp'] = df1_offset['timestamp'] - df1_offset['timestamp'].min()
        df2_offset['timestamp'] = df2_offset['timestamp'] - df2_offset['timestamp'].min()
        
        print(f"Timestamp offsets applied:")
        print(f"Test1: starts at 0, ends at {df1_offset['timestamp'].max():.2f} seconds")
        print(f"Test2: starts at 0, ends at {df2_offset['timestamp'].max():.2f} seconds")
        
        # Create the plot
        plt.figure(figsize=(15, 10))
        
        # Nature color palette optimized for color-blind individuals
        # Colors from: https://github.com/atsuyaw/NatureColorPalette
        nature_colors = {
            'blue': '#0072B2',      # Blue
            'lightblue': '#56B4E9', # Light blue  
            'red': '#D55E00',       # Reddish orange
            'orange': '#E69F00'     # Orange
        }
        
        # Plot CH0 from both files (Node 2 and Node 5)
        plt.plot(df1_offset['timestamp'], df1_offset['CH0_pF'], 
                linewidth=2, alpha=0.8, color=nature_colors['blue'], 
                label='CH0 - Node 2&5')
        
        plt.plot(df2_offset['timestamp'], df2_offset['CH0_pF'], 
                linewidth=2, alpha=0.8, color=nature_colors['lightblue'], linestyle='--',
                label='CH0 - Node 2&5 (Test2)')
        
        # Plot CH3 from both files (Node 1 and Node 6)
        plt.plot(df1_offset['timestamp'], df1_offset['CH3_pF'], 
                linewidth=2, alpha=0.8, color=nature_colors['red'], 
                label='CH3 - Node 1&6')
        
        plt.plot(df2_offset['timestamp'], df2_offset['CH3_pF'], 
                linewidth=2, alpha=0.8, color=nature_colors['orange'], linestyle='--',
                label='CH3 - Node 1&6 (Test2)')
        
        # Customize the plot
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('Capacitance (pF)', fontsize=12)
        plt.title('Node Comparison: CH0 (Node 2&5) vs CH3 (Node 1&6)', fontsize=14, fontweight='bold')
        plt.legend(fontsize=11, loc='upper right')
        plt.grid(True, alpha=0.3)
        
        # Add statistics box in the upper left
        stats_text = ""
        stats_text += f"CH0 (Node 2&5):\n"
        stats_text += f"  Test1: {df1_offset['CH0_pF'].mean():.2f}±{df1_offset['CH0_pF'].std():.2f} pF\n"
        stats_text += f"  Test2: {df2_offset['CH0_pF'].mean():.2f}±{df2_offset['CH0_pF'].std():.2f} pF\n"
        stats_text += f"CH3 (Node 1&6):\n"
        stats_text += f"  Test1: {df1_offset['CH3_pF'].mean():.2f}±{df1_offset['CH3_pF'].std():.2f} pF\n"
        stats_text += f"  Test2: {df2_offset['CH3_pF'].mean():.2f}±{df2_offset['CH3_pF'].std():.2f} pF"
        
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                 verticalalignment='top', horizontalalignment='left',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                 fontsize=10)
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save the plot as high-quality PNG
        output_filename = "0921_pose_brandon.png"
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
        
        print(f"\nTest1 - Node 2&5 (CH0):")
        print(f"  Mean: {df1_offset['CH0_pF'].mean():.2f} pF")
        print(f"  Std:  {df1_offset['CH0_pF'].std():.2f} pF")
        print(f"  Min:  {df1_offset['CH0_pF'].min():.2f} pF")
        print(f"  Max:  {df1_offset['CH0_pF'].max():.2f} pF")
        
        print(f"\nTest2 - Node 2&5 (CH0):")
        print(f"  Mean: {df2_offset['CH0_pF'].mean():.2f} pF")
        print(f"  Std:  {df2_offset['CH0_pF'].std():.2f} pF")
        print(f"  Min:  {df2_offset['CH0_pF'].min():.2f} pF")
        print(f"  Max:  {df2_offset['CH0_pF'].max():.2f} pF")
        
        print(f"\nTest1 - Node 1&6 (CH3):")
        print(f"  Mean: {df1_offset['CH3_pF'].mean():.2f} pF")
        print(f"  Std:  {df1_offset['CH3_pF'].std():.2f} pF")
        print(f"  Min:  {df1_offset['CH3_pF'].min():.2f} pF")
        print(f"  Max:  {df1_offset['CH3_pF'].max():.2f} pF")
        
        print(f"\nTest2 - Node 1&6 (CH3):")
        print(f"  Mean: {df2_offset['CH3_pF'].mean():.2f} pF")
        print(f"  Std:  {df2_offset['CH3_pF'].std():.2f} pF")
        print(f"  Min:  {df2_offset['CH3_pF'].min():.2f} pF")
        print(f"  Max:  {df2_offset['CH3_pF'].max():.2f} pF")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure both CSV files exist in the current directory.")
    except Exception as e:
        print(f"Error reading files: {e}")

if __name__ == "__main__":
    plot_node_comparison()
