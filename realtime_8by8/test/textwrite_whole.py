import serial
import os
import time

# Create subfolder if it doesn't exist
folder_name = "txt_files"
os.makedirs(folder_name, exist_ok=True)

# Path to output file inside the subfolder
output_file = os.path.join(folder_name, "matrix_log10.txt")

ser = serial.Serial('/dev/tty.usbserial-210', 115200)   # Change to your port
matrix = [[0]*8 for _ in range(8)]
values_collected = 0

first_time = time.time()

while True:
    line = ser.readline().decode().strip()

    # Ignore header lines
    if line.startswith("---"):
        continue

    # Only process valid value lines
    if "Row" not in line or "Col" not in line or ":" not in line:
        continue

    try:
        # Example: "16852 , Row 7, Col 7 : 10235574"
        left, value_str = line.split(":")
        value = int(value_str.strip())

        parts = left.split(",")
        row = int(parts[1].strip().split()[1])
        col = int(parts[2].strip().split()[1])

        matrix[row][col] = value
        values_collected += 1

        # End of matrix is when Row 7, Col 7 arrives
        if row == 7 and col == 7:
            with open(output_file, "a") as f:
                f.write(f"Matrix {row}, {col} @ {time.time() - first_time}:\n")
                for r in range(8):
                    f.write(" ".join(str(x) for x in matrix[r]) + "\n")
                f.write("\n")  # Blank line between matrices

            print("Matrix saved to", output_file)

            # Reset for next matrix
            matrix = [[0]*8 for _ in range(8)]
            values_collected = 0

    except Exception as e:
        print("Parse error on line:", line)
