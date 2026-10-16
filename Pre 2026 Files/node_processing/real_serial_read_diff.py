import serial
import time
import threading
import signal
import sys
import csv
import os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.ndimage import zoom
from collections import deque
import queue

# Configuration
AUTO_DETECT_PORT = True
PORT = "/dev/cu.usbserial-10"
BAUD = 115200

NUM_ROWS = 8
NUM_COLS = 8
TOTAL_NODES = NUM_ROWS * NUM_COLS
INTERP_SCALE = 20  # Interpolation scale for smooth visualization (similar to Multi-Touch Kit)
TOUCH_THRESHOLD = 0.0001  # Minimum |ΔC/C₀| to display as touch (0.01% change - tuned for actual data)
DELTA_C_MIN = -0.001  # Color range adjusted based on observed data (±0.0003 range)
DELTA_C_MAX = 0.001   # Color range adjusted based on observed data (±0.0003 range)
DEBUG_MODE = True  # Enable debug output to see raw values

# 4-node configuration (2x2 grid)
ACTIVE_NODES = [(0, 0), (0, 1), (1, 0), (1, 1)]  # Your 4 connected nodes

BASELINE_TIME_SEC = 10.0  # Reduced from 10s for faster startup
DATA_DIR = "../data"
NUM_ACTIVE_NODES = len(ACTIVE_NODES)  # Only scan 4 nodes instead of 64

# Global state
frame_buffer = {}
completed_frames = deque(maxlen=10)
lock = threading.Lock()
baseline_c0 = {}
baseline_ready = False
baseline_start_time = None
baseline_samples_per_node = {}
csv_queue = queue.Queue()
running = True
writer_running = True
samples_received = 0
frames_completed = 0
current_timestamp = 0.0
ser = None

csv_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_RAW = os.path.join(DATA_DIR, f"{csv_timestamp}_raw_realtime_cap_data.csv")
CSV_PF = os.path.join(DATA_DIR, f"{csv_timestamp}_realtime_cap_data_pF.csv")


def handle_exit(sig, frame):
    global running, writer_running
    print("\nStopping...")
    running = False
    writer_running = False
    if ser:
        ser.close()


signal.signal(signal.SIGINT, handle_exit)


def find_arduino_port():
    import serial.tools.list_ports
    import glob
    
    patterns = ["/dev/cu.usbserial-*", "/dev/cu.usbmodem*", 
                "/dev/cu.wchusbserial*", "/dev/cu.SLAB_USBtoUART*"]
    
    for pattern in patterns:
        ports = glob.glob(pattern)
        if ports:
            for port in sorted(ports):
                if "usbserial" in port or "usbmodem" in port:
                    return port
    
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.device.startswith("/dev/cu.") and ("usb" in port.device.lower() or "serial" in port.description.lower()):
            return port.device
    
    return None


