import serial
import csv
import time
from datetime import datetime
import math

# FDC2214 constants
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)  # ~0.149 Hz per LSB
inductance = 180e-9  # H

def raw_to_capacitance(raw):
    freq = raw * scale_factor
    if freq <= 0:
        return 0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # convert to picofarads

# CSV setup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"fdc2214_data_log_{timestamp}.csv"
csv_file = open(csv_filename, 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Time_s', 'Capacitance_CH0_pF', 'Capacitance_CH1_pF', 'Capacitance_CH2_pF', 'Capacitance_CH3_pF'])

print(f"Data will be saved to: {csv_filename}")
print("Press Ctrl+C to stop data collection")

# Serial setup
ser = serial.Serial('/dev/tty.usbmodem2101', 115200)  # Update COM port if needed

# Timing
start_time = time.time()

# Data collection loop
try:
    while True:
        line = ser.readline().decode().strip()
        try:
            raw_values = list(map(int, line.split(",")))
            if len(raw_values) == 4:
                cap_values = [raw_to_capacitance(raw) for raw in raw_values]
                current_time = time.time() - start_time

                # Save to CSV
                csv_writer.writerow([current_time] + cap_values)
                csv_file.flush()  # Ensure data is written immediately
                
                # Print status every 100 samples
                if int(current_time * 10) % 100 == 0:  # Every 10 seconds
                    print(f"Time: {current_time:.1f}s, CH0: {cap_values[0]:.2f} pF")
                    
        except Exception as e:
            print(f"Error parsing data: {e}")
            pass
            
except KeyboardInterrupt:
    print(f"\nData collection stopped. Data saved to: {csv_filename}")
    csv_file.close()
    ser.close() 