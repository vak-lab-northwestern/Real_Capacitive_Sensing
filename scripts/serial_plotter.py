#!/usr/bin/env python3
"""
Live Serial Plotter for debugging capacitance sensing data.

Reads serial data from Arduino and plots in real-time.
Supports multiple channels/values per line.

Usage:
    python scripts/serial_plotter.py
    python scripts/serial_plotter.py --port /dev/cu.usbserial-210
    python scripts/serial_plotter.py --port /dev/cu.usbserial-210 --baud 115200
"""

import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import argparse
import sys
import time
import re

# Configuration
DEFAULT_PORT = "/dev/cu.usbserial-210"
DEFAULT_BAUD = 115200
MAX_POINTS = 500  # Number of data points to keep in buffer
PLOT_INTERVAL = 50  # Update interval in milliseconds

# Data buffers
timestamps = deque(maxlen=MAX_POINTS)
data_channels = {}  # Will be populated dynamically based on data format


class SerialPlotter:
    def __init__(self, port, baud_rate, timeout=1.0):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None
        self.start_time = time.time()
        self.fig = None
        self.axes = None
        self.lines = {}
        self.data_format = None  # 'main_E' or 'auto'
        
    def connect(self):
        """Connect to serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=timeout)
            print(f"[INFO] Connected to {self.port} at {self.baud_rate} baud")
            time.sleep(0.5)  # Wait for connection to stabilize
            self.ser.reset_input_buffer()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False
    
    def parse_line(self, line):
        """
        Parse serial line. Supports:
        - main_E.cpp format: Row_index,Column_index,Node_Value (3 values)
        - Generic CSV format: value1,value2,value3,...
        """
        if not line or not line.strip():
            return None
        
        # Skip header lines
        if any(keyword in line for keyword in ["Row_index", "Column_index", "FDC", "READY", "FAIL"]):
            return None
        
        parts = line.strip().split(',')
        
        if len(parts) == 3:
            # main_E.cpp format: row, col, value
            try:
                row = int(parts[0].strip())
                col = int(parts[1].strip())
                value = float(parts[2].strip())
                timestamp = time.time() - self.start_time
                
                # Store as channel: "R{row}_C{col}"
                channel_name = f"R{row}_C{col}"
                
                if channel_name not in data_channels:
                    data_channels[channel_name] = deque(maxlen=MAX_POINTS)
                    timestamps.clear()  # Reset timestamps when new channel appears
                
                # Use the same timestamp for all channels in a frame
                if len(timestamps) == 0 or timestamps[-1] < timestamp - 0.01:
                    timestamps.append(timestamp)
                    # Extend all existing channels with None for this timestamp
                    for ch in data_channels.keys():
                        while len(data_channels[ch]) < len(timestamps) - 1:
                            data_channels[ch].append(None)
                
                # Align data to timestamps
                while len(data_channels[channel_name]) < len(timestamps) - 1:
                    data_channels[channel_name].append(None)
                
                data_channels[channel_name].append(value)
                
                # Return format for plotting
                return {
                    'format': 'grid',
                    'row': row,
                    'col': col,
                    'value': value,
                    'timestamp': timestamp
                }
            except (ValueError, IndexError):
                return None
        
        elif len(parts) > 1:
            # Generic CSV format: multiple values
            try:
                values = [float(p.strip()) for p in parts]
                timestamp = time.time() - self.start_time
                
                if self.data_format is None:
                    # Initialize channels on first data
                    for i in range(len(values)):
                        ch_name = f"CH{i}"
                        data_channels[ch_name] = deque(maxlen=MAX_POINTS)
                
                timestamps.append(timestamp)
                
                for i, val in enumerate(values):
                    ch_name = f"CH{i}"
                    data_channels[ch_name].append(val)
                
                return {'format': 'multi', 'values': values, 'timestamp': timestamp}
            except ValueError:
                return None
        
        return None
    
    def setup_plot(self):
        """Setup matplotlib figure and axes."""
        self.fig, self.axes = plt.subplots(figsize=(12, 8))
        self.axes.set_xlabel('Time (s)', fontsize=12)
        self.axes.set_ylabel('Value', fontsize=12)
        self.axes.set_title('Live Serial Data Plotter', fontsize=14, fontweight='bold')
        self.axes.grid(True, alpha=0.3)
        self.axes.legend(loc='upper left')
        
        plt.tight_layout()
    
    def read_serial(self):
        """Read from serial port (non-blocking)."""
        if self.ser and self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore')
                return self.parse_line(line)
            except Exception as e:
                print(f"[WARNING] Serial read error: {e}")
                return None
        return None
    
    def update_plot(self, frame):
        """Update plot with new data."""
        # Read serial data
        result = self.read_serial()
        
        if not timestamps or not data_channels:
            return []
        
        # Clear and replot
        self.axes.clear()
        self.axes.set_xlabel('Time (s)', fontsize=12)
        self.axes.set_ylabel('Value', fontsize=12)
        self.axes.set_title(f'Live Serial Plotter - {self.port}', fontsize=14, fontweight='bold')
        self.axes.grid(True, alpha=0.3)
        
        # Plot all channels
        colors = plt.cm.tab20(range(len(data_channels)))
        plot_items = []
        
        for idx, (ch_name, values) in enumerate(data_channels.items()):
            if len(values) == 0:
                continue
            
            # Align data with timestamps
            t_data = list(timestamps)[-len(values):]
            v_data = list(values)
            
            # Filter out None values
            valid_data = [(t, v) for t, v in zip(t_data, v_data) if v is not None]
            if not valid_data:
                continue
            
            t_vals, v_vals = zip(*valid_data)
            
            line, = self.axes.plot(t_vals, v_vals, label=ch_name, 
                                  color=colors[idx % len(colors)], 
                                  linewidth=1.5, alpha=0.8)
            plot_items.append(line)
        
        if plot_items:
            self.axes.legend(loc='upper left', fontsize=8, ncol=2)
            
            # Auto-scale axes
            if len(timestamps) > 0:
                self.axes.set_xlim(max(0, timestamps[-1] - 10), timestamps[-1] + 1)
        
        return plot_items
    
    def run(self):
        """Start the live plotter."""
        if not self.connect():
            return False
        
        print("[INFO] Starting live serial plotter...")
        print("[INFO] Press CTRL+C to stop\n")
        
        self.setup_plot()
        
        # Start animation
        ani = animation.FuncAnimation(
            self.fig, 
            self.update_plot, 
            interval=PLOT_INTERVAL,
            blit=False
        )
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n[INFO] Stopping plotter...")
        finally:
            if self.ser:
                self.ser.close()
            print("[INFO] Disconnected")
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Live Serial Plotter for debugging')
    parser.add_argument('--port', '-p', type=str, default=DEFAULT_PORT,
                        help=f'Serial port (default: {DEFAULT_PORT})')
    parser.add_argument('--baud', '-b', type=int, default=DEFAULT_BAUD,
                        help=f'Baud rate (default: {DEFAULT_BAUD})')
    parser.add_argument('--timeout', '-t', type=float, default=1.0,
                        help='Serial timeout in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    plotter = SerialPlotter(args.port, args.baud, args.timeout)
    success = plotter.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

