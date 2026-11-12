#!/usr/bin/env python3
"""
Capacitive-textile heatmap, SPEED-OPTIMIZED build (text serial input, 115200 baud default).

Same behaviour, layout, colors and command-line options as cap_heatmap.py, but much
cheaper per serial line and per redraw. What changed:

  INTAKE
    * Serial bytes are split and parsed with plain bytes.split()/int() instead of a regex
      plus decode() per line, and a whole chunk of lines is applied to the arrays in one
      vectorised numpy step (np.bincount for calibration sums, a rank-ordered EMA update
      so repeated cells in one chunk still average in arrival order).
    * Calibration completion is checked once per chunk, not once per line.
    * The noise "dead zone" is computed once when calibration ends, not every frame.

  DISPLAY
    * Blitting: the static parts (axes, ticks, colorbar, title) are cached as a bitmap and
      each frame only the heatmap image, cell grid, numbers and status text are redrawn.
    * Cell number text is only updated for cells whose value actually changed, and the
      white/black text color is decided for all cells at once with numpy (the original
      called the PowerNorm object once per cell per frame, which is very slow).
    * If nothing visible changed since the last frame, the redraw is skipped entirely.
    * plt.pause() is replaced by canvas.flush_events(), and the serial read no longer
      blocks for 50 ms when idle.

  NOTE: at 115200 baud, one "r,c,value" line is ~10 bytes, so the link itself carries only
  ~1100 cells/s (~17 full 8x8 frames/s). If you need more sensor frames per second, raise
  the baud in the firmware and pass --baud to match.

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

GRID SIZE
    Type a number into the "Rows" / "Cols" boxes at the top of the window and press
    Enter. The grid redraws immediately and recalibration restarts.
    (--rows / --cols only set the starting values.)

COLORS
    First --calib-seconds: learns each cell's resting capacitance (don't touch!).
    After that a cell stays CREAM until its capacitance rises above its own baseline;
    the bigger the rise, the hotter the color (cream -> yellow -> orange -> red).
    Every cell always prints its raw capacitance in pF, rounded to a whole number.

    python cap_heatmap_fast.py --port /dev/cu.usbserial-0001
    python cap_heatmap_fast.py --port /dev/cu.usbserial-0001 --rows 8 --cols 8 --full-scale 2

Press  r  in the plot window to recalibrate (not while typing in a box).
If the window ever looks wrong on your GUI backend, add --no-blit to fall back to
ordinary full redraws (still faster than the original thanks to the other changes).
"""
import argparse
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
import serial
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.widgets import TextBox

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ----------------------------------------------------------------------------
# Fixed settings
# ----------------------------------------------------------------------------
BAUD = 115200            # default; must match Serial.begin() in the firmware
UNIT = 1000.0            # serial integers are counts of 1/1000 pF (milli-pF)
MAX_DIM = 64             # largest rows/cols you can type into the boxes
NO_VALUE = np.iinfo(np.int64).min        # marks "no reading yet" in the label cache

PURPLE = "#4E2A84"       # window background
CREAM = "#FFF3D6"        # resting color of every cell
FG, FG_DIM = "white", "#D8CCEB"
TITLE = "Two Layer Knitted Textile: Capacitive Sensing"
CMAP = LinearSegmentedColormap.from_list(
    "cream_hot", [CREAM, "#FFE08A", "#FFC94D", "#FF8C1A", "#E8281E", "#7A0000"])


