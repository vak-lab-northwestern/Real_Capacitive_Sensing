import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_ch0_comparison():
    # File paths
    data1_file = "20250801_x4_yarn_capacitance.csv"
    data2_file = "20250801_x4_PVDF_yarn_capacitance.csv"
    
    # Read the CSV files
    try:
        print(f"Reading {data1_file}...")
        df1 = pd.read_csv(data1_file)
        print(f"Data1 shape: {df1.shape}")
        print(f"Data1 columns: {df1.columns.tolist()}")
        
        print(f"Reading {data2_file}...")
        df2 = pd.read_csv(data2_file)
        print(f"Data2 shape: {df2.shape}")
        print(f"Data2 columns: {df2.columns.tolist()}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure both CSV files exist in the current directory.")
        return
    except Exception as e:
        print(f"Error reading files: {e}")
        return
    
    # Check if CH0_pF column exists
    if 'CH0_pF' not in df1.columns or 'CH0_pF' not in df2.columns:
        print("Error: CH0_pF column not found in one or both files.")
        print(f"Data1 columns: {df1.columns.tolist()}")
        print(f"Data2 columns: {df2.columns.tolist()}")
        return
    
    # Create the plot
    plt.figure(figsize=(15, 8))
    
    # Plot data1
    plt.plot(df1['timestamp'], df1['CH0_pF'], 
             label='X4 Yarn', linewidth=1.5, alpha=0.8, color='blue')
    
    # Plot data2
    plt.plot(df2['timestamp'], df2['CH0_pF'], 
             label='X4 PVDF Yarn', linewidth=1.5, alpha=0.8, color='red')
    
    # Customize the plot
    plt.xlabel('Time (s)', fontsize=12)
    plt.ylabel('Capacitance (pF)', fontsize=12)
    plt.title('CH0 Capacitance Comparison: X4 Yarn vs X4 PVDF Yarn', fontsize=14, fontweight='bold')
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # Add statistics
    mean1 = df1['CH0_pF'].mean()
    std1 = df1['CH0_pF'].std()
    mean2 = df2['CH0_pF'].mean()
    std2 = df2['CH0_pF'].std()
    
    stats_text = f'X4 Yarn: Mean={mean1:.2f}±{std1:.2f} pF\nX4 PVDF Yarn: Mean={mean2:.2f}±{std2:.2f} pF'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
             fontsize=10)
    
    # Adjust layout and show
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"X4 Yarn (Data1):")
    print(f"  Mean: {mean1:.2f} pF")
    print(f"  Std:  {std1:.2f} pF")
    print(f"  Min:  {df1['CH0_pF'].min():.2f} pF")
    print(f"  Max:  {df1['CH0_pF'].max():.2f} pF")
    print(f"  Data points: {len(df1)}")
    
    print(f"\nX4 PVDF Yarn (Data2):")
    print(f"  Mean: {mean2:.2f} pF")
    print(f"  Std:  {std2:.2f} pF")
    print(f"  Min:  {df2['CH0_pF'].min():.2f} pF")
    print(f"  Max:  {df2['CH0_pF'].max():.2f} pF")
    print(f"  Data points: {len(df2)}")
    
    # Calculate difference
    diff_mean = mean2 - mean1
    print(f"\nDifference (PVDF - X4): {diff_mean:.2f} pF")

if __name__ == "__main__":
    plot_ch0_comparison() 