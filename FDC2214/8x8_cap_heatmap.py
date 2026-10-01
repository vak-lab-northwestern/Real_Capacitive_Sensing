#!/usr/bin/env python3
"""
Fast 8x8 capacitance heatmap for the FDC2214 + dual-mux sketch.

Accepts either serial format:
  new (capacitance_grid.ino): 64 tab-separated values per line, row-major
  old:                        0,0: 12.3456<TAB>0,1: 12.4001 ...

    python cap_heatmap.py --port /dev/cu.usbserial-0001              # raw pF
    python cap_heatmap.py --port /dev/cu.usbserial-0001 --delta      # change vs background
    python cap_heatmap.py --port /dev/cu.usbserial-0001 --baseline 20
    python cap_heatmap.py --file capture.txt
Baud must match the sketch (new sketch = 921600, old sketch = 115200).
"""
import argparse
import re
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

ROWS, COLS = 8, 8
PATTERN = re.compile(r"(\d+),(\d+):\s*(-?\d+(?:\.\d+)?)")


def parse_line(line):
    """Return an 8x8 array (NaN = missing) or None if the line isn't data."""
    found = PATTERN.findall(line)
    if found:                                   # old labeled format
        grid = np.full((ROWS, COLS), np.nan)
        for r, c, v in found:
            r, c = int(r), int(c)
            if r < ROWS and c < COLS:
                grid[r, c] = float(v)
        return grid
    try:                                        # new compact format
        vals = [float(x) for x in line.split()]
    except ValueError:
        return None
    if len(vals) != ROWS * COLS:
        return None
    return np.array(vals).reshape(ROWS, COLS)


def main():
    p = argparse.ArgumentParser()
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--port")
    src.add_argument("--file")
    p.add_argument("--baud", type=int, default=921600)
    p.add_argument("--delta", action="store_true",
                   help="Color by increase over background instead of raw pF")
    p.add_argument("--baseline", type=int, default=0,
                   help="Average first N frames and subtract them (implies --delta)")
    p.add_argument("--min-span", type=float, default=0.5,
                   help="Delta mode only: smallest pF increase that reaches full red")
    p.add_argument("--smooth", action="store_true", help="Smooth gradient instead of squares")
    p.add_argument("--no-labels", action="store_true", help="Hide the raw pF value in each cell")
    args = p.parse_args()
    delta_mode = args.delta or args.baseline > 0

    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(np.zeros((ROWS, COLS)), cmap="YlOrRd", vmin=0, vmax=1,
                   interpolation="gaussian" if args.smooth else "nearest")
    ax.set_xticks(range(COLS)); ax.set_yticks(range(ROWS))
    ax.set_xlabel("Column"); ax.set_ylabel("Row")
    if not args.smooth:   # grid lines between cells
        ax.set_xticks(np.arange(-0.5, COLS, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, ROWS, 1), minor=True)
        ax.grid(which="minor", color="black", linewidth=1)
        ax.tick_params(which="minor", length=0)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Increase above background (pF)" if delta_mode else "Capacitance (pF)")
    texts = None
    if not args.no_labels:
        texts = [[ax.text(c, r, "", ha="center", va="center", fontsize=7)
                  for c in range(COLS)] for r in range(ROWS)]

    state = {"last": np.full((ROWS, COLS), np.nan), "base": [], "baseline": None}

    def process(line):
        """Return (color_grid, title, raw_grid) or None."""
        grid = parse_line(line)
        if grid is None:
            return None
        state["last"] = np.where(np.isnan(grid), state["last"], grid)
        raw = state["last"].copy()
        if not delta_mode:
            return raw, "Raw capacitance (pF)", raw
        if args.baseline:
            if state["baseline"] is None:
                state["base"].append(raw)
                if len(state["base"]) >= args.baseline:
                    state["baseline"] = np.nanmean(state["base"], axis=0)
                return (np.zeros((ROWS, COLS)),
                        f"Calibrating {len(state['base'])}/{args.baseline}", raw)
            return raw - state["baseline"], "Delta from baseline", raw
        return raw - np.nanmedian(raw), "Increase over background", raw

    def draw(show, title, raw, fps=None):
        im.set_data(np.ma.masked_invalid(show))
        if delta_mode:
            im.set_clim(0, max(float(np.nanmax(show)), args.min_span))
        else:   # raw: scale to the actual min/max of the data
            lo, hi = float(np.nanmin(show)), float(np.nanmax(show))
            im.set_clim(lo, max(hi, lo + 1e-3))
        if texts:
            for r in range(ROWS):
                for c in range(COLS):
                    v = raw[r, c]
                    texts[r][c].set_text("" if np.isnan(v) else f"{v:.2f}")
        ax.set_title(title + (f" - {fps:.1f} fps" if fps else ""))

    if args.file:
        result = None
        with open(args.file) as f:
            for line in f:
                result = process(line) or result
        if result is None:
            sys.exit("No data found in file.")
        draw(*result)
        plt.show()
        return

    import serial
    ser = serial.Serial(args.port, args.baud, timeout=0.1)
    ser.reset_input_buffer()
    plt.ion(); plt.show(block=False)
    buf, fps, t_prev = b"", 0.0, time.perf_counter()
    try:
        while plt.fignum_exists(fig.number):
            buf += ser.read(max(ser.in_waiting, 1))
            if b"\n" not in buf:
                plt.pause(0.001)
                continue
            # Take only the NEWEST complete line; older ones are stale, so skip them
            lines = buf.split(b"\n")
            buf = lines[-1]
            result = None
            for raw_line in lines[-3:-1][::-1]:
                result = process(raw_line.decode(errors="ignore"))
                if result is not None:
                    break
            if result is None:
                continue
            now = time.perf_counter()
            fps = 0.8 * fps + 0.2 / max(now - t_prev, 1e-6) if fps else 1 / (now - t_prev)
            t_prev = now
            draw(*result, fps=fps)
            plt.pause(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
