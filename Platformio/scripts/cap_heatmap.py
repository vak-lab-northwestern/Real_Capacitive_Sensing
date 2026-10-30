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

Press  r  in the plot window to recalibrate (not while typing in a box).
"""
import argparse
import re
import time
import warnings

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
    args = p.parse_args()

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
    # Rows / Cols input boxes (top of window)
    # ------------------------------------------------------------------------
    rows_box = TextBox(fig.add_axes([0.36, 0.885, 0.08, 0.04]), "Rows ",
                       initial=str(grid["rows"]), color="white", hovercolor="#F2EAFB")
    cols_box = TextBox(fig.add_axes([0.58, 0.885, 0.08, 0.04]), "Cols ",
                       initial=str(grid["cols"]), color="white", hovercolor="#F2EAFB")
    for box in (rows_box, cols_box):
        box.label.set_color(FG)

    def layout(event=None):
        """Keep the grid centered at any window size; colorbar sits to its right."""
        W, H = fig.get_size_inches()
        side = min(0.68 * H, 0.72 * W)               # square area that holds the grid
        left, bottom = (W - side) / 2, (H - side) / 2 - 0.02 * H
        ax.set_position([left / W, bottom / H, side / W, side / H])
        cax.set_position([(left + side + 0.03 * W) / W, bottom / H, 0.02, side / H])
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
        d = state["ema"] - state["base"]             # change from resting value (pF)
        d = {"both": np.abs(d), "up": d, "down": -d}[args.direction]
        dead = np.maximum(args.sigma * state["noise"] * noise_factor, args.deadband)
        change = np.nan_to_num(np.clip(d - dead, 0, None))   # 0 => cream
        return change, "Press r to recalibrate" + warn, raw

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

    rows_box.on_submit(on_size_submit)
    cols_box.on_submit(on_size_submit)

    def on_key(event):
        # Don't treat the letter 'r' as "recalibrate" while typing in a box.
        if any(getattr(b, "capturekeystrokes", False) for b in (rows_box, cols_box)):
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