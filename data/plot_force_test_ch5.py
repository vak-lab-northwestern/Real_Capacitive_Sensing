#!/usr/bin/env python3
"""
Plot CH5_pF data from FDC2214_Force_Test_CH5.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

def plot_force_test_ch5():
    """Plot CH5_pF data from the force test CSV file"""
    
    # Read the CSV file
    filename = "FDC2214_Force_Test_CH5.csv"
    print(f"Reading {filename}...")
    
    try:
        df = pd.read_csv(filename)
        print(f"Data shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        # Check if CH5_pF column exists
        if 'CH5_pF' not in df.columns:
            print("Error: CH5_pF column not found in the data")
            return
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        # Plot CH5_pF vs timestamp
        plt.plot(df['timestamp'], df['CH5_pF'], 
                linewidth=1.5, color='#2E86AB', alpha=0.8)
        
        # Customize the plot
        plt.title('FDC2214 Force Test - CH5 Capacitance', fontsize=16, fontweight='bold')
        plt.xlabel('Time (s)', fontsize=14)
        plt.ylabel('Capacitance (pF)', fontsize=14)
        plt.grid(True, alpha=0.3)
        
        # Set font to Arial
        plt.rcParams['font.family'] = 'Arial'
        
        # Add statistics text box
        mean_val = df['CH5_pF'].mean()
        std_val = df['CH5_pF'].std()
        min_val = df['CH5_pF'].min()
        max_val = df['CH5_pF'].max()
        
        stats_text = f"CH5 Statistics:\n"
        stats_text += f"Mean: {mean_val:.2f} pF\n"
        stats_text += f"Std: {std_val:.2f} pF\n"
        stats_text += f"Min: {min_val:.2f} pF\n"
        stats_text += f"Max: {max_val:.2f} pF\n"
        stats_text += f"Range: {max_val - min_val:.2f} pF"
        
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                verticalalignment='top', horizontalalignment='left',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                fontsize=12)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        output_filename = "FDC2214_Force_Test_CH5_plot.png"
        plt.savefig(output_filename, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', format='png')
        print(f"Plot saved as: {output_filename}")
        
        plt.show()
        
        # Print summary statistics
        print(f"\n=== Summary Statistics ===")
        print(f"Data points: {len(df)}")
        print(f"Duration: {df['timestamp'].max() - df['timestamp'].min():.2f} seconds")
        print(f"Sampling rate: {len(df) / (df['timestamp'].max() - df['timestamp'].min()):.2f} Hz")
        print(f"CH5 Mean: {mean_val:.2f} ± {std_val:.2f} pF")
        print(f"CH5 Range: {min_val:.2f} - {max_val:.2f} pF")
        
    except FileNotFoundError:
        print(f"Error: {filename} not found in the current directory")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    plot_force_test_ch5()


