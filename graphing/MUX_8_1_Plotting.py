import serial
import csv
import math
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import numpy as np

# FDC2214 constants 
REF_CLOCK = 40e6  # Hz
SCALE_FACTOR = REF_CLOCK / (2 ** 28)
INDUCTANCE = 18e-6  # H
CHANNEL_NUM = 32    # total MUXed channels

# Plot settings
PLOT_WINDOW_S = 30  # seconds of data to display
MAX_POINTS = 1000   # maximum points to keep in memory per channel

def raw_to_capacitance(raw):
    freq = raw * SCALE_FACTOR
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * INDUCTANCE)
    return cap_F * 1e12  # pF

# --- Serial setup ---
PORT = "COM9"      # Change to your Nano's port
BAUD = 115200
TIMEOUT_S = 0.1    # Shorter timeout for responsive plotting

def choose_output_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Select CSV file to save readings"
    )
    root.destroy()
    return file_path

class LivePlotter:
    def __init__(self, num_channels, window_s):
        self.num_channels = num_channels
        self.window_s = window_s
        
        # Store data for each channel
        self.times = deque(maxlen=MAX_POINTS)
        self.data = [deque(maxlen=MAX_POINTS) for _ in range(num_channels)]
        
        # Create single plot with all channels
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.fig.suptitle('FDC2214 Live Capacitance Readings - All Channels', fontsize=14)
        
        # Generate colors for each channel
        colors = plt.cm.tab20(np.linspace(0, 1, 20))
        colors2 = plt.cm.tab20b(np.linspace(0, 1, 12))
        all_colors = np.vstack([colors, colors2])
        
        # Initialize lines for each channel
        self.lines = []
        for i in range(num_channels):
            line, = self.ax.plot([], [], linewidth=1.0, label=f'CH{i}', 
                                color=all_colors[i], alpha=0.7)
            self.lines.append(line)
        
        self.ax.set_xlabel('Time (s)', fontsize=12)
        self.ax.set_ylabel('Capacitance (pF)', fontsize=12)
        self.ax.grid(True, alpha=0.3)
        
        # Create legend outside plot area
        self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), 
                      fontsize=8, ncol=2)
        
        plt.tight_layout()
        
    def update(self, timestamp, capacitances):
        """Add new data point"""
        self.times.append(timestamp)
        for i, cap in enumerate(capacitances):
            self.data[i].append(cap)
    
    def refresh_plot(self):
        """Update all plot lines"""
        if len(self.times) == 0:
            return
        
        times_array = np.array(self.times)
        current_time = times_array[-1]
        
        # Only show data within the time window
        mask = times_array >= (current_time - self.window_s)
        visible_times = times_array[mask]
        
        all_data = []
        
        # Update each channel
        for i in range(self.num_channels):
            data_array = np.array(self.data[i])
            visible_data = data_array[mask]
            
            if len(visible_times) > 0:
                self.lines[i].set_data(visible_times, visible_data)
                all_data.extend(visible_data)
        
        # Auto-scale axes
        if len(visible_times) > 0:
            self.ax.set_xlim(max(0, current_time - self.window_s), current_time + 1)
            
            if len(all_data) > 0:
                data_min, data_max = min(all_data), max(all_data)
                margin = (data_max - data_min) * 0.1 if data_max > data_min else 1
                self.ax.set_ylim(data_min - margin, data_max + margin)
        
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

def main():
    file_path = choose_output_file()
    if not file_path:
        print("[INFO] Logging cancelled (no file selected).")
        return
    
    print(f"[INFO] Opening serial port {PORT}...")
    ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT_S)
    print(f"[INFO] Serial connected to {PORT}")
    
    # Initialize live plotter
    plotter = LivePlotter(CHANNEL_NUM, PLOT_WINDOW_S)
    plt.ion()  # Enable interactive mode
    plt.show()
    
    # Open CSV file
    with open(file_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        header = ["timestamp_s"] + [f"CH{i}_pF" for i in range(CHANNEL_NUM)]
        writer.writerow(header)
        
        start_time = time.time()
        duration_s = 120  # <-- how long to record (seconds)
        last_plot_update = 0
        plot_update_interval = 0.1  # Update plot every 100ms
        
        print(f"[INFO] Logging for {duration_s} seconds to {file_path} ...")
        print("[INFO] Close the plot window to stop logging early.")
        
        try:
            while plt.fignum_exists(plotter.fig.number):
                now = time.time()
                elapsed = now - start_time
                
                if elapsed > duration_s:
                    print("[INFO] Logging time limit reached.")
                    break
                
                raw_line = ser.readline().decode(errors="ignore").strip()
                if not raw_line:
                    # Give matplotlib a chance to process events
                    plt.pause(0.001)
                    continue
                
                parts = raw_line.split(",")
                if len(parts) != CHANNEL_NUM:
                    continue  # skip incomplete/malformed lines
                
                try:
                    raw_vals = [int(p) for p in parts]
                except ValueError:
                    continue
                
                caps = [raw_to_capacitance(r) for r in raw_vals]
                timestamp = elapsed
                
                # Write to CSV
                writer.writerow([timestamp] + caps)
                
                # Update plotter data
                plotter.update(timestamp, caps)
                
                # Refresh plot at specified interval
                if now - last_plot_update >= plot_update_interval:
                    plotter.refresh_plot()
                    last_plot_update = now
                    
        except KeyboardInterrupt:
            print("\n[INFO] Logging stopped by user.")
        finally:
            ser.close()
            plt.ioff()
            plt.close('all')
            print("[INFO] Serial closed.")
            print(f"[INFO] CSV saved → {file_path}")
            print(f"[INFO] Total time logged: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()