import serial
import os
import time

# Create subfolder if it doesn't exist
folder_name = "txt_files"
os.makedirs(folder_name, exist_ok=True)

# Path to output file inside the subfolder
output_file = os.path.join(folder_name, "matrix_log6.txt")

ser = serial.Serial('/dev/tty.usbserial-210', 115200)   # Change to your port
matrix = [[0]*8 for _ in range(8)]
values_collected = 0
matrix_index = 0

first_time = time.time()

while True:
    line = ser.readline().decode().strip()

    # Ignore header lines
    if line.startswith("---"):
        continue

    # Only process lines containing row/col/value
    if "Row" not in line or "Col" not in line or ":" not in line:
        continue

    try:
        # Example: "16852 , Row 7, Col 7 : 10235574"
        left, value_str = line.split(":")
        value = int(value_str.strip())

        parts = left.split(",")

        # parts[1] = " Row 7"
        # parts[2] = " Col 7"
        row = int(parts[1].strip().split()[1])
        col = int(parts[2].strip().split()[1])

        matrix[row][col] = value
        # values_collected += 1

        # When last element (Row 7, Col 7) arrives, save matrix
        # if row == 7 and col == 7:
        with open(output_file, "a") as f:
            f.write(f"Matrix {row}, {col} @ {time.time() - first_time}:\n")
            for r in range(8):
                f.write(" ".join(str(x) for x in matrix[r]) + "\n")
            f.write("\n")  # Blank line between matrices

        print(f"{time.time() - first_time} Matrix {row}, {col} saved.\n")

        # Reset
        # matrix = [[0]*8 for _ in range(8)]
        # values_collected = 0
        # matrix_index += 1

    except Exception as e:
        print("Parse error on line:", line)
