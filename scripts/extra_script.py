"""
PlatformIO extra script to add custom tasks.
This adds custom tasks like 'plotter' and 'monitor_plot' to PlatformIO.
"""

Import("env")

# Custom target: Live serial plotter
def plotter_target(source, target, env):
    """Launch live serial plotter for debugging."""
    import subprocess
    import sys
    
    # Get serial port from environment or use default
    port = env.get("UPLOAD_PORT") or "/dev/cu.usbserial-210"
    
    print(f"[INFO] Launching serial plotter on {port}...")
    
    try:
        # Run the serial plotter script
        subprocess.run([
            sys.executable,
            "scripts/serial_plotter.py",
            "--port", port,
            "--baud", "115200"
        ])
    except KeyboardInterrupt:
        print("\n[INFO] Plotter stopped")
    except Exception as e:
        print(f"[ERROR] Failed to launch plotter: {e}")

# Custom target: Monitor with plotter option
def monitor_plot_target(source, target, env):
    """Monitor serial output and optionally launch plotter."""
    import subprocess
    import sys
    
    port = env.get("UPLOAD_PORT") or "/dev/cu.usbserial-210"
    
    print("[INFO] Starting serial monitor with plotting option...")
    print("[INFO] Press 'p' to open plotter, CTRL+C to exit")
    
    # For now, just launch the plotter directly
    # In a more advanced version, this could be interactive
    plotter_target(source, target, env)

# Register custom targets
env.AddCustomTarget(
    "plotter",
    None,
    plotter_target,
    title="Serial Plotter",
    description="Launch live serial data plotter for debugging"
)

env.AddCustomTarget(
    "monitor_plot",
    None,
    monitor_plot_target,
    title="Monitor + Plot",
    description="Monitor serial output with plotting option"
)

print("[INFO] Custom targets registered: 'plotter', 'monitor_plot'")

