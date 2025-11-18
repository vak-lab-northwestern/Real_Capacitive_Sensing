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
FINAL_OUT = "cap_data_clean.csv"

# Thread-safe queue for passing samples from reader → writer
write_queue = queue.Queue()

# RAM buffer (optional)
memory_buffer = []

running = True
writer_running = True


def handle_exit(sig, frame):
    """Handles CTRL+C"""
    global running, writer_running
    print("\nStopping...")
    running = False
    writer_running = False


signal.signal(signal.SIGINT, handle_exit)


# ---------------- WRITER THREAD ----------------
def writer_thread_func():
    """Consumes queue entries and writes to CSV."""
    with open(RAW_OUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "row_index", "col_index", "value"])

        while writer_running or not write_queue.empty():
            try:
                row = write_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            writer.writerow(row)
            f.flush()


# ---------------- READER THREAD ----------------
def reader_thread_func():
    """Reads serial (row,col,val) and pushes samples to queue."""
    ser = serial.Serial(PORT, BAUD, timeout=0.01)
    print("Recording... press CTRL+C to stop\n")

    start_time = time.time()

    while running:
        line = ser.readline().decode("utf-8").strip()
        if not line:
            continue

        parts = line.split(",")
        if len(parts) != 3:
            continue

        try:
            r_idx = int(parts[0].strip())
            c_idx = int(parts[1].strip())
            val = float(parts[2].strip())
        except ValueError:
            continue

        timestamp = time.time() - start_time
        sample = [timestamp, r_idx, c_idx, val]

        write_queue.put(sample)
        memory_buffer.append(sample)


# ---------------- MAIN ----------------
def main():
    global writer_running

    # start writer thread
    wt = threading.Thread(target=writer_thread_func)
    wt.start()

    # start reader thread
    rt = threading.Thread(target=reader_thread_func)
    rt.start()

    # wait for reader to finish
    rt.join()

    # stop writer
    writer_running = False
    wt.join()

    print("Finished acquisition. Saving cleaned CSV…")

    # rewrite memory buffer to the final CSV
    with open(FINAL_OUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "row_index", "col_index", "value"])

        for item in memory_buffer:
            writer.writerow(item)

    print(f"Done!\nRaw saved:   {RAW_OUT}\nFinal saved: {FINAL_OUT}")


if __name__ == "__main__":
    main()
