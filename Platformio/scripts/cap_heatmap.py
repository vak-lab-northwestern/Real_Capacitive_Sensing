#!/usr/bin/env python3
"""
8x8 pressure/touch heatmap for the FDC2214 + dual-mux firmware.

1. For the first 5 seconds it learns each cell's resting capacitance (don't touch!).
2. After that, every cell stays CREAM until its capacitance rises above its own baseline.
   The bigger the increase, the hotter the color (cream -> yellow -> orange -> red).
3. Each cell always prints its raw capacitance in pF, rounded to a whole number.
4. Row 0 is at the top and row 7 at the bottom; column 0 is on the left. Cell (0,0) is the
   top-left corner and (7,7) the bottom-right. The grid stays centered at any window size
   (press f for full screen).

Serial formats (--format):
  binary (default): 5-byte packets [0xA5][idx][lo][hi][chk], value = 1/100 pF  (current main.cpp)
  text:             per-line formats below
Text formats (auto-detected per line):
  streaming cells:  3,5,512345        row,col,milli-pF
  full frames:      64 numbers (or 16 for a 4x4 board), tab/space/comma separated
  labeled:          0,0: 12.3456<TAB>0,1: 12.4001 ...
  timing comment:   #frame_us=12345   (shown in the title)

    python cap_heatmap.py --port /dev/cu.usbserial-0001
    python cap_heatmap.py --port /dev/cu.usbserial-0001 --full-scale 2
    python cap_heatmap.py --file capture.txt

Press  r  in the plot window to recalibrate.
Baud must match the firmware (current main.cpp = 921600).
"""
import argparse
import re
import sys
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, PowerNorm

warnings.filterwarnings("ignore", category=RuntimeWarning)
ROWS, COLS = 8, 8
CELL = re.compile(r"^\s*(\d+),(\d+),(-?\d+)\s*$")
LABELED = re.compile(r"(\d+),(\d+):\s*(-?\d+(?:\.\d+)?)")
PURPLE = "#4E2A84"          # Northwestern purple (window background)
CREAM = "#FFF3D6"           # resting color of every cell
FG, FG_DIM = "white", "#D8CCEB"
TITLE = "Two Layer 8x8 Knitted Textile: Capacitive Sensing"
CMAP = LinearSegmentedColormap.from_list(
    "cream_hot", [CREAM, "#FFE08A", "#FFC94D", "#FF8C1A", "#E8281E", "#7A0000"])


PKT_LEN, SYNC, FRAME_IDX = 5, 0xA5, 0xFE


def parse_binary(buf):
    """Pull every valid 5-byte packet out of bytearray buf (consumed in place).
    Returns (list of (idx, value), number_of_bytes_discarded). Bad bytes are skipped
    one at a time until a packet with a correct checksum lines up again."""
    out, i, dropped = [], 0, 0
    while len(buf) - i >= PKT_LEN:
        if buf[i] == SYNC:
            idx, lo, hi, chk = buf[i + 1], buf[i + 2], buf[i + 3], buf[i + 4]
            if chk == (idx ^ lo ^ hi ^ 0x5A) and (idx < ROWS * COLS or idx == FRAME_IDX):
                out.append((idx, lo | (hi << 8)))
                i += PKT_LEN
                continue
        i += 1
        dropped += 1
    del buf[:i]
    return out, dropped


