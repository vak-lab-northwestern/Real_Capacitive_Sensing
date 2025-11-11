import serial
import csv
import math
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import numpy as np

# --- Constants ---
REF_CLOCK = 40e6
SCALE_FACTOR = REF_CLOCK / (2 ** 28)
INDUCTANCE = 18e-6
CHANNEL_NUM = 32
PORT = "COM9"
BAUD = 115200
TIMEOUT_S = 0.1
MAX_POINTS = 1000
PLOT_WINDOW_S = 30

def raw_to_capacitance(raw):
    freq = raw * SCALE_FACTOR
    if freq <= 0:
        return 0.0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * INDUCTANCE)
    return cap_F * 1e12  # pF

class LivePlotter:
    def __init__(self, root, num_channels, window_s):
        self.root = root
        self.num_channels = num_channels
        self.window_s = window_s
        
        self.times = deque(maxlen=MAX_POINTS)
        self.data = [deque(maxlen=MAX_POINTS) for _ in range(num_channels)]
        
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fig.suptitle('FDC2214 Live Capacitance Readings')
        
        colors = plt.cm.tab20(np.linspace(0, 1, num_channels))
        self.lines = []
        for i in range(num_channels):
            (line,) = self.ax.plot([], [], label=f"CH{i}", color=colors[i % len(colors)])
            self.lines.append(line)
        
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Capacitance (pF)")
        self.ax.grid(True)
        self.ax.legend(loc="upper right", fontsize=8)
        
        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.draw()
        
    def update(self, timestamp, caps):
        self.times.append(timestamp)
        for i, cap in enumerate(caps):
            self.data[i].append(cap)
        self.refresh_plot()
        
    def refresh_plot(self):
        if not self.times:
            return
        
        t = np.array(self.times)
        current_time = t[-1]
        mask = t >= (current_time - self.window_s)
        t_visible = t[mask]
        
        all_vals = []
        for i in range(self.num_channels):
            y = np.array(self.data[i])[mask]
            if len(y) > 0:
                self.lines[i].set_data(t_visible, y)
                all_vals.extend(y)
        
        if len(t_visible) > 0:
            self.ax.set_xlim(max(0, current_time - self.window_s), current_time + 1)
            if len(all_vals) > 0:
                ymin, ymax = min(all_vals), max(all_vals)
                margin = (ymax - ymin) * 0.1 if ymax > ymin else 1
                self.ax.set_ylim(ymin - margin, ymax + margin)
        
        self.canvas.draw_idle()

class MuxLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MUX Capacitance Live Plot")
        
        self.plotter = LivePlotter(root, CHANNEL_NUM, PLOT_WINDOW_S)
        
        # Buttons
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(self.control_frame, text="Start Logging", command=self.toggle_logging)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.file_btn = ttk.Button(self.control_frame, text="Select CSV File", command=self.choose_output_file)
        self.file_btn.pack(side=tk.LEFT, padx=10)
        
        self.status_label = ttk.Label(self.control_frame, text="Status: Idle")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.is_logging = False
        self.ser = None
        self.log_thread = None
        self.file_path = None
    
    def choose_output_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save data to CSV"
        )
        if path:
            self.file_path = path
            self.status_label.config(text=f"Selected file: {path.split('/')[-1]}")
        
    def toggle_logging(self):
        if not self.is_logging:
            if not self.file_path:
                messagebox.showwarning("No File", "Please select a CSV output file first.")
                return
            self.start_logging()
        else:
            self.stop_logging()
    
    def start_logging(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT_S)
        except Exception as e:
            messagebox.showerror("Serial Error", str(e))
            return
        
        self.is_logging = True
        self.start_time = time.time()
        self.status_label.config(text="Status: Logging...")
        self.start_btn.config(text="Stop Logging")
        
        self.log_thread = threading.Thread(target=self.log_loop, daemon=True)
        self.log_thread.start()
    
    def stop_logging(self):
        self.is_logging = False
        self.start_btn.config(text="Start Logging")
        self.status_label.config(text="Status: Stopped")
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def log_loop(self):
        with open(self.file_path, "w", newline="") as f:
            writer = csv.writer(f)
            header = ["timestamp_s"] + [f"CH{i}_pF" for i in range(CHANNEL_NUM)]
            writer.writerow(header)
            
            while self.is_logging:
                raw_line = self.ser.readline().decode(errors="ignore").strip()
                if not raw_line:
                    continue
                
                parts = raw_line.split(",")
                if len(parts) != CHANNEL_NUM:
                    continue
                
                try:
                    raw_vals = [int(p) for p in parts]
                except ValueError:
                    continue
                
                caps = [raw_to_capacitance(r) for r in raw_vals]
                timestamp = time.time() - self.start_time
                
                writer.writerow([timestamp] + caps)
                self.plotter.update(timestamp, caps)
                
                time.sleep(0.05)  # reduce CPU load
        
        self.stop_logging()

# --- Run ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MuxLoggerApp(root)
    root.mainloop()