def compute_median(values):
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2.0
    return sorted_values[n // 2]


def initialize_baseline_collection():
    global baseline_start_time, baseline_samples_per_node, baseline_ready
    baseline_start_time = time.time()
    baseline_samples_per_node = {}
    baseline_ready = False
    print(f"Collecting baseline for {BASELINE_TIME_SEC} seconds...")


def collect_baseline_sample(row, col, cap_value):
    global baseline_c0, baseline_ready, baseline_start_time, baseline_samples_per_node
    
    if baseline_start_time is None:
        initialize_baseline_collection()
    
    elapsed_time = time.time() - baseline_start_time
    
    if elapsed_time < BASELINE_TIME_SEC:
        node_key = (row, col)
        if node_key not in baseline_samples_per_node:
            baseline_samples_per_node[node_key] = []
        baseline_samples_per_node[node_key].append(cap_value)
        return False
    
    if not baseline_ready:
        print("Calculating baseline medians...")
        
        for r in range(NUM_ROWS):
            for c in range(NUM_COLS):
                node_key = (r, c)
                if node_key in baseline_samples_per_node and len(baseline_samples_per_node[node_key]) > 0:
                    baseline_c0[node_key] = compute_median(baseline_samples_per_node[node_key])
                    if DEBUG_MODE and len(baseline_samples_per_node[node_key]) > 0:
                        samples = baseline_samples_per_node[node_key]
                        print(f"  Node ({r},{c}): baseline={baseline_c0[node_key]:.3f} pF (from {len(samples)} samples, range: {min(samples):.3f}-{max(samples):.3f} pF)")
                else:
                    baseline_c0[node_key] = 0.0
        
        baseline_ready = True
        baseline_samples_per_node = {}
        print("Baseline established. Starting visualization...")
        if DEBUG_MODE:
            baseline_values = [v for v in baseline_c0.values() if v > 0]
            if baseline_values:
                print(f"  Baseline summary: min={min(baseline_values):.3f} pF, max={max(baseline_values):.3f} pF, mean={np.mean(baseline_values):.3f} pF")
    
    return baseline_ready


def compute_delta_c_normalized(frame_grid):
    """Compute delta_C/C_0 = (C - C_0) / C_0 for each node using its own median baseline."""
    delta_grid = np.zeros((NUM_ROWS, NUM_COLS))
    
    if not baseline_ready or len(baseline_c0) == 0:
        return delta_grid
    
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


def frame_to_grid(frame_data):
    grid = np.zeros((NUM_ROWS, NUM_COLS))
    for (r, c), cap_value in frame_data.items():
        if 0 <= r < NUM_ROWS and 0 <= c < NUM_COLS:
            grid[r, c] = cap_value
    return grid


def extract_active_nodes_region(delta_grid):
    """Extract only the 2x2 region containing the 4 active nodes."""
    active_rows = sorted(set(r for r, c in ACTIVE_NODES))
    active_cols = sorted(set(c for r, c in ACTIVE_NODES))
    
    # Extract the 2x2 region
    active_region = np.zeros((len(active_rows), len(active_cols)))
    for i, r in enumerate(active_rows):
        for j, c in enumerate(active_cols):
            if 0 <= r < NUM_ROWS and 0 <= c < NUM_COLS:
                active_region[i, j] = delta_grid[r, c]
    
    return active_region, active_rows, active_cols


def interpolate_touch_grid(delta_grid, num_rows, num_cols):
    """
    Interpolate a grid to create smooth touch visualization.
    Similar to Multi-Touch Kit approach with bicubic interpolation.
    """
    # Add padding around grid for better edge interpolation
    PAD = 1
    padded = np.zeros((num_rows + 2*PAD, num_cols + 2*PAD))
    padded[PAD:PAD+num_rows, PAD:PAD+num_cols] = delta_grid
    
    # Interpolate using bicubic (order=3) for smooth touch visualization
    interp_grid = zoom(padded, (INTERP_SCALE, INTERP_SCALE), order=3)
    
    return interp_grid


def csv_writer_thread_func():
    global writer_running
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    raw_file = open(CSV_RAW, "w", newline="")
    pf_file = open(CSV_PF, "w", newline="")
    raw_writer = csv.writer(raw_file)
    pf_writer = csv.writer(pf_file)
    
    raw_writer.writerow(["timestamp", "row_index", "col_index", "capacitance_pF"])
    pf_writer.writerow(["timestamp", "row_index", "col_index", "capacitance_pF"])
    
    while writer_running or not csv_queue.empty():
        try:
            sample = csv_queue.get(timeout=0.1)
            timestamp, r_idx, c_idx, cap_pf = sample
            raw_writer.writerow([timestamp, r_idx, c_idx, cap_pf])
            pf_writer.writerow([timestamp, r_idx, c_idx, cap_pf])
            raw_file.flush()
            pf_file.flush()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"CSV write error: {e}")
            continue
    
    raw_file.close()
    pf_file.close()
    print(f"\nData saved to {CSV_RAW} and {CSV_PF}")


