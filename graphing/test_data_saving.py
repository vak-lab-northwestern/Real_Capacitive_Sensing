import csv
import time
from datetime import datetime

# Test the data saving functionality
def test_csv_saving():
    # Create a test CSV file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_filename = f"test_data_{timestamp}.csv"
    
    print(f"Creating test file: {test_filename}")
    
    with open(test_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['timestamp', 'CH0_pF', 'CH1_pF', 'CH2_pF', 'CH3_pF'])
        
        # Write some test data
        for i in range(10):
            timestamp = time.time()
            test_data = [timestamp, 100.0 + i, 200.0 + i, 300.0 + i, 400.0 + i]
            writer.writerow(test_data)
            csvfile.flush()  # Force write to disk
            print(f"Wrote data: {test_data}")
            time.sleep(0.1)
    
    print(f"Test completed. Check file: {test_filename}")
    
    # Verify the file was created and has data
    try:
        with open(test_filename, 'r') as f:
            lines = f.readlines()
            print(f"File contains {len(lines)} lines")
            if len(lines) > 1:
                print("First data line:", lines[1].strip())
    except Exception as e:
        print(f"Error reading test file: {e}")

if __name__ == "__main__":
    test_csv_saving() 