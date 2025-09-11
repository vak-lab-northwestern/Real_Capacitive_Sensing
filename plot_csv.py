import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV file
df = pd.read_csv('fdc2214_data_log.csv')

# Create the plot
plt.figure(figsize=(12, 6))
plt.plot(df['Time_s'], df['Capacitance_pF'], 'b-', linewidth=1)
plt.xlabel('Time (s)')
plt.ylabel('Capacitance (pF)')
plt.title('FDC2214 Capacitance Data')
plt.grid(True, alpha=0.3)

# Set y-axis range to show the actual data range
plt.ylim(30250, 30350)

# Add some statistics
mean_cap = df['Capacitance_pF'].mean()
std_cap = df['Capacitance_pF'].std()
plt.text(0.02, 0.98, f'Mean: {mean_cap:.2f} pF\nStd: {std_cap:.2f} pF', 
         transform=plt.gca().transAxes, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
plt.show()

# Print some basic statistics
print(f"Data points: {len(df)}")
print(f"Time range: {df['Time_s'].min():.2f} - {df['Time_s'].max():.2f} seconds")
print(f"Capacitance range: {df['Capacitance_pF'].min():.2f} - {df['Capacitance_pF'].max():.2f} pF")
print(f"Mean capacitance: {mean_cap:.2f} pF")
print(f"Standard deviation: {std_cap:.2f} pF") 