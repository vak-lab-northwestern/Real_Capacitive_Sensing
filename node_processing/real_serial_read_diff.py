import serial
import time
import threading
import signal
import sys
import math
import csv
import os
import glob
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.ndimage import zoom
from collections import deque
import queue

# Serial port configuration
# Auto-detect port, or set manually if auto-detection fails
AUTO_DETECT_PORT = True
PORT = "/dev/cu.usbserial-210"  # Fallback if auto-detection fails
BAUD = 115200

# Set to True to list available serial ports on startup
LIST_PORTS = True

# Grid configuration: 8x8 = 64 nodes
NUM_ROWS = 8
NUM_COLS = 8
TOTAL_NODES = NUM_ROWS * NUM_COLS

# Visualization configuration
# Individual sphere rendering parameters for each contact region
GRID_RES = 400  # Resolution for sphere visualization (higher = smoother spheres)
SPHERE_SIZE_FACTOR = 0.045  # Controls size of each sphere (smaller = more distinct spheres)
HEAT_BLUR = 1.5  # Light blur applied to each sphere for smooth edges

# Delta capacitance range for display (normalized change: delta_C/C_0)
# These are percentage changes relative to baseline
DELTA_C_MIN = -0.10  # -10% change (negative = decrease in capacitance)
DELTA_C_MAX = 0.10   # +10% change (positive = increase in capacitance)

# FDC2214 constants for raw to capacitance conversion
REF_CLOCK = 40e6  # Hz
SCALE_FACTOR = REF_CLOCK / (2 ** 28)  # ~0.149 Hz per LSB
INDUCTANCE = 180e-9  # H

# Thread-safe data structures
frame_buffer = {}  # Current frame being built: {(row, col): value}
completed_frames = deque(maxlen=10)  # Keep last 10 frames for smooth animation
lock = threading.Lock()

# Baseline capacitance tracking (C_0)
baseline_c0 = {}  # {(row, col): baseline_capacitance_pF} - stable state reference
baseline_ready = False  # True when baseline has been established
BASELINE_FRAMES = 5  # Number of frames to average for baseline calibration
baseline_frames_collected = 0
baseline_values_history = []  # List of frames for baseline averaging

# CSV file paths (will be created with timestamp in ../data directory)
DATA_DIR = "../data"
csv_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_RAW = os.path.join(DATA_DIR, f"{csv_timestamp}_raw_realtime_cap_data.csv")
CSV_PF = os.path.join(DATA_DIR, f"{csv_timestamp}_realtime_cap_data_pF.csv")


# Queue for passing samples to CSV writer thread
csv_queue = queue.Queue()

running = True
writer_running = True

# Statistics
samples_received = 0
frames_completed = 0
invalid_samples = 0
current_timestamp = 0.0

# Capacitance value tracking for debugging
cap_min = float('inf')
cap_max = float('-inf')

# Serial connection (initialized in reader thread)
ser = None


def handle_exit(sig, frame):
    """Handles CTRL+C"""
    global running, writer_running
    print("\nStopping...")
    running = False
    writer_running = False
    if ser:
        ser.close()


signal.signal(signal.SIGINT, handle_exit)


# ---------------- SERIAL PORT UTILITIES ----------------
def list_serial_ports():
    """List available serial ports (helpful for debugging)."""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    print("\n[DEBUG] Available serial ports:")
    if not ports:
        print("  No serial ports found!")
    else:
        for port in ports:
            print(f"  {port.device} - {port.description}")
    print()