def reader_thread_func():
    global samples_received, frames_completed, current_timestamp, frame_buffer, ser
    
    port_to_use = PORT
    if AUTO_DETECT_PORT:
        detected_port = find_arduino_port()
        if detected_port:
            port_to_use = detected_port
    
    try:
        ser = serial.Serial(port_to_use, BAUD, timeout=0.01)
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print(f"Connected to {port_to_use}")
        print("=" * 60)
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        return

    start_time = time.time()
    last_frame_time = start_time

    while running:
        try:
            raw_line = ser.readline()
            if not raw_line:
                continue
            
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            line_upper = line.upper()
            if any(skip in line_upper for skip in ["FDC", "READY", "FAIL", "TIMESTAMP", "ROW_INDEX", "COLUMN_INDEX", "RAW_CAPACITANCE", "SENSOR"]):
                continue

            parts = line.split(",")
            if len(parts) != 4:
                continue

            try:
                timestamp_ms = int(parts[0].strip())
                r_idx = int(parts[1].strip())
                c_idx = int(parts[2].strip())
                cap_pf = float(parts[3].strip())
                
                if r_idx < 0 or r_idx >= NUM_ROWS or c_idx < 0 or c_idx >= NUM_COLS:
                    continue
            except ValueError:
                continue
            
            collect_baseline_sample(r_idx, c_idx, cap_pf)
            
            with lock:
                current_timestamp = time.time() - start_time
                node_key = (r_idx, c_idx)
                
                # Store all nodes in buffer
                frame_buffer[node_key] = cap_pf
                
                # Complete frame when all 4 active nodes are received (much faster than waiting for 64)
                active_nodes_in_buffer = [k for k in ACTIVE_NODES if k in frame_buffer]
                if len(active_nodes_in_buffer) >= NUM_ACTIVE_NODES:
                    frames_completed += 1
                    completed_frame = {k: frame_buffer[k] for k in ACTIVE_NODES}
                    completed_frames.append((current_timestamp, completed_frame))
                    # Clear only active nodes from buffer to allow next frame
                    for k in list(ACTIVE_NODES):
                        if k in frame_buffer:
                            del frame_buffer[k]
                    last_frame_time = time.time()
            
            sample = [current_timestamp, r_idx, c_idx, cap_pf]
            try:
                csv_queue.put(sample, timeout=0.1)
            except queue.Full:
                pass
            
            samples_received += 1
        
        except Exception as e:
            print(f"Serial error: {e}")
            break


