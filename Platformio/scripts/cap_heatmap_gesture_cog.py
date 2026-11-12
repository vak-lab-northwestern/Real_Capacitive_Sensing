#!/usr/bin/env python3
"""
Capacitive-textile heatmap (text serial input only, always 115200 baud).

SERIAL INPUT (one cell per line, newline terminated), e.g.  3,6,511238
    row,col,value
    value = INTEGER in milli-pF  ->  511238 means 511.238 pF
    Lines that don't match (debug prints, blank lines, '#' comments) are ignored.

HOW ROWS / COLUMNS ARE MAPPED ON SCREEN
    The ORIGIN (0,0) IS THE BOTTOM-LEFT cell. Rows count UP, columns count RIGHT.
    The TOP-RIGHT cell is (rows-1, cols-1), e.g. (7,7) on an 8x8 grid.

        row 7 | (7,0) (7,1) ... (7,7)   <- top row
        row 6 | (6,0) (6,1) ... (6,7)
         ...  |  ...
        row 1 | (1,0) (1,1) ... (1,7)
        row 0 | (0,0) (0,1) ... (0,7)   <- bottom row
              +------------------------
                col0  col1  ...  col7
                (left)         (right)

    The firmware's "r,c" go straight into data[r][c]; there is no flipping of any
    kind other than drawing row 0 at the bottom (imshow origin="lower").

GRID SIZE
    Type a number into the "Rows" / "Cols" boxes at the top of the window and press
    Enter. The grid redraws immediately and recalibration restarts.
    (--rows / --cols only set the starting values.)

COLORS
    First --calib-seconds: learns each cell's resting capacitance (don't touch!).
    After that a cell stays CREAM until its capacitance rises above its own baseline;
    the bigger the rise, the hotter the color (cream -> yellow -> orange -> red).
    Every cell always prints its raw capacitance in pF, rounded to a whole number.

    python cap_heatmap.py --port /dev/cu.usbserial-0001
    python cap_heatmap.py --port /dev/cu.usbserial-0001 --rows 8 --cols 8 --full-scale 2

SWIPE GESTURES (optional, OFF unless one of these flags is given)
    --gesture-four    recognise UP / DOWN / LEFT / RIGHT swipes
    --gesture-eight   same, plus the four diagonals
    Directions are relative to the DISPLAYED grid: UP = toward higher row numbers
    (top of the screen), RIGHT = toward higher column numbers.
    Method: the "center of gravity" of the whole grid (change-weighted, so big touch areas
    and noisy sensors work well) is tracked while the total change is above a threshold;
    its net direction of travel is the swipe.
    A small arrow icon replaces the Rows / Cols boxes at the top of the window and
    holds for --gesture-hold seconds. (Grid size is then set with --rows / --cols only.)

    python cap_heatmap_gesture.py --port /dev/cu.usbserial-0001 --gesture-four
    python cap_heatmap_gesture.py --port /dev/cu.usbserial-0001 --gesture-eight

Press  r  in the plot window to recalibrate (not while typing in a box).
"""
import argparse
import math
import re
import time
import warnings
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
import serial
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.widgets import TextBox

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ----------------------------------------------------------------------------
# Fixed settings
# ----------------------------------------------------------------------------
BAUD = 115200            # always 115200 (must match Serial.begin() in the firmware)
UNIT = 1000.0            # serial integers are counts of 1/1000 pF (milli-pF)
MAX_DIM = 64             # largest rows/cols you can type into the boxes

# "row,col,value"  e.g. "3,6,511238"  -> groups: row, col, value
LINE = re.compile(r"^\s*(\d+)\s*,\s*(\d+)\s*,\s*(-?\d+)\s*$")

PURPLE = "#4E2A84"       # window background
CREAM = "#FFF3D6"        # resting color of every cell
FG, FG_DIM = "white", "#D8CCEB"
TITLE = "Two Layer Knitted Textile: Capacitive Sensing"
CMAP = LinearSegmentedColormap.from_list(
    "cream_hot", [CREAM, "#FFE08A", "#FFC94D", "#FF8C1A", "#E8281E", "#7A0000"])


def parse_line(line):
    """Parse one serial line. Returns (row, col, pF) or None if it isn't a data line.
    No range check here: the caller decides whether (row, col) fits the current grid."""
    m = LINE.match(line)
    if not m:
        return None
    row, col, raw = int(m[1]), int(m[2]), int(m[3])
    return row, col, raw / UNIT          # milli-pF -> pF


