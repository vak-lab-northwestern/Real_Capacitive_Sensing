import serial
import csv
import time
import threading
from collections import deque
import math

# FDC2214 constants
ref_clock = 40e6  # Hz
scale_factor = ref_clock / (2 ** 28)
inductance = 180e-9  # H

def raw_to_capacitance(raw):
    freq = raw * scale_factor
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * inductance)
    return cap_F * 1e12  # picofarads

# Test serial connection
print("[DEBUG] Testing serial connection...")
try:
    ser = serial.Serial("/dev/tty.usbmodem2101", 115200, timeout=1)
    print(f"[INFO] Serial connection established: {ser.name}")
except Exception as e:
    print(f"[ERROR] Failed to connect to serial port: {e}")
    exit(1)

# Test CSV file creation
print("[DEBUG] Testing CSV file creation...")
try:
    test_filename = "debug_test.csv"
    with open(test_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['timestamp', 'CH0_pF', 'CH1_pF', 'CH2_pF', 'CH3_pF'])
        writer.writerow([time.time(), 100.0, 200.0, 300.0, 400.0])
        csvfile.flush()
    print(f"[INFO] CSV test file created: {test_filename}")
except Exception as e:
    print(f"[ERROR] Failed to create CSV file: {e}")
    exit(1)

# Data collection test
print("[DEBUG] Starting data collection test...")
start_time = time.time()
data_count = 0

try:
    while data_count < 10:  # Collect 10 samples
        try:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line:
                print("[DEBUG] No data received, waiting...")
                continue
                
            print(f"[DEBUG] Raw data: {raw_line}")
            parts = raw_line.split(",")
            
            if len(parts) != 4:
                print(f"[DEBUG] Invalid data format, expected 4 parts, got {len(parts)}")
                continue
                
            raw_vals = list(map(int, parts))
            caps = [raw_to_capacitance(r) for r in raw_vals]
            
            timestamp = time.time() - start_time
            print(f"[DEBUG] Processed data: {timestamp:.2f}s, {caps}")
            
            data_count += 1
            
        except Exception as e:
            print(f"[ERROR] Data processing error: {e}")
            continue
            
except KeyboardInterrupt:
    print("\n[INFO] Data collection stopped by user")

finally:
    ser.close()
    print("[INFO] Serial connection closed")
    print(f"[INFO] Collected {data_count} data samples") 