#!/usr/bin/env python3
"""
Plot capacitance recordings with on/off checkboxes and axis controls.

Place this script in your scripts folder, next to a folder called "recordings"
containing CSV files with the columns: cap,row,col,time_s

Run:  python plot_recordings.py
Requires: pip install pandas matplotlib

Axis controls (bottom left): type a value into X min / X max / Y min / Y max
and press Enter. Leave a box empty for automatic scaling on that limit.
"""
from pathlib import Path
import sys

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, Button, TextBox

RECORDINGS_DIR = Path(__file__).resolve().parent / "recordings"
START_VISIBLE = True  # False = everything starts unchecked


def load_recordings(folder):
    """Return {filename: [(label, time_array, cap_array), ...]}."""
    data = {}
    for path in sorted(folder.glob("*.csv")):
        try:
            df = pd.read_csv(path)
            df = df.dropna(subset=["cap", "time_s"])
        except Exception as e:
            print(f"Skipping {path.name}: {e}")
            continue

        # A file may contain several (row, col) cells; plot each as its own line
        groups = list(df.groupby(["row", "col"])) if {"row", "col"} <= set(df.columns) else [((None, None), df)]
        series = []
        for (r, c), g in groups:
            label = path.stem if len(groups) == 1 else f"{path.stem} (r{r},c{c})"
            series.append((label, g["time_s"].to_numpy(), g["cap"].to_numpy()))
        data[path.stem] = series
    return data


def main():
    if not RECORDINGS_DIR.is_dir():
        sys.exit(f"Folder not found: {RECORDINGS_DIR}")

    recordings = load_recordings(RECORDINGS_DIR)
    if not recordings:
        sys.exit(f"No CSV files found in {RECORDINGS_DIR}")

    names = list(recordings)
    n = len(names)

    fig = plt.figure(figsize=(13, 7.5))
    ax = fig.add_axes([0.30, 0.10, 0.68, 0.84])

    # Checkbox panel (sized to fit, leaving room for the controls below it)
    panel_h = min(0.55, 0.04 * n + 0.04)
    rax = fig.add_axes([0.01, 0.92 - panel_h, 0.25, panel_h])
    rax.set_title("Recordings", fontsize=10)

    lines = {}
    for name in names:
        lines[name] = []
        for label, t, cap in recordings[name]:
            (ln,) = ax.plot(t, cap, label=label, visible=START_VISIBLE, linewidth=1)
            lines[name].append(ln)

    check = CheckButtons(rax, names, [START_VISIBLE] * n)

    # Manual axis limits (None = auto)
    lim = {"xmin": None, "xmax": None, "ymin": None, "ymax": None}

    def refresh():
        ax.relim(visible_only=True)
        ax.autoscale_view()

        xlo, xhi = ax.get_xlim()
        ylo, yhi = ax.get_ylim()
        xlo = lim["xmin"] if lim["xmin"] is not None else xlo
        xhi = lim["xmax"] if lim["xmax"] is not None else xhi
        ylo = lim["ymin"] if lim["ymin"] is not None else ylo
        yhi = lim["ymax"] if lim["ymax"] is not None else yhi
        if xlo < xhi:
            ax.set_xlim(xlo, xhi)
        if ylo < yhi:
            ax.set_ylim(ylo, yhi)

        visible = [ln for lns in lines.values() for ln in lns if ln.get_visible()]
        if visible:
            ax.legend(handles=visible, loc="upper right", fontsize=8)
        elif ax.get_legend():
            ax.get_legend().remove()
        fig.canvas.draw_idle()

    def toggle(label):
        for ln in lines[label]:
            ln.set_visible(not ln.get_visible())
        refresh()

    check.on_clicked(toggle)

    def set_all(state):
        status = check.get_status()
        for i in range(n):
            if status[i] != state:
                check.set_active(i)  # triggers toggle() via callback

    # --- Axis limit text boxes -------------------------------------------
    boxes = {}

    def make_submit(key):
        def submit(text):
            text = text.strip()
            if text == "":
                lim[key] = None
            else:
                try:
                    lim[key] = float(text)
                except ValueError:
                    print(f"Invalid number for {key}: {text!r}")
                    boxes[key].set_val("" if lim[key] is None else str(lim[key]))
                    return
            refresh()
        return submit

    for key, label, y in [
        ("xmin", "X min ", 0.29),
        ("xmax", "X max ", 0.245),
        ("ymin", "Y min ", 0.20),
        ("ymax", "Y max ", 0.155),
    ]:
        bax = fig.add_axes([0.10, y, 0.15, 0.035])
        tb = TextBox(bax, label, initial="")
        tb.on_submit(make_submit(key))
        boxes[key] = tb

    def auto_axes(_=None):
        for key in lim:
            lim[key] = None
            boxes[key].set_val("")
        ax.set_yscale("linear")
        refresh()

    def toggle_log(_=None):
        ax.set_yscale("linear" if ax.get_yscale() == "log" else "log")
        refresh()

    ax_auto = fig.add_axes([0.01, 0.095, 0.11, 0.04])
    ax_log = fig.add_axes([0.14, 0.095, 0.11, 0.04])
    btn_auto = Button(ax_auto, "Auto axes")
    btn_log = Button(ax_log, "Log Y")
    btn_auto.on_clicked(auto_axes)
    btn_log.on_clicked(toggle_log)

    ax_all = fig.add_axes([0.01, 0.02, 0.11, 0.05])
    ax_none = fig.add_axes([0.14, 0.02, 0.11, 0.05])
    btn_all = Button(ax_all, "Select all")
    btn_none = Button(ax_none, "Clear all")
    btn_all.on_clicked(lambda _: set_all(True))
    btn_none.on_clicked(lambda _: set_all(False))

    ax.set_xlabel("time (s)")
    ax.set_ylabel("cap")
    ax.set_title("Capacitance recordings")
    ax.grid(True, alpha=0.3)
    refresh()
    plt.show()


if __name__ == "__main__":
    main()