# Swipe direction names, indexed by angle / 45 degrees (0 = RIGHT, counter-clockwise).
DIR8 = ["RIGHT", "UP-RIGHT", "UP", "UP-LEFT", "LEFT", "DOWN-LEFT", "DOWN", "DOWN-RIGHT"]


class SwipeDetector:
    """Recognises swipes from the motion of the grid's "center of gravity".

    Every call to update() gets the current "change from baseline" grid (pF). The WHOLE
    grid is used, weighted by how much each cell changed (no per-cell cutoff), so a big
    noisy touch patch contributes all of its area and the stray noise cells add ~nothing:

        mass = sum(change)                        total touch strength
        COG  = (sum(change * col) / mass,         x = column (right is +)
                sum(change * row) / mass)         y = row    (up is +, row 0 at the bottom)

    A touch is ACTIVE while `mass` is above `threshold` (with hysteresis: once active it
    stays active until mass falls below half the threshold). While active, the COG path is
    stored in a rolling history. When the touch has ended for `release` seconds the stroke
    is judged: weak samples at touch-down/lift-off are dropped, a straight line is
    least-squares fitted through the rest of the COG path (this averages out jitter),
    its net displacement gives the direction, and if the COG travelled at
    least `min_travel` cells the direction is snapped to the nearest 4 or 8 compass points.
    """

    def __init__(self, eight, threshold, min_travel, history, release):
        self.eight, self.threshold, self.min_travel = eight, threshold, min_travel
        self.history, self.release = history, release
        self.hist = deque()                  # (time, cog_x, cog_y, mass)
        self.last_touch = 0.0
        self.active = False
        self._idx = None                     # cached (ys, xs) index grids

    def reset(self):
        self.hist.clear()
        self.active = False

    def update(self, t, change):
        """Feed one grid. Returns (name, (ux, uy)) when a swipe just finished, else None."""
        if self._idx is None or self._idx[0].shape != change.shape:
            self._idx = np.indices(change.shape)
        ys, xs = self._idx
        mass = float(change.sum())
        # Hysteresis: need `threshold` to start, only half of it to stay on.
        if mass > self.threshold * (0.5 if self.active else 1.0):
            self.active = True
            self.hist.append((t, float((change * xs).sum() / mass),
                              float((change * ys).sum() / mass), mass))
            self.last_touch = t
            while t - self.hist[0][0] > self.history:        # keep only the recent past
                self.hist.popleft()
            return None
        if self.hist and t - self.last_touch >= self.release:   # touch over: judge the stroke
            pts = np.array(self.hist)
            self.hist.clear()
            self.active = False
            return self._classify(pts)
        return None

    def _classify(self, pts):
        # Drop the weak touch-down / lift-off samples (< 25% of peak strength): there the
        # COG is dominated by noise and by the smoothing filter's decay, not by the finger.
        pts = pts[pts[:, 3] >= 0.25 * pts[:, 3].max()]
        if len(pts) < 3:
            return None                                      # too brief: a tap, not a swipe
        t = pts[:, 0] - pts[0, 0]
        span = t[-1]
        if span <= 0:
            return None
        # Net COG displacement = slope of a least-squares line through the path x span,
        # with stronger (more reliable) samples counting for more.
        w = np.sqrt(pts[:, 3])
        dx = np.polyfit(t, pts[:, 1], 1, w=w)[0] * span
        dy = np.polyfit(t, pts[:, 2], 1, w=w)[0] * span
        if math.hypot(dx, dy) < self.min_travel:
            return None                                      # COG barely moved: ignore
        ang = math.degrees(math.atan2(dy, dx)) % 360         # 0 = right, 90 = up
        idx = int(round(ang / 45.0)) % 8 if self.eight else (int(round(ang / 90.0)) % 4) * 2
        rad = math.radians(idx * 45)
        return DIR8[idx], (math.cos(rad), math.sin(rad))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="serial port, e.g. /dev/cu.usbserial-0001")
    p.add_argument("--rows", type=int, default=8, help="starting number of rows (editable in window)")
    p.add_argument("--cols", type=int, default=8, help="starting number of columns (editable in window)")
    p.add_argument("--max-fps", type=float, default=30.0, help="cap on screen redraws per second")
    p.add_argument("--calib-seconds", type=float, default=4.0,
                   help="seconds spent learning each cell's resting value")
    # --- sensitivity knobs ---
    p.add_argument("--full-scale", type=float, default=5.0,
                   help="change (pF) that shows as full dark red. LOWER = MORE SENSITIVE")
    p.add_argument("--gamma", type=float, default=0.5,
                   help="color curve; below 1 boosts small changes (0.5 = sqrt), 1 = linear")
    p.add_argument("--sigma", type=float, default=2.5,
                   help="ignore changes under this many noise std-devs per cell. Lower = more sensitive")
    p.add_argument("--deadband", type=float, default=0.1,
                   help="also ignore changes under this many pF (keeps rest state cream)")
    p.add_argument("--avg", type=int, default=3,
                   help="smooth each cell over ~N readings to cut jitter (1 = off)")
    p.add_argument("--direction", choices=["both", "up", "down"], default="up",
                   help="which capacitance change counts as heat: up (default), down, or both")
    p.add_argument("--smooth", action="store_true", help="smooth gradient instead of squares")
    p.add_argument("--font-size", type=float, default=None,
                   help="fixed size for the pF numbers (default: scales with the window)")
    p.add_argument("--no-labels", action="store_true", help="hide the raw pF value in each cell")
    # --- swipe gestures (off unless one of the two flags is given) ---
    g = p.add_mutually_exclusive_group()
    g.add_argument("--gesture-four", action="store_true",
                   help="detect UP/DOWN/LEFT/RIGHT swipes and show an arrow at the top")
    g.add_argument("--gesture-eight", action="store_true",
                   help="detect the 4 cardinal swipes plus the 4 diagonals")
    p.add_argument("--gesture-threshold", type=float, default=1.0,
                   help="total change over the whole grid (pF, after sigma/deadband) that "
                        "counts as a touch; the center of gravity is tracked while above it")
    p.add_argument("--gesture-min-travel", type=float, default=1.5,
                   help="cells the center of gravity must move to count as a swipe")
    p.add_argument("--gesture-history", type=float, default=1.0,
                   help="seconds of center-of-gravity history kept for judging a swipe")
    p.add_argument("--gesture-release", type=float, default=0.15,
                   help="seconds without touch before a swipe is judged finished")
    p.add_argument("--gesture-hold", type=float, default=1.5,
                   help="seconds the arrow stays on screen")
    args = p.parse_args()

    gesture_mode = args.gesture_four or args.gesture_eight
    detector = (SwipeDetector(args.gesture_eight, args.gesture_threshold, args.gesture_min_travel,
                              args.gesture_history, args.gesture_release)
                if gesture_mode else None)

    # Current grid size. Changed live by the Rows / Cols text boxes.
    grid = {"rows": int(np.clip(args.rows, 1, MAX_DIM)),
            "cols": int(np.clip(args.cols, 1, MAX_DIM))}

    alpha = 1.0 / max(args.avg, 1)
    noise_factor = np.sqrt(alpha / (2 - alpha))     # noise reduction from the running average

    # ------------------------------------------------------------------------
    # Figure, heatmap image, colorbar
    # ------------------------------------------------------------------------
    norm = PowerNorm(gamma=args.gamma, vmin=0, vmax=args.full_scale, clip=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PURPLE)

    # origin="lower" is what puts row 0 at the BOTTOM and the last row at the TOP.
    # The image array is indexed [row, col], so cell (r, c) is drawn at x=c, y=r.
    im = ax.imshow(np.zeros((grid["rows"], grid["cols"])), cmap=CMAP, norm=norm,
                   interpolation="gaussian" if args.smooth else "nearest",
                   origin="lower")
    ax.set_xlabel("Column  (0 = left)", color=FG)
    ax.set_ylabel("Row  (0 = bottom)", color=FG)
    ax.tick_params(axis="both", which="major", colors=FG)
    for spine in ax.spines.values():
        spine.set_edgecolor(FG)
    if not args.smooth:                              # black grid lines between cells
        ax.grid(which="minor", color="black", linewidth=1)
        ax.tick_params(which="minor", length=0)
    fig.text(0.5, 0.975, TITLE, ha="center", va="top", color=FG, fontsize=15, fontweight="bold")

    cax = fig.add_axes([0.9, 0.2, 0.02, 0.6])        # positioned by layout()
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("Increase from baseline (pF)", color=FG)
    cbar.ax.tick_params(colors=FG)
    cbar.outline.set_edgecolor(FG)

    status = fig.text(0.015, 0.015, "", ha="left", va="bottom", fontsize=8, color=FG_DIM)
    metrics = fig.text(0.985, 0.015, "", ha="right", va="bottom", fontsize=8, color=FG_DIM)

    texts = []   # texts[r][c] is the number drawn in cell (r, c); rebuilt when grid size changes

    # ------------------------------------------------------------------------
    # Top strip: Rows / Cols input boxes normally; swipe arrow when gestures are on
    # ------------------------------------------------------------------------
    boxes = []
    if not gesture_mode:
        rows_box = TextBox(fig.add_axes([0.36, 0.885, 0.08, 0.04]), "Rows ",
                           initial=str(grid["rows"]), color="white", hovercolor="#F2EAFB")
        cols_box = TextBox(fig.add_axes([0.58, 0.885, 0.08, 0.04]), "Cols ",
                           initial=str(grid["cols"]), color="white", hovercolor="#F2EAFB")
        boxes = [rows_box, cols_box]
        for box in boxes:
            box.label.set_color(FG)
    else:
        ICON_H = 0.045                                   # icon height as a fraction of the window
        icon = fig.add_axes([0.48, 0.8825, 0.04, ICON_H])    # re-squared by layout()
        icon.set_xlim(-1.2, 1.2)
        icon.set_ylim(-1.2, 1.2)
        icon.axis("off")
        idle_dot, = icon.plot([0], [0], "o", color=FG_DIM, markersize=4)
        gest_label = fig.text(0.47, 0.905, f"Swipe ({'8' if args.gesture_eight else '4'}-way):",
                              ha="right", va="center", color=FG_DIM, fontsize=11)
        gest_name = fig.text(0.53, 0.905, "-", ha="left", va="center", color=FG_DIM,
                             fontsize=11, fontweight="bold")
        gest = {"arrow": None, "until": 0.0}

    def show_gesture(name, vec):
        """Draw an arrow pointing along vec (x right, y up) and name it."""
        clear_gesture()
        idle_dot.set_visible(False)
        v = np.array(vec) * 0.85
        gest["arrow"] = icon.annotate(
            "", xy=tuple(v), xytext=tuple(-v),
            arrowprops=dict(arrowstyle="-|>", color=FG, lw=3.5, mutation_scale=18,
                            shrinkA=0, shrinkB=0))
        gest_name.set_text(name)
        gest_name.set_color(FG)

    def clear_gesture():
        if gest["arrow"] is not None:
            gest["arrow"].remove()
            gest["arrow"] = None
        idle_dot.set_visible(True)
        gest_name.set_text("-")
        gest_name.set_color(FG_DIM)

    def layout(event=None):
        """Keep the grid centered at any window size; colorbar sits to its right."""
        W, H = fig.get_size_inches()
        side = min(0.68 * H, 0.72 * W)               # square area that holds the grid
        left, bottom = (W - side) / 2, (H - side) / 2 - 0.02 * H
        ax.set_position([left / W, bottom / H, side / W, side / H])
        cax.set_position([(left + side + 0.03 * W) / W, bottom / H, 0.02, side / H])
        if gesture_mode:                             # square icon, centred on the old box row
            iw = ICON_H * H / W
            icon.set_position([0.5 - iw / 2, 0.8825, iw, ICON_H])
            gest_label.set_x(0.5 - iw / 2 - 0.008)
            gest_name.set_x(0.5 + iw / 2 + 0.008)
        if texts and args.font_size is None:
            cell_in = side / max(grid["rows"], grid["cols"])    # one cell's size in inches
            fs = float(np.clip(0.25 * cell_in * 72, 4, 48))     # 72 points per inch
            for row in texts:
                for t in row:
                    t.set_fontsize(fs)

    fig.canvas.mpl_connect("resize_event", layout)

    # ------------------------------------------------------------------------
    # Per-cell state. Every array is shaped (rows, cols) and indexed [row, col].
    # ------------------------------------------------------------------------
    state = {}
    meta = {"max_r": -1, "max_c": -1}    # largest row/col index ever received (for the warning)

    def reset():
        """(Re)start calibration with empty arrays sized to the current grid."""
        shape = (grid["rows"], grid["cols"])
        nan = np.full(shape, np.nan)
        state.update(cur=nan.copy(),         # latest raw reading (pF)
                     ema=nan.copy(),         # running average of readings
                     n=np.zeros(shape),      # calibration sample count
                     sum=np.zeros(shape), sq=np.zeros(shape),
                     base=None, noise=None, t0=None)
        if detector is not None:
            detector.reset()
            clear_gesture()

    def calibration_done():
        if time.perf_counter() - state["t0"] < args.calib_seconds:
            return False
        seen = state["n"] > 0
        if not seen.any():
            return False
        return state["n"][seen].min() >= 2           # every cell that reports has 2+ samples

    def finish_calibration():
        n, seen = state["n"], state["n"] > 0
        base = np.where(seen, state["sum"] / np.maximum(n, 1), np.nan)
        var = np.where(seen, state["sq"] / np.maximum(n, 1) - base ** 2, 0.0)
        state["base"] = base                         # resting capacitance of each cell
        state["noise"] = np.sqrt(np.clip(np.nan_to_num(var), 0, None))
        state["ema"] = base.copy()

    def ingest(r, c, v):
        """Store one reading for the cell at row r, column c (0,0 = bottom-left)."""
        meta["max_r"], meta["max_c"] = max(meta["max_r"], r), max(meta["max_c"], c)
        if r >= grid["rows"] or c >= grid["cols"]:
            return                                   # outside current grid: ignore (status bar warns)
        if state["t0"] is None:
            state["t0"] = time.perf_counter()
        state["cur"][r, c] = v
        if state["base"] is None:                    # still calibrating: accumulate sums
            state["n"][r, c] += 1
            state["sum"][r, c] += v
            state["sq"][r, c] += v * v
            if calibration_done():
                finish_calibration()
        else:                                        # calibrated: running average of the cell
            e = state["ema"][r, c]
            state["ema"][r, c] = v if np.isnan(e) else e + alpha * (v - e)

    def handle(line):
        """Feed one serial line in. Returns True if it was a valid data line."""
        parsed = parse_line(line)
        if parsed is None:
            return False
        ingest(*parsed)
        return True

    def change_grid():
        """Heat per cell in pF (0 => cream). Only valid once calibration has finished."""
        d = state["ema"] - state["base"]             # change from resting value (pF)
        d = {"both": np.abs(d), "up": d, "down": -d}[args.direction]
        dead = np.maximum(args.sigma * state["noise"] * noise_factor, args.deadband)
        return np.nan_to_num(np.clip(d - dead, 0, None))

    def view():
        """Return (change_grid, status_text, raw_grid), all shaped (rows, cols)."""
        R, C = grid["rows"], grid["cols"]
        raw = state["cur"].copy()
        warn = ""
        if meta["max_r"] >= R or meta["max_c"] >= C:
            warn = (f"   |   data seen up to row {meta['max_r']}, col {meta['max_c']} "
                    f"- enlarge Rows/Cols")
        if state["base"] is None:
            t0 = state["t0"] or time.perf_counter()
            left = max(args.calib_seconds - (time.perf_counter() - t0), 0)
            msg = f"Calibrating... {left:.1f}s - don't touch the sensor"
            return np.zeros((R, C)), msg + warn, raw
        return change_grid(), "Press r to recalibrate" + warn, raw

    def draw(show, status_msg, raw, fps=None):
        im.set_data(show)
        for r, row in enumerate(texts):
            for c, t in enumerate(row):
                v = raw[r, c]
                t.set_text("" if np.isnan(v) else str(int(round(v))))   # whole pF
                t.set_color("white" if float(norm(show[r, c])) > 0.65 else "black")
        status.set_text(status_msg)
        metrics.set_text(f"display {fps:.0f} fps" if fps else "")

    def apply_grid():
        """Rebuild everything that depends on the grid size, then restart calibration."""
        R, C = grid["rows"], grid["cols"]
        im.set_data(np.zeros((R, C)))
        # Cell (r, c) is centered on x=c, y=r, so the edges sit at -0.5 and R/C - 0.5.
        im.set_extent((-0.5, C - 0.5, -0.5, R - 0.5))
        ax.set_xlim(-0.5, C - 0.5)
        ax.set_ylim(-0.5, R - 0.5)                   # low y at the bottom => row 0 at the bottom
        ax.set_xticks(range(C))                      # tick labels = column numbers
        ax.set_yticks(range(R))                      # tick labels = row numbers
        if not args.smooth:
            ax.set_xticks(np.arange(-0.5, C, 1), minor=True)
            ax.set_yticks(np.arange(-0.5, R, 1), minor=True)
        for row in texts:                            # throw away the old number labels
            for t in row:
                t.remove()
        texts.clear()
        if not args.no_labels:
            # One label per cell, placed at x=col, y=row (same mapping as the image).
            texts.extend([[ax.text(c, r, "", ha="center", va="center",
                                   fontsize=args.font_size or 11, fontweight="bold")
                           for c in range(C)] for r in range(R)])
        reset()
        layout()
        draw(*view())
        fig.canvas.draw_idle()

    def on_size_submit(_text=None):
        """Called when Enter is pressed (or focus leaves) in either box."""
        try:
            R, C = int(rows_box.text), int(cols_box.text)
        except ValueError:                           # junk typed: put the old numbers back
            rows_box.set_val(str(grid["rows"]))
            cols_box.set_val(str(grid["cols"]))
            return
        R, C = int(np.clip(R, 1, MAX_DIM)), int(np.clip(C, 1, MAX_DIM))
        rows_box.set_val(str(R))
        cols_box.set_val(str(C))
        if (R, C) != (grid["rows"], grid["cols"]):   # only rebuild if something changed
            grid["rows"], grid["cols"] = R, C
            apply_grid()

    for box in boxes:
        box.on_submit(on_size_submit)

    def on_key(event):
        # Don't treat the letter 'r' as "recalibrate" while typing in a box.
        if any(getattr(b, "capturekeystrokes", False) for b in boxes):
            return
        if event.key == "r":
            reset()

    fig.canvas.mpl_connect("key_press_event", on_key)

    apply_grid()                                     # initial build

    # ------------------------------------------------------------------------
    # Serial loop
    # ------------------------------------------------------------------------
    ser = serial.Serial(args.port, BAUD, timeout=0.05)
    ser.reset_input_buffer()
    plt.ion()
    plt.show(block=False)
    status.set_text("Waiting for data from the serial port...")
    print(f"Opened {args.port} at {BAUD} baud. Waiting for data... (Ctrl+C to quit)")

    buf = b""
    dirty = False
    fps, t_draw = 0.0, time.perf_counter()
    last_rx, last_warn = time.perf_counter(), 0.0
    t_gest = 0.0
    try:
        while plt.fignum_exists(fig.number):
            data = ser.read(max(ser.in_waiting, 1))
            now = time.perf_counter()
            if data:
                last_rx = now
                buf += data
            elif now - last_rx > 3 and now - last_warn > 3:
                print("No bytes received. Check: correct --port, firmware uploaded, "
                      "serial monitor closed.")
                last_warn = now

            if b"\n" in buf:
                *lines, buf = buf.split(b"\n")       # keep any partial last line in buf
                unparsed = None
                for raw_line in lines:               # ingest EVERY line, not just the newest
                    text = raw_line.decode(errors="ignore").strip()
                    if not text or text.startswith("#"):
                        continue
                    if handle(text):
                        dirty = True
                    else:
                        unparsed = text
                if unparsed is not None and now - last_warn > 2:
                    print(f"Ignored a line that isn't 'row,col,value': {unparsed[:150]!r}")
                    last_warn = now

            if detector is not None:
                # Sample the touch position up to ~50x/s (independent of the redraw rate).
                if data and state["base"] is not None and now - t_gest >= 0.02:
                    t_gest = now
                    hit = detector.update(now, change_grid())
                    if hit is not None:
                        show_gesture(*hit)
                        gest["until"] = now + args.gesture_hold
                        print(f"Swipe: {hit[0]}")
                        dirty = True
                if gest["until"] and now >= gest["until"]:
                    clear_gesture()
                    gest["until"] = 0.0
                    dirty = True

            if dirty and now - t_draw >= 1.0 / args.max_fps:
                dt = now - t_draw
                fps = 0.8 * fps + 0.2 / dt if fps else 1 / dt
                t_draw, dirty = now, False
                draw(*view(), fps=fps)
                plt.pause(0.001)
            elif not data:
                plt.pause(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()