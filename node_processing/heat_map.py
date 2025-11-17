import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from scipy.ndimage import zoom

INPUT_CSV = "grid_output.csv"
OUTPUT_VIDEO = "heatmap_video.mp4"

# interpolation factor (how smooth)
INTERP_SCALE = 20   # 20x upsampling

def main():
    df = pd.read_csv(INPUT_CSV)

    # Determine grid size from columns named aXY
    grid_cols = [c for c in df.columns if c.startswith("a")]
    indices = [(int(c[1]), int(c[2])) for c in grid_cols]  # aRC → (R,C)
    max_r = max(r for r, c in indices)
    max_c = max(c for r, c in indices)

    # Sort columns row-major order
    grid_cols_sorted = sorted(grid_cols, key=lambda x: (int(x[1]), int(x[2])))

    # Extract grid frames
    frames = []
    for _, row in df.iterrows():
        grid = row[grid_cols_sorted].values.reshape(max_r, max_c)
        frames.append(grid)

    frames = np.array(frames)

    # Interpolate using scipy.ndimage.zoom
    interp_frames = []
    for grid in frames:
        interp = zoom(grid, (INTERP_SCALE, INTERP_SCALE), order=3)  # bicubic
        interp_frames.append(interp)

    interp_frames = np.array(interp_frames)

    # Global color limits for stable colors
    vmin = np.min(interp_frames)
    vmax = np.max(interp_frames)

    # Plot setup
    fig, ax = plt.subplots(figsize=(6, 6))
    heatmap = ax.imshow(interp_frames[0], cmap="inferno", vmin=vmin, vmax=vmax)
    plt.colorbar(heatmap)
    ax.set_title("Heatmap Over Time")

    writer = FFMpegWriter(fps=20)

    print("Rendering video...")

    with writer.saving(fig, OUTPUT_VIDEO, dpi=150):
        for frame in interp_frames:
            heatmap.set_data(frame)
            writer.grab_frame()

    print(f"Saved → {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