def parse_chunk(lines):
    """Parse a list of byte-string lines of 'row,col,value'.
    Returns (rows, cols, milli_pF_values, last_unparsed_line_or_None).
    No range check here: the caller decides whether (row, col) fits the current grid."""
    rows, cols, vals, bad = [], [], [], None
    for ln in lines:
        parts = ln.split(b",")
        if len(parts) == 3:
            try:
                r, c, v = int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                pass
            else:
                if r >= 0 and c >= 0:
                    rows.append(r)
                    cols.append(c)
                    vals.append(v)
                    continue
        s = ln.strip()
        if s and not s.startswith(b"#"):
            bad = s
    return rows, cols, vals, bad


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="serial port, e.g. /dev/cu.usbserial-0001")
    p.add_argument("--baud", type=int, default=BAUD, help="serial baud rate (must match firmware)")
    p.add_argument("--rows", type=int, default=8, help="starting number of rows (editable in window)")
    p.add_argument("--cols", type=int, default=8, help="starting number of columns (editable in window)")
    p.add_argument("--max-fps", type=float, default=60.0, help="cap on screen redraws per second")
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
    p.add_argument("--no-blit", action="store_true",
                   help="disable the blitting fast path (use ordinary full redraws)")
    args = p.parse_args()

    # Current grid size. Changed live by the Rows / Cols text boxes.
    grid = {"rows": int(np.clip(args.rows, 1, MAX_DIM)),
            "cols": int(np.clip(args.cols, 1, MAX_DIM))}

    alpha = 1.0 / max(args.avg, 1)
    noise_factor = np.sqrt(alpha / (2 - alpha))     # noise reduction from the running average
    # Text turns white once the color-curve value passes 0.65. Since the curve is
    # (change / full_scale) ** gamma, that is the same as change > this threshold.
    white_thr = args.full_scale * 0.65 ** (1.0 / args.gamma)

    # ------------------------------------------------------------------------
    # Figure, heatmap image, colorbar
    # ------------------------------------------------------------------------
    norm = PowerNorm(gamma=args.gamma, vmin=0, vmax=args.full_scale, clip=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PURPLE)
    use_blit = bool(getattr(fig.canvas, "supports_blit", False)) and not args.no_blit

    # Artists that change every frame are marked "animated" so they are left out of the
    # cached background bitmap and redrawn on top of it each frame (blitting).
    im = ax.imshow(np.zeros((grid["rows"], grid["cols"])), cmap=CMAP, norm=norm,
                   interpolation="gaussian" if args.smooth else "nearest",
                   origin="lower", animated=use_blit)
    ax.set_xlabel("Column  (0 = left)", color=FG)
    ax.set_ylabel("Row  (0 = bottom)", color=FG)
    ax.tick_params(axis="both", which="major", colors=FG)
    for spine in ax.spines.values():
        spine.set_edgecolor(FG)
    fig.text(0.5, 0.975, TITLE, ha="center", va="top", color=FG, fontsize=15, fontweight="bold")

    cax = fig.add_axes([0.9, 0.2, 0.02, 0.6])        # positioned by layout()
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("Increase from baseline (pF)", color=FG)
    cbar.ax.tick_params(colors=FG)
    cbar.outline.set_edgecolor(FG)

    status = fig.text(0.015, 0.015, "", ha="left", va="bottom", fontsize=8, color=FG_DIM,
                      animated=use_blit)
    metrics = fig.text(0.985, 0.015, "", ha="right", va="bottom", fontsize=8, color=FG_DIM,
                       animated=use_blit)

    texts = []          # texts[r][c] is the number drawn in cell (r, c); rebuilt on grid change
    grid_lc = [None]    # the black lines between cells (one LineCollection)
    bg = {"img": None}  # cached bitmap of everything that does NOT change per frame
    cache = {"show": None, "msg": None, "fps": None, "txt": None, "col": None}

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

    def on_resize(event):
        bg["img"] = None                             # cached bitmap is the wrong size now
        layout(event)

    fig.canvas.mpl_connect("resize_event", on_resize)

    # ------------------------------------------------------------------------
    # Blitting
    # ------------------------------------------------------------------------
    def draw_animated():
        """Draw the per-frame artists, bottom to top (same stacking as a normal draw)."""
        ax.draw_artist(im)
        if grid_lc[0] is not None:
            ax.draw_artist(grid_lc[0])
        for spine in ax.spines.values():             # redrawn so the image can't cover them
            ax.draw_artist(spine)
        for row in texts:
            for t in row:
                ax.draw_artist(t)
        fig.draw_artist(status)
        fig.draw_artist(metrics)

    def on_draw(event):
        """After every full draw: snapshot the static background, then put the live
        artists on top of it."""
        bg["img"] = fig.canvas.copy_from_bbox(fig.bbox)
        draw_animated()

    if use_blit:
        fig.canvas.mpl_connect("draw_event", on_draw)

    def render():
        """Get the current artist state onto the screen."""
        if use_blit and bg["img"] is not None:
            fig.canvas.restore_region(bg["img"])
            draw_animated()
            fig.canvas.blit(fig.bbox)
        else:
            fig.canvas.draw_idle()                   # first frame / after resize / no blit

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
                     base=None, noise=None, dead=None, t0=None)

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
        # The dead zone only depends on the noise, so compute it once here, not per frame.
        state["dead"] = np.maximum(args.sigma * state["noise"] * noise_factor, args.deadband)
        state["ema"] = base.copy()

    def ingest_batch(rows, cols, vals):
        """Apply many readings at once. Arrays are indexed [row, col], (0,0) = bottom-left."""
        r = np.asarray(rows, dtype=np.intp)
        c = np.asarray(cols, dtype=np.intp)
        v = np.asarray(vals, dtype=np.float64) / UNIT           # milli-pF -> pF
        meta["max_r"] = max(meta["max_r"], int(r.max()))
        meta["max_c"] = max(meta["max_c"], int(c.max()))
        R, C = grid["rows"], grid["cols"]
        ok = (r < R) & (c < C)
        if not ok.all():                             # outside current grid: ignore (status bar warns)
            r, c, v = r[ok], c[ok], v[ok]
        if r.size == 0:
            return
        if state["t0"] is None:
            state["t0"] = time.perf_counter()
        state["cur"][r, c] = v                       # for repeated cells the last value wins
        flat = r * C + c
        if state["base"] is None:                    # still calibrating: accumulate sums
            size = R * C
            shape = (R, C)
            state["n"] += np.bincount(flat, minlength=size).reshape(shape)
            state["sum"] += np.bincount(flat, weights=v, minlength=size).reshape(shape)
            state["sq"] += np.bincount(flat, weights=v * v, minlength=size).reshape(shape)
            if calibration_done():
                finish_calibration()
        else:                                        # calibrated: running average of each cell
            ema = state["ema"].reshape(-1)           # flat view of the (R, C) array
            # A cell can appear several times in one chunk. Group repeats and apply them
            # in arrival order (stable sort), one "round" per repeat, so the result equals
            # feeding the readings in one at a time.
            order = np.argsort(flat, kind="stable")
            fs, vs = flat[order], v[order]
            pos = np.arange(fs.size)
            starts = np.maximum.accumulate(np.where(np.r_[True, fs[1:] != fs[:-1]], pos, 0))
            rank = pos - starts                      # 0 for first occurrence of a cell, 1 for second...
            for k in range(int(rank.max()) + 1):
                sel = rank == k
                idx, val = fs[sel], vs[sel]
                e = ema[idx]
                ema[idx] = np.where(np.isnan(e), val, e + alpha * (val - e))

    def change_grid():
        d = state["ema"] - state["base"]             # change from resting value (pF)
        if args.direction == "down":
            d = -d
        elif args.direction == "both":
            d = np.abs(d)
        return np.nan_to_num(np.clip(d - state["dead"], 0, None))   # 0 => cream

    def view():
        """Return (change_grid, status_text, raw_grid), all shaped (rows, cols)."""
        R, C = grid["rows"], grid["cols"]
        raw = state["cur"]
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

    def update_artists(show, status_msg, raw, fps_text=None):
        """Push new data into the artists, touching only what actually changed.
        Returns True if anything visible changed (i.e. a redraw is needed)."""
        changed = False
        if cache["show"] is None or not np.array_equal(show, cache["show"]):
            im.set_data(show)
            cache["show"] = show
            changed = True
        if texts:
            isn = np.isnan(raw)
            ints = np.rint(np.where(isn, 0.0, raw)).astype(np.int64)     # whole pF
            ints[isn] = NO_VALUE
            white = (show > white_thr).astype(np.int8)                   # all cells at once
            for r, c in np.argwhere(ints != cache["txt"]):
                v = ints[r, c]
                texts[r][c].set_text("" if v == NO_VALUE else str(v))
                changed = True
            for r, c in np.argwhere(white != cache["col"]):
                texts[r][c].set_color("white" if white[r, c] else "black")
                changed = True
            cache["txt"], cache["col"] = ints, white
        if status_msg != cache["msg"]:
            status.set_text(status_msg)
            cache["msg"] = status_msg
            changed = True
        if fps_text is not None and fps_text != cache["fps"]:
            metrics.set_text(fps_text)
            cache["fps"] = fps_text
            changed = True
        return changed

    def apply_grid():
        """Rebuild everything that depends on the grid size, then restart calibration."""
        R, C = grid["rows"], grid["cols"]
        bg["img"] = None                             # force a fresh background snapshot
        im.set_data(np.zeros((R, C)))
        # Cell (r, c) is centered on x=c, y=r, so the edges sit at -0.5 and R/C - 0.5.
        im.set_extent((-0.5, C - 0.5, -0.5, R - 0.5))
        ax.set_xlim(-0.5, C - 0.5)
        ax.set_ylim(-0.5, R - 0.5)                   # low y at the bottom => row 0 at the bottom
        ax.set_xticks(range(C))                      # tick labels = column numbers
        ax.set_yticks(range(R))                      # tick labels = row numbers
        if grid_lc[0] is not None:
            grid_lc[0].remove()
            grid_lc[0] = None
        if not args.smooth:                          # black grid lines between cells
            ys, xs = np.arange(-0.5, R, 1.0), np.arange(-0.5, C, 1.0)
            segs = ([[(-0.5, y), (C - 0.5, y)] for y in ys] +
                    [[(x, -0.5), (x, R - 0.5)] for x in xs])
            grid_lc[0] = LineCollection(segs, colors="black", linewidths=1, zorder=2,
                                        animated=use_blit)
            ax.add_collection(grid_lc[0], autolim=False)
        for row in texts:                            # throw away the old number labels
            for t in row:
                t.remove()
        texts.clear()
        if not args.no_labels:
            # One label per cell, placed at x=col, y=row (same mapping as the image).
            texts.extend([[ax.text(c, r, "", ha="center", va="center", zorder=3,
                                   fontsize=args.font_size or 11, fontweight="bold",
                                   animated=use_blit)
                           for c in range(C)] for r in range(R)])
        cache.update(show=None, msg=None, fps=None,
                     txt=np.full((R, C), NO_VALUE + 1, dtype=np.int64),   # never equal to a real value
                     col=np.full((R, C), -1, dtype=np.int8))
        reset()
        layout()
        update_artists(*view(), fps_text="")
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
    ser = serial.Serial(args.port, args.baud, timeout=0.005)   # short timeout: never stall the GUI
    ser.reset_input_buffer()
    plt.ion()
    plt.show(block=False)
    status.set_text("Waiting for data from the serial port...")
    cache["msg"] = "Waiting for data from the serial port..."
    fig.canvas.draw()                                # fires on_draw -> first background snapshot
    print(f"Opened {args.port} at {args.baud} baud. Waiting for data... (Ctrl+C to quit)")

    buf = bytearray()
    dirty = False
    min_dt = 1.0 / args.max_fps
    fps, t_draw = 0.0, time.perf_counter()
    t_metrics, t_events = 0.0, 0.0
    last_rx, last_warn = time.perf_counter(), 0.0
    try:
        while plt.fignum_exists(fig.number):
            waiting = ser.in_waiting
            data = ser.read(waiting if waiting else 1)
            now = time.perf_counter()
            if data:
                last_rx = now
                buf.extend(data)
                end = buf.rfind(b"\n")
                if end >= 0:                         # parse every COMPLETE line in one go
                    chunk = bytes(buf[:end])
                    del buf[:end + 1]                # keep any partial last line in buf
                    rows, cols, vals, bad = parse_chunk(chunk.split(b"\n"))
                    if rows:
                        ingest_batch(rows, cols, vals)
                        dirty = True
                    if bad is not None and now - last_warn > 2:
                        print(f"Ignored a line that isn't 'row,col,value': "
                              f"{bad[:150].decode(errors='replace')!r}")
                        last_warn = now
                elif len(buf) > 65536:               # garbage with no newline: don't grow forever
                    buf.clear()
            elif now - last_rx > 3 and now - last_warn > 3:
                print("No bytes received. Check: correct --port, firmware uploaded, "
                      "serial monitor closed.")
                last_warn = now

            if dirty and now - t_draw >= min_dt:
                dt = now - t_draw
                fps = 0.8 * fps + 0.2 / dt if fps else 1 / dt
                t_draw, dirty = now, False
                fps_text = None
                if now - t_metrics >= 0.5:           # update the fps text only twice a second
                    t_metrics = now
                    fps_text = f"display {fps:.0f} fps"
                if update_artists(*view(), fps_text=fps_text):
                    render()
                fig.canvas.flush_events()
                t_events = now
            elif now - t_events >= 0.015:            # keep the window responsive between frames
                fig.canvas.flush_events()
                t_events = now
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