def find_arduino_port():
    """Auto-detect Arduino serial port on macOS."""
    import serial.tools.list_ports
    import glob
    
    # Common macOS Arduino port patterns (use cu.* not tty.* for serial communication)
    patterns = [
        "/dev/cu.usbserial-*",
        "/dev/cu.usbmodem*",
        "/dev/cu.wchusbserial*",
        "/dev/cu.SLAB_USBtoUART*"
    ]
    
    # Try pattern matching first
    for pattern in patterns:
        ports = glob.glob(pattern)
        if ports:
            # Prefer ports that look like Arduino (USB Serial)
            for port in sorted(ports):
                if "usbserial" in port or "usbmodem" in port:
                    print(f"[DEBUG] Auto-detected port via pattern: {port}")
                    return port
    
    # Fall back to serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.device.startswith("/dev/cu.") and ("usb" in port.device.lower() or "serial" in port.description.lower()):
            print(f"[DEBUG] Auto-detected port via list_ports: {port.device}")
            return port.device
    
    return None


# ---------------- CAPACITANCE CONVERSION (from data_logger.py) ----------------
def raw_to_capacitance(raw):
    """
    Convert raw FDC2214 reading to capacitance in picofarads (pF).
    """
    freq = raw * SCALE_FACTOR
    if freq <= 0:
        return 0
    cap_F = 1.0 / ((2 * math.pi * freq) ** 2 * INDUCTANCE)
    return cap_F * 1e12  # convert to picofarads


# ---------------- BASELINE AND DELTA COMPUTATION ----------------
def establish_baseline(frame_grid):
    """
    Establish baseline C_0 from initial stable frames.
    Stores average capacitance for each node.
    """
    global baseline_c0, baseline_frames_collected, baseline_ready, baseline_values_history
    
    baseline_values_history.append(frame_grid.copy())
    baseline_frames_collected += 1
    
    if baseline_frames_collected >= BASELINE_FRAMES:
        # Average all collected baseline frames
        baseline_array = np.array(baseline_values_history)
        baseline_avg = np.mean(baseline_array, axis=0)
        
        # Store baseline for each node
        for r in range(NUM_ROWS):
            for c in range(NUM_COLS):
                baseline_c0[(r, c)] = baseline_avg[r, c]
        
        baseline_ready = True
        print(f"[DEBUG] Baseline C_0 established from {BASELINE_FRAMES} frames")
        print(f"[DEBUG] Baseline range: [{np.min(baseline_avg):.2f}, {np.max(baseline_avg):.2f}] pF")
        return True
    
    return False


def compute_delta_c_normalized(frame_grid):
    """
    Compute delta_C/C_0 = (C - C_0) / C_0 for each node.
    
    Returns:
        2D numpy array of delta_C/C_0 values (normalized change)
    """
    delta_grid = np.zeros((NUM_ROWS, NUM_COLS))
    
    if not baseline_ready or len(baseline_c0) == 0:
        return delta_grid  # Return zeros if baseline not ready
    
    for r in range(NUM_ROWS):
        for c in range(NUM_COLS):
            c_current = frame_grid[r, c]
            c0 = baseline_c0.get((r, c), c_current)
            
            if c0 > 0:
                delta_c = c_current - c0
                delta_normalized = delta_c / c0
                delta_grid[r, c] = delta_normalized
            else:
                delta_grid[r, c] = 0.0
    
    return delta_grid


# ---------------- GRID PROCESSING FUNCTIONS (from process_csv.py) ----------------
def frame_to_grid(frame_data, num_rows=NUM_ROWS, num_cols=NUM_COLS):
    """
    Convert frame data dictionary {(row, col): raw_value} to 2D grid array in pF.
    Similar to process_csv.py logic but for in-memory data.
    Converts raw values to capacitance in pF.
    """
    grid = np.zeros((num_rows, num_cols))
    for (r, c), raw_value in frame_data.items():
        if 0 <= r < num_rows and 0 <= c < num_cols:
            grid[r, c] = raw_to_capacitance(raw_value)
    return grid


# ---------------- GAUSSIAN BLUR FUNCTIONS (from v5pMap.py) ----------------
def gaussian1d(sigma_px, radius=None):
    """Create 1D Gaussian kernel."""
    if sigma_px <= 0:
        return np.array([1.0])
    if radius is None:
        radius = max(1, int(3 * sigma_px))
    xs = np.arange(-radius, radius + 1)
    k = np.exp(-(xs**2) / (2 * sigma_px**2))
    return k / k.sum()