def setup_visualization():
    """Setup multi-touch style visualization similar to Multi-Touch Kit."""
    # Dark background style like multi-touch displays
    fig = plt.figure(figsize=(10, 10), facecolor='black')
    ax = fig.add_subplot(111, facecolor='black')
    
    # Extract active nodes region (2x2 grid)
    active_rows = sorted(set(r for r, c in ACTIVE_NODES))
    active_cols = sorted(set(c for r, c in ACTIVE_NODES))
    NUM_ACTIVE_ROWS = len(active_rows)
    NUM_ACTIVE_COLS = len(active_cols)
    
    # Initialize with empty interpolated grid for 2x2 region
    empty_grid_2x2 = np.zeros((NUM_ACTIVE_ROWS, NUM_ACTIVE_COLS))
    interp_grid = interpolate_touch_grid(empty_grid_2x2, NUM_ACTIVE_ROWS, NUM_ACTIVE_COLS)
    
    # Calculate extent to map interpolated grid to the 2x2 coordinate system
    # Map to the actual row/column indices (0-1 for rows, 0-1 for columns)
    PAD = 1
    col_min, col_max = min(active_cols), max(active_cols)
    row_min, row_max = min(active_rows), max(active_rows)
    
    # Extend slightly beyond for padding visualization
    xmin = col_min - 0.5
    xmax = col_max + 1.5
    ymin = row_min - 0.5
    ymax = row_max + 1.5
    
    # Use 'RdBu_r' colormap: red=positive change, blue=negative change
    # This is more intuitive for capacitance changes
    # Set extent to map pixel coordinates to grid coordinates for proper alignment
    im = ax.imshow(interp_grid, cmap="RdBu_r", aspect='equal', origin='lower',
                   interpolation='bilinear', vmin=-DELTA_C_MAX, vmax=DELTA_C_MAX,
                   extent=[xmin, xmax, ymin, ymax])
    
    # Set axis limits to show only the 2x2 active nodes region
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    
    # Add grid overlay only for active nodes region
    ax.set_xticks(active_cols)
    ax.set_yticks(active_rows)
    ax.grid(True, color='white', linestyle='--', alpha=0.2, linewidth=0.5)
    ax.set_xticklabels([f"C{c}" for c in active_cols], color='white', fontsize=10)
    ax.set_yticklabels([f"R{r}" for r in active_rows], color='white', fontsize=10)
    
    # Create meshgrid based on row and column indices of active nodes
    from matplotlib.patches import Circle
    node_circles = []
    
    # Extract unique row and column indices from active nodes
    active_rows = sorted(set(r for r, c in ACTIVE_NODES))
    active_cols = sorted(set(c for r, c in ACTIVE_NODES))
    
    # Create meshgrid for the active nodes (row_grid, col_grid represent intersection points)
    row_grid, col_grid = np.meshgrid(active_rows, active_cols, indexing='ij')
    
    # Draw connecting lines to visualize the meshgrid structure
    # Draw horizontal lines (rows)
    for r in active_rows:
        if len(active_cols) > 1:
            ax.plot([min(active_cols), max(active_cols)], [r, r], 
                   'w--', alpha=0.2, linewidth=1.0)
    
    # Draw vertical lines (columns)
    for c in active_cols:
        if len(active_rows) > 1:
            ax.plot([c, c], [min(active_rows), max(active_rows)], 
                   'w--', alpha=0.2, linewidth=1.0)
    
    # Draw circles at each intersection point of the meshgrid
    for i, r in enumerate(active_rows):
        for j, c in enumerate(active_cols):
            # Verify this is an active node (should always be true, but check anyway)
            if (r, c) in ACTIVE_NODES:
                # Get the meshgrid intersection coordinates
                mesh_r = row_grid[i, j]
                mesh_c = col_grid[i, j]
                
                # Draw a circle at the meshgrid intersection point
                # Coordinates: (x, y) where x=column, y=row
                # Base radius matches the interpolated blur area (slightly larger than node spacing)
                base_radius = 0.5  # Matches typical blur spread from interpolation
                circle = Circle((mesh_c, mesh_r), radius=base_radius, 
                               fill=True, facecolor='cyan', edgecolor='white', 
                               linewidth=2.0, alpha=0.2)
                ax.add_patch(circle)
                node_circles.append((circle, (r, c), base_radius))  # Store circle with base radius
    
    # Title with white text on dark background
    ax.set_title("Multi-Touch Capacitance Sensor", 
                fontsize=16, fontweight='bold', color='white', pad=20)
    
    # Colorbar with white label
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Touch Intensity (ΔC/C₀)", rotation=270, labelpad=20, color='white')
    cbar.ax.yaxis.set_tick_params(color='white')
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
    
    # Stats text with white background
    stats_text = ax.text(0.02, 0.98, "", transform=ax.transAxes, 
                        fontsize=10, verticalalignment='top', color='white',
                        bbox=dict(boxstyle='round', facecolor='black', alpha=0.7, edgecolor='white'))
    
    return fig, ax, im, stats_text, node_circles


