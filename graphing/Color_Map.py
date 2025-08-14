import pygame
import numpy as np
import matplotlib.pyplot as plt
from serial import Serial
import scipy.ndimage

# ==== SETTINGS ====
serialPort = "COM8"
baudrate = 115200
grid_rows, grid_cols = 2, 4     # Original sensor layout
target_rows, target_cols = 60, 60  # Heatmap resolution (higher = smoother)
width, height = 600, 600        # Window size

# ==== PYGAME INIT ====
pygame.init()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("FDC2214 Heatmap")

# ==== SERIAL INIT ====
ser = Serial(serialPort, baudrate=baudrate, timeout=1)

def read_sensor_values():
    """Read one line of comma-separated integers from serial."""
    try:
        line = ser.readline().decode().strip()
        if not line:
            return None
        values = list(map(int, line.split(",")))
        if len(values) != grid_rows * grid_cols:
            return None
        return np.array(values).reshape(grid_rows, grid_cols)
    except:
        return None

def make_heatmap_surface(data):
    """Interpolate the data and convert to a Pygame surface."""
    # Interpolate to target resolution
    zoom_factors = (target_rows / grid_rows, target_cols / grid_cols)
    smooth_data = scipy.ndimage.zoom(data, zoom_factors, order=3)

    # Normalize to [0, 1]
    normed = (smooth_data - smooth_data.min()) / (smooth_data.max() - smooth_data.min() + 1e-6)

    # Apply colormap
    cmap = plt.get_cmap('viridis')
    colors = (cmap(normed)[:, :, :3] * 255).astype(np.uint8)  # Drop alpha

    # Convert to Pygame surface
    surface = pygame.surfarray.make_surface(colors.swapaxes(0, 1))
    surface = pygame.transform.smoothscale(surface, (width, height))
    return surface

# ==== MAIN LOOP ====
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    sensor_data = read_sensor_values()
    if sensor_data is not None:
        heatmap_surface = make_heatmap_surface(sensor_data)
        screen.blit(heatmap_surface, (0, 0))
        pygame.display.flip()

pygame.quit()
ser.close()