def gaussian_blur(arr, sigma_px=3):
    """Apply 2D Gaussian blur to array."""
    if sigma_px <= 0:
        return arr
    k = gaussian1d(sigma_px)
    arr = np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'),
                              axis=1, arr=arr)
    arr = np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'),
                              axis=0, arr=arr)
    return arr


# ---------------- INDIVIDUAL SPHERE GENERATION ----------------
def create_individual_spheres(delta_grid, grid_res=GRID_RES, sphere_size_factor=SPHERE_SIZE_FACTOR, heat_blur=HEAT_BLUR):
    """
    Create individual spheres for each grid position representing contact regions.
    Each grid node gets its own distinct sphere with intensity based on delta_C/C_0.
    
    Args:
        delta_grid: 2D numpy array of shape (NUM_ROWS, NUM_COLS) with delta_C/C_0 values
        grid_res: Resolution of output field
        sphere_size_factor: Controls size of each sphere (fraction of grid span)
        heat_blur: Blur applied to each individual sphere for smoothness
    
    Returns:
        2D numpy array of shape (grid_res, grid_res) with individual spheres
    """
    # Normalize delta_C/C_0 values for visualization
    # We'll use absolute values for sphere intensity, but keep sign for color mapping
    grid_normalized = np.copy(delta_grid)
    # Clip values to range
    grid_normalized = np.clip(grid_normalized, DELTA_C_MIN, DELTA_C_MAX)
    # Normalize to 0-1 range for intensity
    intensity_grid = (grid_normalized - DELTA_C_MIN) / (DELTA_C_MAX - DELTA_C_MIN)
    
    # Create meshgrid for field (using indices 1-8)
    x_grid = np.linspace(1, NUM_COLS, grid_res)
    y_grid = np.linspace(1, NUM_ROWS, grid_res)
    X, Y = np.meshgrid(x_grid, y_grid)
    
    # Initialize field
    F = np.zeros_like(X)
    
    # Calculate sphere size (sigma) - each sphere should be isolated
    span = max(NUM_COLS, NUM_ROWS)  # Span in index units
    sigma = sphere_size_factor * span  # Sphere size in index units
    
    # Create individual sphere for each grid node
    for r in range(NUM_ROWS):
        for c in range(NUM_COLS):
            # Use 1-based indices (1-8)
            x_pos = c + 1
            y_pos = r + 1
            intensity = intensity_grid[r, c]
            
            # Only create sphere if there's a significant change
            if intensity > 0.01:  # Threshold to avoid showing noise
                # Create gaussian sphere centered at this node position
                g = np.exp(-(((X - x_pos)**2) / (2 * sigma**2) +
                             ((Y - y_pos)**2) / (2 * sigma**2)))
                
                # Scale sphere by intensity (higher delta_C/C_0 = brighter/larger sphere)
                F += intensity * g
    
    # Clip and normalize field
    F = np.clip(F, 0, 1)
    
    # Apply light blur to each sphere for smooth edges
    if heat_blur > 0:
        F = gaussian_blur(F, sigma_px=heat_blur)
    
    return F


