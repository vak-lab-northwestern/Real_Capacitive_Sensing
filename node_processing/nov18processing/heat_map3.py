import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from scipy.ndimage import zoom

# ============================
# CONFIG
# ============================
INPUT_CSV = "processed/11182025_nomux_Node64_CH0_CH1_test3_processed.csv"
OUTPUT_VIDEO = "videos/11182025_nomux_Node64_CH0_CH1_test3_video.mp4"

INTERP_SCALE = 20     # 8x8 → 160x160 (before padding)
FPS = 20

PAD = 1               # number of zero-value cells around the grid

VMIN = 0.0            # 0% change
VMAX = 0.02           # 2% = white-hot

# Highlighted node (1-based indexing)
HIGHLIGHT_ROW = 1     # choose 1–8
HIGHLIGHT_COL = 8     # choose 1–8


# ============================
# MAIN FUNCTION
# ============================

def main():
    df = pd.read_csv(INPUT_CSV)

    timestamps = df["timestamp"].values

    # -------------------------------
    # Extract grid columns a11..a88
    # -------------------------------
    grid_cols = [c for c in df.columns if c.startswith("a")]
    grid_cols_sorted = sorted(grid_cols, key=lambda x: (int(x[1]), int(x[2])))

    raw_frames = df[grid_cols_sorted].to_numpy()
    num_frames = len(raw_frames)

    max_r = max(int(c[1]) for c in grid_cols_sorted)
    max_c = max(int(c[2]) for c in grid_cols_sorted)

    raw_frames = raw_frames.reshape(num_frames, max_r, max_c)

    # -------------------------------
    # Add padding around the grid
    # -------------------------------
    padded_frames = []

    for frame in raw_frames:
        # Create padded array (8 + 2*PAD) × (8 + 2*PAD)
        padded = np.zeros((max_r + 2*PAD, max_c + 2*PAD))

        # Insert original 8×8 into center
        padded[PAD:PAD+max_r, PAD:PAD+max_c] = frame

        padded_frames.append(padded)

    padded_frames = np.array(padded_frames)

    # -------------------------------
    # Interpolate padded grid
    # -------------------------------

    interp_frames = np.array([
        zoom(f, (INTERP_SCALE, INTERP_SCALE), order=1)  # bilinear
        for f in padded_frames
    ])

    H, W = interp_frames[0].shape

    # -------------------------------
    # Compute highlight pixel coords
    # -------------------------------
    px = int((HIGHLIGHT_ROW - 1 + PAD + 0.5) * INTERP_SCALE)
    py = int((HIGHLIGHT_COL - 1 + PAD + 0.5) * INTERP_SCALE)

    # -------------------------------
    # Setup Matplotlib figure
    # -------------------------------
    fig, ax = plt.subplots(figsize=(6, 6))
    heatmap = ax.imshow(interp_frames[0], cmap="inferno", vmin=VMIN, vmax=VMAX)

    ax.set_xticks([])
    ax.set_yticks([])
    plt.colorbar(heatmap, fraction=0.046, pad=0.04)

    # ---------------------------
    # Timestamp at top of figure
    # ---------------------------
    time_text = fig.text(
        0.5, 0.98,
        f"t = {timestamps[0]:.2f}s",
        ha="center", va="top",
        fontsize=12,
        color="white"
    )


    # -------------------------------
    # Update function
    # -------------------------------
    def update(i):
        heatmap.set_data(interp_frames[i])
        time_text.set_text(f"t = {timestamps[i]:.2f}s")
        return (heatmap, time_text)

    # -------------------------------
    # Create animation w/ blitting
    # -------------------------------
    ani = FuncAnimation(
        fig,
        update,
        frames=num_frames,
        blit=True,
        interval=1000 / FPS
    )

    # -------------------------------
    # Save MP4
    # -------------------------------
    print("Saving video…")
    writer = FFMpegWriter(fps=FPS, codec="h264")
    ani.save(OUTPUT_VIDEO, writer=writer, dpi=150)
    print(f"Done → {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
