
"""
Reads lines of 16 comma-separated numbers from an Arduino over serial
and writes them to a CSV file, one row per line received.
 
Requires pyserial:
    pip install pyserial
 
Usage:
    python serial_to_csv.py
"""
 
import csv
import serial
import time
 
# ---- Configuration ----
SERIAL_PORT = "/dev/cu.usbserial-0001"     
BAUD_RATE = 115200          # Must match Serial.begin(...) in your Arduino sketch
#OUTPUT_FILE = "data.csv"
EXPECTED_VALUES = 16        # Number of numbers expected per line
INCLUDE_TIMESTAMP = True    # Adds a timestamp column if True
 
 
def main():
    # Open serial connection
    
    output_file = input("Enter file name (ex: data1.csv)\n")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Give the Arduino time to reset after opening the port
    start_time = time.time()
 
    print(f"Listening on {SERIAL_PORT} at {BAUD_RATE} baud...")
    print(f"Writing data to {output_file}")
    print("Press Ctrl+C to stop.\n")
 
    # Open CSV file in append mode so re-running the script doesn't wipe old data
    with open(output_file, mode="a", newline="") as f:
        writer = csv.writer(f)
 
        # Optional header row (only written if file is empty)
        if f.tell() == 0:
            header = [f"value_{i+1}" for i in range(EXPECTED_VALUES)]
            if INCLUDE_TIMESTAMP:
                header = ["elapsed_seconds"] + header
            writer.writerow(header)
            f.flush()
 
        try:
            while True:
                raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
 
                if not raw_line:
                    continue  # timeout with no data, just loop again
 
                # Split on comma and clean up whitespace
                values = [v.strip() for v in raw_line.split(",")]
 
                # Basic validation: make sure we got the right number of values
                # and that they all look like numbers
                if len(values) != EXPECTED_VALUES:
                    print(f"Skipping malformed line (got {len(values)} values): {raw_line}")
                    continue
 
                try:
                    values = [float(v) for v in values]
                except ValueError:
                    print(f"Skipping non-numeric line: {raw_line}")
                    continue
 
                row = values
                if INCLUDE_TIMESTAMP:
                    # Plain number of seconds since the script started (millisecond precision).
                    # Numeric, never gets auto-reformatted by Excel/Sheets, never wraps around.
                    elapsed = round(time.time() - start_time, 3)
                    row = [elapsed] + row
 
                writer.writerow(row)
                f.flush()  # write to disk immediately in case script is interrupted
 
                print(row)
 
        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            ser.close()
 
 
if __name__ == "__main__":
    main()