# ---------------- CSV WRITER THREAD ----------------
def csv_writer_thread_func():
    """Writes samples from queue to CSV files (raw and pF)."""
    global writer_running
    
    print(f"[DEBUG] CSV writer thread starting...")
    print(f"[DEBUG] CSV files: {CSV_RAW}, {CSV_PF}")
    
    try:
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"[DEBUG] Data directory: {os.path.abspath(DATA_DIR)}")
        
        # Open CSV files for writing
        raw_file = open(CSV_RAW, "w", newline="")
        pf_file = open(CSV_PF, "w", newline="")
        
        raw_writer = csv.writer(raw_file)
        pf_writer = csv.writer(pf_file)
        
        # Write headers (matching Arduino format: row_index, col_index, value)
        raw_writer.writerow(["row_index", "col_index", "raw_value"])
        pf_writer.writerow(["row_index", "col_index", "capacitance_pF"])
        
        raw_file.flush()
        pf_file.flush()
        print(f"[DEBUG] CSV headers written successfully")
        
        rows_written = 0
        
        while writer_running or not csv_queue.empty():
            try:
                # Get sample from queue: [timestamp, row, col, raw_value]
                sample = csv_queue.get(timeout=0.1)
                timestamp, r_idx, c_idx, raw_value = sample
                
                # Write raw data (without timestamp, matching Arduino format)
                raw_writer.writerow([r_idx, c_idx, raw_value])
                
                # Convert and write capacitance in pF (without timestamp)
                cap_pf = raw_to_capacitance(raw_value)
                pf_writer.writerow([r_idx, c_idx, cap_pf])
                
                rows_written += 1
                
                # Flush to disk for crash safety
                raw_file.flush()
                pf_file.flush()
                
                # Debug: print first few writes
                if rows_written <= 5:
                    print(f"[DEBUG] CSV write #{rows_written}: row={r_idx}, col={c_idx}, raw={raw_value}, cap={cap_pf:.2f} pF")
                elif rows_written % 100 == 0:
                    print(f"[DEBUG] CSV: {rows_written} rows written")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ERROR] CSV write error: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Close files
        raw_file.close()
        pf_file.close()
        print(f"\n[DEBUG] CSV writer thread finished. Total rows written: {rows_written}")
        print(f"CSV files saved:")
        print(f"  Raw data: {CSV_RAW}")
        print(f"  Capacitance (pF): {CSV_PF}")
        
    except Exception as e:
        print(f"[ERROR] CSV writer thread failed to start: {e}")
        import traceback
        traceback.print_exc()