def make_update_function(im, stats_text, node_circles):
    def update_visualization(frame):
        global completed_frames, frame_buffer, current_timestamp, baseline_ready, baseline_start_time
        
        with lock:
            if completed_frames:
                timestamp, frame_data = completed_frames[-1]
            elif frame_buffer:
                # Show partial frame if we have some active nodes (for faster response)
                active_nodes_in_buffer = {k: frame_buffer[k] for k in ACTIVE_NODES if k in frame_buffer}
                if len(active_nodes_in_buffer) > 0:
                    timestamp = current_timestamp
                    frame_data = active_nodes_in_buffer.copy()
                    # Fill missing active nodes with last known values or 0
                    for node_key in ACTIVE_NODES:
                        if node_key not in frame_data:
                            frame_data[node_key] = frame_buffer.get(node_key, 0.0)
                else:
                    # Return circles even when no data available for consistency
                    circle_objects = [circle for circle, _, _ in node_circles]
                    return [im, stats_text] + circle_objects
            else:
                # Return circles even when no data available for consistency
                circle_objects = [circle for circle, _, _ in node_circles]
                return [im, stats_text] + circle_objects
        
        grid = frame_to_grid(frame_data)
        
        if not baseline_ready:
            # Use 2x2 empty grid for active nodes region
            active_rows = sorted(set(r for r, c in ACTIVE_NODES))
            active_cols = sorted(set(c for r, c in ACTIVE_NODES))
            empty_grid_2x2 = np.zeros((len(active_rows), len(active_cols)))
            empty_interp = interpolate_touch_grid(empty_grid_2x2, len(active_rows), len(active_cols))
            im.set_data(empty_interp)
            
            if baseline_start_time is not None:
                elapsed = time.time() - baseline_start_time
                remaining = max(0, BASELINE_TIME_SEC - elapsed)
                progress_pct = min(100, (elapsed / BASELINE_TIME_SEC) * 100)
                stats_str = (f"Calibrating baseline...\n"
                            f"Time: {elapsed:.1f}s / {BASELINE_TIME_SEC}s ({progress_pct:.0f}%)\n"
                            f"Remaining: {remaining:.1f}s\n"
                            f"Keep sensor stable")
            else:
                stats_str = "Initializing..."
            stats_text.set_text(stats_str)
            # Reset circles to default appearance during calibration
            for circle, (r, c), base_radius in node_circles:
                circle.set_facecolor('cyan')
                circle.set_edgecolor('white')
                circle.set_alpha(0.2)
                circle.set_linewidth(2.0)
                circle.set_radius(base_radius)  # Reset to base radius
            circle_objects = [circle for circle, _, _ in node_circles]
            return [im, stats_text] + circle_objects
        
        # Compute delta C/C₀ and interpolate for smooth visualization
        delta_grid = compute_delta_c_normalized(grid)
        
        # Extract only the 2x2 region containing active nodes
        active_region, active_rows, active_cols = extract_active_nodes_region(delta_grid)
        
        # Debug: Print values specifically for active 4 nodes
        if DEBUG_MODE and frames_completed % 5 == 0:  # Every 5 frames
            print(f"\n  Frame {frames_completed} - Active nodes:")
            for node_key in ACTIVE_NODES:
                r, c = node_key
                if r < NUM_ROWS and c < NUM_COLS:
                    current_val = grid[r, c]
                    baseline_val = baseline_c0.get(node_key, 0)
                    delta_val = delta_grid[r, c]
                    delta_c_abs = abs(current_val - baseline_val) if baseline_val > 0 else 0
                    status = "✓" if abs(delta_val) > TOUCH_THRESHOLD else " "
                    print(f"    {status} Node ({r},{c}): C={current_val:.3f}pF, C0={baseline_val:.3f}pF, "
                          f"ΔC={delta_c_abs:+.3f}pF, ΔC/C={delta_val:+.4f} ({delta_val*100:+.2f}%)")
        
        # Apply threshold - only show changes above threshold for active nodes
        active_region_clipped = np.zeros_like(active_region)
        for i, r in enumerate(active_rows):
            for j, c in enumerate(active_cols):
                if (r, c) in ACTIVE_NODES:
                    delta_val = delta_grid[r, c]
                    # Show all changes above threshold
                    if abs(delta_val) > TOUCH_THRESHOLD:
                        active_region_clipped[i, j] = delta_val
        
        # Interpolate for smooth touch visualization (2x2 region only)
        interp_grid = interpolate_touch_grid(active_region_clipped, len(active_rows), len(active_cols))
        
        # Update visualization - show absolute values with sign preserved in color
        im.set_data(interp_grid)
        
        # Use dynamic color range based on actual data range for better visibility
        max_abs_in_grid = np.max(np.abs(active_region_clipped))
        if max_abs_in_grid > 0:
            # Scale colorbar to actual data range with margin (but don't go below minimum visible range)
            # Ensure at least 0.0002 range for visibility, or 1.5x the actual max
            min_range = 0.0002  # Minimum visible range based on observed data
            color_range = max(min_range, max_abs_in_grid * 1.5)
            # But don't exceed DELTA_C_MAX
            color_range = min(color_range, DELTA_C_MAX)
            im.set_clim(vmin=-color_range, vmax=color_range)
        else:
            # Default to a small range that makes noise visible
            color_range = DELTA_C_MAX
            im.set_clim(vmin=-DELTA_C_MAX, vmax=DELTA_C_MAX)
        
        # Count active touches specifically for the 4 nodes
        active_touches = sum(1 for node in ACTIVE_NODES 
                           if abs(delta_grid[node[0], node[1]]) > TOUCH_THRESHOLD)
        
        # Find max changes in active nodes
        active_node_deltas = [delta_grid[r, c] for r, c in ACTIVE_NODES if r < NUM_ROWS and c < NUM_COLS]
        max_touch_abs = max([abs(d) for d in active_node_deltas]) if active_node_deltas else 0
        max_touch_pos = max([d for d in active_node_deltas if d > TOUCH_THRESHOLD], default=0)
        max_touch_neg = min([d for d in active_node_deltas if d < -TOUCH_THRESHOLD], default=0)
        
        stats_str = (f"Time: {timestamp:.2f}s\n"
                    f"Active Nodes: {len(ACTIVE_NODES)}\n"
                    f"Touches: {active_touches}/{len(ACTIVE_NODES)}")
        
        if max_touch_abs > TOUCH_THRESHOLD:
            stats_str += f"\nMax |ΔC/C|: {max_touch_abs:.4f}"
            if max_touch_pos > TOUCH_THRESHOLD:
                stats_str += f"\nMax +: {max_touch_pos:.4f}"
            if max_touch_neg < -TOUCH_THRESHOLD:
                stats_str += f"\nMax -: {max_touch_neg:.4f}"
        
        if frames_completed > 0 and timestamp > 0:
            frame_rate = frames_completed / timestamp
            stats_str += f"\nRate: {frame_rate:.2f} Hz"
        
        # Show active node values in debug mode
        if DEBUG_MODE:
            stats_str += f"\n--- Active Nodes ---"
            for r, c in ACTIVE_NODES:
                if r < NUM_ROWS and c < NUM_COLS:
                    current_val = grid[r, c]
                    baseline_val = baseline_c0.get((r, c), 0)
                    delta_val = delta_grid[r, c]
                    if abs(delta_val) > TOUCH_THRESHOLD:
                        stats_str += f"\n({r},{c}): {current_val:.2f}pF (Δ={delta_val*100:+.2f}%)"
        
        stats_text.set_text(stats_str)
        
        # Update circle colors and sizes based on touch intensity to match blur area
        for circle, (r, c), base_radius in node_circles:
            if r < NUM_ROWS and c < NUM_COLS:
                delta_val = delta_grid[r, c]
                abs_delta = abs(delta_val)
                
                if abs_delta > TOUCH_THRESHOLD:
                    # Normalize delta value to [0, 1] for colormap
                    # Use the same color range as the main visualization
                    vmin = -color_range
                    vmax = color_range
                    normalized = np.clip((delta_val - vmin) / (vmax - vmin), 0, 1)
                    
                    # Get color from RdBu_r colormap (red=positive, blue=negative)
                    cmap = plt.get_cmap('RdBu_r')
                    circle_color = cmap(normalized)
                    circle.set_facecolor(circle_color)
                    circle.set_alpha(0.7)  # More visible when touched
                    circle.set_linewidth(2.5)  # Thicker edge when active
                    
                    # Scale circle radius to match blur area based on touch intensity
                    # Stronger touches create larger blur (scale from 1.0x to 1.5x base radius)
                    intensity_scale = 1.0 + (normalized * 0.5)  # Scale from 1.0 to 1.5
                    circle.set_radius(base_radius * intensity_scale)
                else:
                    # Default appearance when not touched
                    circle.set_facecolor('cyan')
                    circle.set_edgecolor('white')
                    circle.set_alpha(0.2)  # Subtle when not active
                    circle.set_linewidth(2.0)
                    circle.set_radius(base_radius)  # Reset to base radius
        
        # Return all animated objects
        circle_objects = [circle for circle, _, _ in node_circles]
        return [im, stats_text] + circle_objects
    
    return update_visualization


def main():
    global running, writer_running
    
    csv_writer_thread = threading.Thread(target=csv_writer_thread_func, daemon=False)
    csv_writer_thread.start()
    
    reader_thread = threading.Thread(target=reader_thread_func, daemon=True)
    reader_thread.start()
    
    time.sleep(0.5)
    
    fig, ax, im, stats_text, node_circles = setup_visualization()
    update_func = make_update_function(im, stats_text, node_circles)
    ani = FuncAnimation(fig, update_func, interval=33, blit=False, cache_frame_data=False)  # ~30 FPS for faster updates
    
    plt.tight_layout()
    plt.show()
    
    running = False
    writer_running = False
    
    csv_writer_thread.join(timeout=5.0)
    if ser:
        ser.close()
    
    print("\nVisualization stopped.")


if __name__ == "__main__":
    main()