def parse_line(line, unit):
    """Return a list of (row, col, pF) updates, or None if the line isn't data."""
    m = CELL.match(line)
    if m:
        r, c, v = int(m[1]), int(m[2]), int(m[3])
        return [(r, c, v / unit)] if r < ROWS and c < COLS else None
    found = LABELED.findall(line)
    if found:
        out = [(int(r), int(c), float(v)) for r, c, v in found
               if int(r) < ROWS and int(c) < COLS]
        return out or None
    try:
        vals = [float(x) for x in line.replace(",", " ").split()]
    except ValueError:
        return None
    if not vals or not np.all(np.isfinite(vals)):       # nan/inf => sensor read failed
        return None
    if len(vals) == ROWS * COLS:
        return [(i // COLS, i % COLS, v) for i, v in enumerate(vals)]
    if len(vals) == 16:                                  # 4x4 board -> top-left corner
        return [(i // 4, i % 4, v) for i, v in enumerate(vals)]
    return None


def main():
    p = argparse.ArgumentParser()
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--port")
    src.add_argument("--file")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--format", choices=["binary", "text"], default="text",
               help="Serial format: text lines (default) or binary packets")
    p.add_argument("--unit", type=float, default=None,
                   help="Integer values are counts of 1/unit pF (default: 100 binary, 1000 text)")
    p.add_argument("--max-fps", type=float, default=30.0, help="Cap on screen redraws per second")
    p.add_argument("--calib-seconds", type=float, default=4.0,
                   help="Seconds spent learning each cell's resting value (serial mode)")
    p.add_argument("--calib-frames", type=int, default=50,
                   help="Samples per cell used for calibration when reading --file")
    # --- sensitivity knobs ---
    p.add_argument("--full-scale", type=float, default=4.0,
                   help="Change (pF) that shows as full dark red. LOWER = MORE SENSITIVE")
    p.add_argument("--gamma", type=float, default=0.5,
                   help="Color curve; below 1 boosts small changes (0.5 = sqrt), 1 = linear")
    p.add_argument("--sigma", type=float, default=2.5,
                   help="Ignore changes under this many noise std-devs per cell. Lower = more sensitive")
    p.add_argument("--deadband", type=float, default=0.1,
                   help="Also ignore changes under this many pF (keeps rest state white)")
    p.add_argument("--avg", type=int, default=3,
                   help="Smooth each cell over ~N readings to cut jitter (1 = off)")
    p.add_argument("--direction", choices=["both", "up", "down"], default="up",
                   help="Which capacitance change counts as heat: up (default), down, or both")
    p.add_argument("--smooth", action="store_true", help="Smooth gradient instead of squares")
    p.add_argument("--font-size", type=float, default=None,
                   help="Fixed size for the pF numbers (default: scales with the window)")
    p.add_argument("--no-labels", action="store_true", help="Hide the raw pF value in each cell")
    args = p.parse_args()
    if args.unit is None:
        args.unit = 100.0 if args.format == "binary" else 1000.0

    alpha = 1.0 / max(args.avg, 1)
    noise_factor = np.sqrt(alpha / (2 - alpha))         # noise reduction from the running average

    norm = PowerNorm(gamma=args.gamma, vmin=0, vmax=args.full_scale, clip=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PURPLE)
    im = ax.imshow(np.zeros((ROWS, COLS)), cmap=CMAP, norm=norm,
                   interpolation="gaussian" if args.smooth else "nearest",
                   origin="upper")                      # row 0 at the TOP, row 7 at the BOTTOM
    ax.set_xticks(range(COLS)); ax.set_yticks(range(ROWS))
    ax.set_xlabel("Column", color=FG); ax.set_ylabel("Row", color=FG)
    ax.tick_params(axis="both", which="major", colors=FG)
    for spine in ax.spines.values():
        spine.set_edgecolor(FG)
    if not args.smooth:   # grid lines between cells
        ax.set_xticks(np.arange(-0.5, COLS, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, ROWS, 1), minor=True)
        ax.grid(which="minor", color="black", linewidth=1)
        ax.tick_params(which="minor", length=0)
    ax.set_title(TITLE, color=FG, fontsize=15, fontweight="bold", pad=14)
    cax = fig.add_axes([0.9, 0.2, 0.02, 0.6])           # positioned by layout() below
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("Increase from baseline (pF)", color=FG)
    cbar.ax.tick_params(colors=FG)
    cbar.outline.set_edgecolor(FG)
    status = fig.text(0.015, 0.015, "", ha="left", va="bottom", fontsize=8, color=FG_DIM)
    metrics = fig.text(0.985, 0.015, "", ha="right", va="bottom", fontsize=8, color=FG_DIM)
    texts = None
    if not args.no_labels:
        texts = [[ax.text(c, r, "", ha="center", va="center",
                          fontsize=args.font_size or 11, fontweight="bold")
                  for c in range(COLS)] for r in range(ROWS)]

    def layout(event=None):
        """Keep the grid a centered square at any window size; colorbar sits to its right."""
        W, H = fig.get_size_inches()
        side = min(0.74 * H, 0.72 * W)
        left, bottom = (W - side) / 2, (H - side) / 2
        ax.set_position([left / W, bottom / H, side / W, side / H])
        cax.set_position([(left + side + 0.03 * W) / W, bottom / H, 0.02, side / H])
        if texts and args.font_size is None:
            fs = float(np.clip(0.25 * (side / ROWS) * 72, 6, 48))
            for row in texts:
                for t in row:
                    t.set_fontsize(fs)

    fig.canvas.mpl_connect("resize_event", layout)
    layout()

    state, meta = {}, {"frame_us": None}

    def reset():
        nan = np.full((ROWS, COLS), np.nan)
        state.update(cur=nan.copy(), ema=nan.copy(), n=np.zeros((ROWS, COLS)),
                     sum=np.zeros((ROWS, COLS)), sq=np.zeros((ROWS, COLS)),
                     base=None, noise=None, t0=None)

    reset()

    def calibration_done():
        if not args.file and time.perf_counter() - state["t0"] < args.calib_seconds:
            return False
        seen = state["n"] > 0
        if not seen.any():
            return False
        m = state["n"][seen].min()
        return m >= (args.calib_frames if args.file else 2)

    def finish_calibration():
        n, seen = state["n"], state["n"] > 0
        base = np.where(seen, state["sum"] / np.maximum(n, 1), np.nan)
        var = np.where(seen, state["sq"] / np.maximum(n, 1) - base ** 2, 0.0)
        state["base"] = base
        state["noise"] = np.sqrt(np.clip(np.nan_to_num(var), 0, None))
        state["ema"] = base.copy()

    def ingest(r, c, v):
        if state["t0"] is None:
            state["t0"] = time.perf_counter()
        state["cur"][r, c] = v
        if state["base"] is None:                       # calibration: per-cell running sums
            state["n"][r, c] += 1
            state["sum"][r, c] += v
            state["sq"][r, c] += v * v
            if calibration_done():
                finish_calibration()
        else:                                           # running average of each cell
            e = state["ema"][r, c]
            state["ema"][r, c] = v if np.isnan(e) else e + alpha * (v - e)

    def handle(line):
        """Feed one text line in. Returns False only if it looked like data but wasn't parseable."""
        line = line.strip()
        if not line:
            return True
        if line.startswith("#"):
            m = re.search(r"frame_us=(\d+)", line)
            if m:
                meta["frame_us"] = int(m.group(1))
            return True
        updates = parse_line(line, args.unit)
        if updates is None:
            return False
        for r, c, v in updates:
            ingest(r, c, v)
        return True

    def handle_packets(pkts):
        for idx, val in pkts:
            if idx == FRAME_IDX:
                meta["frame_us"] = val * 100
            else:
                ingest(idx // COLS, idx % COLS, val / args.unit)

    def view():
        """Return (change_grid, title, raw_grid). change_grid is 0 at rest."""
        raw = state["cur"].copy()
        if state["base"] is None:
            seen = state["n"] > 0
            if args.file:
                got = int(state["n"][seen].min()) if seen.any() else 0
                msg = f"Calibrating {got}/{args.calib_frames} samples per cell"
            else:
                t0 = state["t0"] or time.perf_counter()
                left = max(args.calib_seconds - (time.perf_counter() - t0), 0)
                msg = f"Calibrating... {left:.1f}s - don't touch the sensor"
            return np.zeros((ROWS, COLS)), msg, raw
        d = state["ema"] - state["base"]
        d = {"both": np.abs(d), "up": d, "down": -d}[args.direction]
        dead = np.maximum(args.sigma * state["noise"] * noise_factor, args.deadband)
        change = np.nan_to_num(np.clip(d - dead, 0, None))   # 0 => white
        return change, "Press r to recalibrate", raw

    def draw(show, status_msg, raw, fps=None):
        im.set_data(show)
        if texts:
            for r in range(ROWS):
                for c in range(COLS):
                    v = raw[r, c]
                    t = texts[r][c]
                    t.set_text("" if np.isnan(v) else str(int(round(v))))   # whole pF
                    t.set_color("white" if float(norm(show[r, c])) > 0.65 else "black")
        status.set_text(status_msg)
        parts = []
        if fps:
            parts.append(f"display {fps:.0f} fps")
        if meta["frame_us"]:
            parts.append(f"device scan {meta['frame_us'] / 1000:.0f} ms ({1e6 / meta['frame_us']:.1f}/s)")
        metrics.set_text("   |   ".join(parts))

    def on_key(event):
        if event.key == "r":
            reset()

    fig.canvas.mpl_connect("key_press_event", on_key)

    if args.file:
        seen_any = False
        if args.format == "binary":
            with open(args.file, "rb") as f:
                pkts, _ = parse_binary(bytearray(f.read()))
            handle_packets(pkts)
            seen_any = any(i != FRAME_IDX for i, _ in pkts)
        else:
            with open(args.file) as f:
                for line in f:
                    seen_any |= handle(line) and bool(line.strip()) and not line.startswith("#")
        if not seen_any:
            sys.exit("No data found in file.")
        draw(*view())
        plt.show()
        return

    import serial
    ser = serial.Serial(args.port, args.baud, timeout=0.05)
    ser.reset_input_buffer()
    plt.ion(); plt.show(block=False)
    status.set_text("Waiting for data from the serial port...")
    print(f"Opened {args.port} at {args.baud} baud. Waiting for data... (Ctrl+C to quit)")
    buf = bytearray() if args.format == "binary" else b""
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
                      "serial monitor closed, baud matches Serial.begin().")
                last_warn = now

            if args.format == "binary":
                pkts, dropped = parse_binary(buf)
                if pkts:
                    handle_packets(pkts)
                    dirty = True
                elif dropped > 20 and now - last_warn > 2:
                    print("Receiving bytes but no valid packets. Check the baud rate, or use "
                          "--format text if the firmware still sends text lines.")
                    last_warn = now
            elif b"\n" in buf:
                *lines, buf = buf.split(b"\n")
                bad = None
                for raw_line in lines:                  # every cell update counts: ingest ALL lines
                    if handle(raw_line.decode(errors="ignore")):
                        dirty = True
                    else:
                        bad = raw_line
                if bad is not None and now - last_warn > 2:
                    print(f"Got data but couldn't parse it: {bad.decode(errors='replace')[:150]!r}")
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