# ---------------- READER THREAD ----------------
def reader_thread_func():
    """Reads serial data from Arduino and builds frames for real-time visualization."""
    global samples_received, frames_completed, invalid_samples, current_timestamp, frame_buffer, ser
    
    # Determine which port to use
    port_to_use = PORT
    if AUTO_DETECT_PORT:
        detected_port = find_arduino_port()
        if detected_port:
            port_to_use = detected_port
        else:
            print(f"[WARNING] Auto-detection failed, using fallback port: {PORT}")
    else:
        print(f"[DEBUG] Using manually specified port: {PORT}")
    
    print(f"[DEBUG] Attempting to connect to: {port_to_use}")
    
    # Try to open serial port with error handling
    try:
        ser = serial.Serial(port_to_use, BAUD, timeout=0.01)
        # Wait a moment for port to initialize
        time.sleep(0.5)
        # Flush any stale data in buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print("=" * 60)
        print("8x8 Capacitance Sensor Real-Time Visualization")
        print(f"Grid: {NUM_ROWS}x{NUM_COLS} = {TOTAL_NODES} nodes")
        print(f"Serial Port: {port_to_use}")
        print(f"Baud Rate: {BAUD}")
        print(f"CSV Output: {CSV_RAW}, {CSV_PF}")
        print("=" * 60)
        print(f"[DEBUG] Serial port opened successfully")
        print(f"[DEBUG] Port info: {ser}")
        print(f"[DEBUG] Waiting for data... Close window or press CTRL+C to stop\n")
    except serial.SerialException as e:
        print(f"[ERROR] Failed to open serial port {PORT}: {e}")
        print(f"[ERROR] Please check:")
        print(f"  1. Arduino is connected and powered on")
        print(f"  2. Port name is correct (current: {PORT})")
        print(f"  3. No other program is using the port")
        return
    except Exception as e:
        print(f"[ERROR] Unexpected error opening serial port: {e}")
        return

    start_time = time.time()
    last_frame_time = start_time
    debug_line_count = 0
    last_debug_time = start_time
    lines_received = 0
    lines_skipped = 0

    while running:
        try:
            raw_line = ser.readline()
            if not raw_line:
                continue
            
            line = raw_line.decode("utf-8", errors="ignore").strip()
            lines_received += 1
            
            # Debug: print first few lines and periodically
            if debug_line_count < 10 or (time.time() - last_debug_time) > 2.0:
                print(f"[DEBUG] Line {lines_received}: '{line}'")
                debug_line_count += 1
                last_debug_time = time.time()
            
            if not line:
                continue

            # Skip Arduino header/info messages
            line_upper = line.upper()
            if any(skip in line_upper for skip in ["FDC", "READY", "FAIL", "ROW_INDEX", "COLUMN_INDEX", "NODE_VALUE"]):
                lines_skipped += 1
                if debug_line_count < 10:
                    print(f"[DEBUG] Skipped header line: '{line}'")
                continue

            parts = line.split(",")
            if len(parts) != 3:
                invalid_samples += 1
                if debug_line_count < 10:
                    print(f"[DEBUG] Invalid format (expected 3 parts, got {len(parts)}): '{line}'")
                continue

            try:
                r_idx = int(parts[0].strip())
                c_idx = int(parts[1].strip())
                raw_value = int(parts[2].strip())  # Raw capacitance is typically an integer
                
                # Validate indices are within 8x8 grid bounds
                if r_idx < 0 or r_idx >= NUM_ROWS or c_idx < 0 or c_idx >= NUM_COLS:
                    invalid_samples += 1
                    if debug_line_count < 10:
                        print(f"[DEBUG] Invalid indices (row={r_idx}, col={c_idx}): '{line}'")
                    continue
                    
            except ValueError as e:
                invalid_samples += 1
                if debug_line_count < 10:
                    print(f"[DEBUG] ValueError parsing line '{line}': {e}")
                continue
            
            # Successfully parsed a sample!
            if samples_received == 0:
                print(f"[DEBUG] First valid sample received: row={r_idx}, col={c_idx}, value={raw_value}")
            
            with lock:
                current_timestamp = time.time() - start_time
                node_key = (r_idx, c_idx)
                
                # Arduino scans sequentially: (0,0) -> (0,7) -> (1,0) -> ... -> (7,7) -> (0,0)...
                # Detect new frame start: if we see (0,0) and already have nodes, previous frame is complete
                if node_key == (0, 0) and len(frame_buffer) >= TOTAL_NODES:
                    frames_completed += 1
                    frame_duration = time.time() - last_frame_time
                    
                    # Add completed frame to deque for visualization
                    completed_frame = frame_buffer.copy()
                    completed_frames.append((current_timestamp, completed_frame))
                    
                    frame_buffer.clear()
                    last_frame_time = time.time()
                    print(f"[DEBUG] Frame {frames_completed} complete ({1.0/frame_duration:.2f} Hz)")
                
                frame_buffer[node_key] = raw_value
            
            # Send sample to CSV writer queue
            sample = [current_timestamp, r_idx, c_idx, raw_value]
            try:
                csv_queue.put(sample, timeout=0.1)
                if samples_received == 0:
                    print(f"[DEBUG] First sample queued for CSV: row={r_idx}, col={c_idx}, value={raw_value}")
            except queue.Full:
                print(f"[WARNING] CSV queue is full! Dropping sample.")
            
            samples_received += 1
            
            # Print status every 100 samples
            if samples_received % 100 == 0:
                elapsed = time.time() - start_time
                print(f"[DEBUG] Progress: {samples_received} samples, {frames_completed} frames, "
                      f"{lines_received} lines received, {lines_skipped} skipped, {invalid_samples} invalid")
        
        except serial.SerialException as e:
            print(f"[ERROR] Serial port error: {e}")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error in reader thread: {e}")
            import traceback
            traceback.print_exc()
            continue

        with lock:
            current_timestamp = time.time() - start_time
            node_key = (r_idx, c_idx)
            
            # Arduino scans sequentially: (0,0) -> (0,7) -> (1,0) -> ... -> (7,7) -> (0,0)...
            # Detect new frame start: if we see (0,0) and already have nodes, previous frame is complete
            if node_key == (0, 0) and len(frame_buffer) >= TOTAL_NODES:
                frames_completed += 1
                frame_duration = time.time() - last_frame_time
                
                # Add completed frame to deque for visualization
                completed_frame = frame_buffer.copy()
                completed_frames.append((current_timestamp, completed_frame))
                
                frame_buffer.clear()
                last_frame_time = time.time()
            
            frame_buffer[node_key] = raw_value
        
        # Send sample to CSV writer queue
        sample = [current_timestamp, r_idx, c_idx, raw_value]
        csv_queue.put(sample)
        
        samples_received += 1


