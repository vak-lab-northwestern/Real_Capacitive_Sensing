import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq

# Read the CSV file
df = pd.read_csv('fdc2214_data_log.csv')

# Extract time and capacitance data
time = df['Time_s'].values
capacitance = df['Capacitance_pF'].values

# Calculate sampling rate
sampling_rate = len(time) / (time[-1] - time[0])
print(f"Sampling rate: {sampling_rate:.2f} Hz")

# Perform FFT to analyze frequency components
n = len(capacitance)
fft_result = fft(capacitance)
freqs = fftfreq(n, 1/sampling_rate)

# Find the 1Hz component
target_freq = 1.0
freq_tolerance = 0.1  # Hz
freq_mask = np.abs(freqs - target_freq) < freq_tolerance
freq_mask_neg = np.abs(freqs + target_freq) < freq_tolerance

# Extract 1Hz component
fft_1hz = fft_result.copy()
fft_1hz[~freq_mask & ~freq_mask_neg] = 0
capacitance_1hz = np.real(np.fft.ifft(fft_1hz))

# Create bandpass filter for 1Hz (0.5-1.5 Hz)
nyquist = sampling_rate / 2
low = 0.5 / nyquist
high = 1.5 / nyquist
b, a = signal.butter(4, [low, high], btype='band')
filtered_capacitance = signal.filtfilt(b, a, capacitance)

# Filter data for time between 0 and 60 seconds
mask = (time >= 0) & (time <= 60)
time_plot = time[mask]
capacitance_plot = capacitance[mask]
capacitance_1hz_plot = capacitance_1hz[mask]
filtered_capacitance_plot = filtered_capacitance[mask]

# Create the plots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

# Plot 1: Original data
ax1.plot(time_plot, capacitance_plot, 'b-', linewidth=1, alpha=0.7, label='Original')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Capacitance (pF)')
ax1.set_title('Original Capacitance Data')
ax1.set_xlim(0, 60)
ax1.grid(True, alpha=0.3)
ax1.legend()

# Plot 2: 1Hz component from FFT
ax2.plot(time_plot, capacitance_1hz_plot, 'r-', linewidth=2, label='1Hz Component (FFT)')
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Capacitance (pF)')
ax2.set_title('1Hz Frequency Component (FFT Method)')
ax2.set_xlim(0, 60)
ax2.grid(True, alpha=0.3)
ax2.legend()

# Plot 3: Bandpass filtered data
ax3.plot(time_plot, filtered_capacitance_plot, 'g-', linewidth=2, label='Bandpass Filtered (0.5-1.5 Hz)')
ax3.set_xlabel('Time (s)')
ax3.set_ylabel('Capacitance (pF)')
ax3.set_title('1Hz Component (Bandpass Filter)')
ax3.set_xlim(0, 60)
ax3.grid(True, alpha=0.3)
ax3.legend()

# Plot 4: Frequency spectrum
positive_freqs = freqs[:n//2]
positive_fft = np.abs(fft_result[:n//2])
ax4.semilogy(positive_freqs, positive_fft, 'b-', linewidth=1)
ax4.axvline(x=1, color='r', linestyle='--', linewidth=2, label='1 Hz')
ax4.set_xlabel('Frequency (Hz)')
ax4.set_ylabel('Magnitude')
ax4.set_title('Frequency Spectrum')
ax4.set_xlim(0, 5)  # Show up to 5 Hz
ax4.grid(True, alpha=0.3)
ax4.legend()

plt.tight_layout()

# Save the plot
import os
save_path = "/Users/cathdxx/desktop/NU_Experiments/ConductiveKnitTest/capacitance/"
os.makedirs(save_path, exist_ok=True)
plt.savefig(os.path.join(save_path, "070925_glove_finger_1hz.eps"), 
            format='eps', dpi=300, bbox_inches='tight')
print(f"Plot saved to: {os.path.join(save_path, '070925_glove_finger_1hz.eps')}")

plt.show()

# Print statistics
print(f"\n1Hz Component Analysis:")
print(f"Original data range: {capacitance.min():.2f} - {capacitance.max():.2f} pF")
print(f"1Hz component range: {capacitance_1hz.min():.2f} - {capacitance_1hz.max():.2f} pF")
print(f"1Hz component amplitude: {capacitance_1hz.max() - capacitance_1hz.min():.2f} pF")
print(f"Filtered data range: {filtered_capacitance.min():.2f} - {filtered_capacitance.max():.2f} pF")

# Calculate power at 1Hz
power_1hz = np.sum(np.abs(fft_result[freq_mask | freq_mask_neg])**2)
total_power = np.sum(np.abs(fft_result)**2)
power_ratio = power_1hz / total_power
print(f"Power at 1Hz: {power_ratio*100:.2f}% of total signal power") 