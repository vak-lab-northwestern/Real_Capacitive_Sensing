import serial
import csv
import time
import queue
import threading
import signal
import sys

PORT = "/dev/tty.usbserial-2110"
BAUD = 115200

RAW_OUT = "raw_cap_data.csv"
FINAL_OUT = "cap_data_with_avg.csv"

# Thread-safe queue for passing samples from reader → writer
write_queue = queue.Queue()

# RAM buffer (used only for post-processing)
memory_buffer = []

running = True
writer_running = True


# exit from read
def handle_exit(sig, frame):
    global running, writer_running
    print("\nStopping...")
    running = False
    writer_running = False


signal.signal(signal.SIGINT, handle_exit)


# write to csv thread
def writer_thread_func():
    """Consumes samples from queue and writes to CSV without blocking the reader."""
    with open(RAW_OUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "row_index", "col_index", "row_cap", "col_cap"])

        while writer_running or not write_queue.empty():
            try:
                row = write_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            writer.writerow(row)
            f.flush()  # ensures crash-safe persistence


# read serial thread
def reader_thread_func():
    """Reads serial input as fast as possible and pushes parsed samples to queue."""
    ser = serial.Serial(PORT, BAUD, timeout=0.01)
    print("Recording... press CTRL+C to stop\n")

    start_time = time.time()

    while running:
        line = ser.readline().decode("utf-8").strip()
        if not line:
            continue

        parts = line.split(",")
        if len(parts) != 4:
            continue

        try:
            r_idx = int(parts[0].strip())
            c_idx = int(parts[1].strip())
            r_cap = float(parts[2].strip())
            c_cap = float(parts[3].strip())
        except ValueError:
            continue

        timestamp = time.time() - start_time

        sample = [timestamp, r_idx, c_idx, r_cap, c_cap]

        # push to writer thread
        write_queue.put(sample)

        # also store in RAM for later processing
        memory_buffer.append(sample)


# main function
def main():
    global writer_running

    # launch writer
    wt = threading.Thread(target=writer_thread_func)
    wt.start()

    # launch reader
    rt = threading.Thread(target=reader_thread_func)
    rt.start()

    # wait for reader to finish
    rt.join()

    # shut down writer thread
    writer_running = False
    wt.join()

    print("Finished acquisition. Now computing averages…")

    # compute average
    with open(FINAL_OUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "row_index", "col_index", "row_cap", "col_cap", "avg"])

        for ts, r_idx, c_idx, r_cap, c_cap in memory_buffer:
            avg = (r_cap + c_cap) / 2.0
            writer.writerow([ts, r_idx, c_idx, r_cap, c_cap, avg])

    print(f"Done!\nRaw saved:   {RAW_OUT}\nFinal saved: {FINAL_OUT}")


if __name__ == "__main__":
    main()