# ---------------- VISUALIZATION SETUP ----------------
def setup_visualization():
    """Set up matplotlib figure with individual sphere visualization for each contact region."""
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Initialize with empty grid
    empty_grid = np.zeros((NUM_ROWS, NUM_COLS))
    sphere_field = create_individual_spheres(empty_grid)
    
    # Display individual spheres for each contact region
    # Use 1-8 indices for axes (not normalized)
    # Use 'hot' colormap to show intensity of contact (brighter = higher delta_C/C_0)
    im = ax.imshow(sphere_field, cmap="hot", aspect='equal', origin='lower',
                   extent=[0.5, NUM_COLS + 0.5, 0.5, NUM_ROWS + 0.5],
                   interpolation='bilinear', vmin=0, vmax=1)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("ΔC/C₀ Intensity", rotation=270, labelpad=20)
    
    ax.set_title("8x8 Capacitance Sensor - Real-Time ΔC/C₀ Visualization", 
                fontsize=14, fontweight='bold')
    ax.set_xlabel("Column Index", fontsize=12)
    ax.set_ylabel("Row Index", fontsize=12)
    
    # Set ticks to show 1-8 indices
    ax.set_xticks(range(1, NUM_COLS + 1))
    ax.set_yticks(range(1, NUM_ROWS + 1))
    
    # Add grid lines to show node positions
    for i in range(1, NUM_ROWS + 2):
        ax.axhline(i, color='white', linestyle='--', alpha=0.15, linewidth=0.5)
    for i in range(1, NUM_COLS + 2):
        ax.axvline(i, color='white', linestyle='--', alpha=0.15, linewidth=0.5)
    
    # Add node position markers to clearly show where each contact region is
    for r in range(NUM_ROWS):
        for c in range(NUM_COLS):
            x_pos = c + 1
            y_pos = r + 1
            ax.plot(x_pos, y_pos, 'o', color='white', markersize=3, alpha=0.3, markeredgewidth=0.5)
    
    # Add text for statistics
    stats_text = ax.text(0.02, 0.98, "", transform=ax.transAxes, 
                        fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    return fig, ax, im, stats_text


# ---------------- ANIMATION UPDATE ----------------
def make_update_function(im, stats_text):
    """Create update function with access to visualization objects."""
    def update_visualization(frame):
        """Update function for matplotlib animation."""
        global completed_frames, frame_buffer, current_timestamp, cap_min, cap_max
        
        with lock:
            # Use latest completed frame if available, otherwise use current frame being built
            if completed_frames:
                timestamp, frame_data = completed_frames[-1]
            elif frame_buffer and len(frame_buffer) >= TOTAL_NODES:
                timestamp = current_timestamp
                frame_data = frame_buffer.copy()
            elif frame_buffer:
                timestamp = current_timestamp
                frame_data = frame_buffer.copy()
            else:
                # No data yet
                return [im, stats_text]
        
        # Convert frame data to grid (capacitance values in pF)
        grid = frame_to_grid(frame_data)
        
        # Establish baseline if not ready yet
        if not baseline_ready:
            establish_baseline(grid)
            # Show baseline collection message
            sphere_field = np.zeros((GRID_RES, GRID_RES))
            im.set_data(sphere_field)
            im.set_clim(vmin=0, vmax=1)
            
            stats_str = (f"Calibrating baseline...\n"
                        f"Frame {baseline_frames_collected}/{BASELINE_FRAMES}\n"
                        f"Please keep sensor stable")
            stats_text.set_text(stats_str)
            return [im, stats_text]
        
        # Compute delta_C/C_0 (normalized change from baseline)
        delta_grid = compute_delta_c_normalized(grid)
        
        # Track min/max delta values for debugging
        delta_min = np.min(delta_grid)
        delta_max = np.max(delta_grid)
        if delta_max > delta_min:
            cap_min = min(cap_min, delta_min) if cap_min != float('inf') else delta_min
            cap_max = max(cap_max, delta_max) if cap_max != float('-inf') else delta_max
        
        # Create individual spheres for each contact region
        sphere_field = create_individual_spheres(delta_grid)
        
        # Update visualization with sphere field (intensity range 0-1)
        im.set_data(sphere_field)
        im.set_clim(vmin=0, vmax=1)
        
        # Update statistics text
        stats_str = (f"Time: {timestamp:.2f}s\n"
                    f"Frames: {frames_completed}\n"
                    f"Samples: {samples_received}\n"
                    f"Invalid: {invalid_samples}")
        if frames_completed > 0 and timestamp > 0:
            frame_rate = frames_completed / timestamp
            stats_str += f"\nRate: {frame_rate:.2f} Hz"
        if cap_min != float('inf') and cap_max != float('-inf'):
            stats_str += f"\nΔC/C₀ range: [{cap_min:.3f}, {cap_max:.3f}]"
        stats_str += f"\nColor range: [{DELTA_C_MIN:.1%}, {DELTA_C_MAX:.1%}]"
        stats_text.set_text(stats_str)
        
        return [im, stats_text]
    
    return update_visualization


# ---------------- MAIN ----------------
def main():
    global running, writer_running
    
    # List available ports if requested
    if LIST_PORTS:
        list_serial_ports()
    
    # Start CSV writer thread (not daemon so it can finish writing on exit)
    csv_writer_thread = threading.Thread(target=csv_writer_thread_func, daemon=False)
    csv_writer_thread.start()
    print(f"[DEBUG] CSV writer thread started")
    
    # Start reader thread
    reader_thread = threading.Thread(target=reader_thread_func, daemon=True)
    reader_thread.start()
    print(f"[DEBUG] Reader thread started")
    
    # Give threads time to initialize
    time.sleep(0.5)
    
    # Check queue status
    print(f"[DEBUG] Initial queue size: {csv_queue.qsize()}")
    
    # Setup visualization
    fig, ax, im, stats_text = setup_visualization()
    
    # Create update function with access to visualization objects
    update_func = make_update_function(im, stats_text)
    
    # Setup animation
    ani = FuncAnimation(fig, update_func, interval=50, blit=False, cache_frame_data=False)
    
    # Show plot (blocks until window is closed)
    plt.tight_layout()
    plt.show()
    
    # Cleanup
    running = False
    writer_running = False
    
    print("\n[DEBUG] Stopping threads...")
    print(f"[DEBUG] Queue size before cleanup: {csv_queue.qsize()}")
    print(f"[DEBUG] Samples received: {samples_received}")
    
    # Wait for CSV writer to finish writing remaining data
    print("[DEBUG] Waiting for CSV writer to finish...")
    csv_writer_thread.join(timeout=5.0)
    
    if csv_writer_thread.is_alive():
        print("[WARNING] CSV writer thread did not finish in time")
    else:
        print("[DEBUG] CSV writer thread finished")
    
    if ser:
        ser.close()
    
    print("\n" + "=" * 60)
    print("Visualization stopped.")
    print(f"Total frames received: {frames_completed}")
    print(f"Total samples: {samples_received}")
    print(f"Final queue size: {csv_queue.qsize()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
