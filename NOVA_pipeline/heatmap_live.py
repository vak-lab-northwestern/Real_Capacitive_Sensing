# heatmap_live.py

import matplotlib.pyplot as plt
from collections import deque
import numpy as np

# Config
MAP_HISTORY = 10  # For smoothing if you want, still capped and tiny

class HeatMap1x4:
    """
    1x4 heat map display.
    feed: pass 4 normalized values.
    render: updates 4 squares.
    """

    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(4, 1))
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_xlim(0, 4)
        self.ax.set_ylim(0, 1)

        # Create 4 squares
        self.squares = []
        for i in range(4):
            sq = plt.Rectangle((i, 0), 1, 1)
            self.ax.add_patch(sq)
            self.squares.append(sq)

        # Tiny capped histories for optional smoothing
        self.histories = [deque(maxlen=MAP_HISTORY) for _ in range(4)]

    def feed(self, norms):
        for i, val in enumerate(norms):
            if val < 0:
                val = 0
            if val > 1:
                val = 1
            self.histories[i].append(val)

    def render(self):
        # Just use the most recent value
        for i, h in enumerate(self.histories):
            intensity = h[-1] if h else 0.0
            self.squares[i].set_facecolor(intensity)  # ← cheap update only
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


hm = HeatMap1x4()
plt.ion()

for _ in range(1000):
    # Example feed loop for conceptual testing
    hm.feed(np.random.rand(4))
    hm.render()
    plt.pause(0.005)
