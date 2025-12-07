# cell_pipeline.py

from collections import deque


class CellPipeline:
    """
    Stateful pipeline for a single sensor cell.

    Usage:
        cell = CellPipeline()
        delta, touched = cell.feed(raw_value)
    """

    def __init__(
        self,
        alpha_baseline: float = 0.0005,   # slow drift when untouched
        press_dip: int = 50000,           # detect touch start if value falls by this much
        release_band: int = 20000,        # consider released if val is within this of baseline
        window: int = 5,                  # small buffer to look at recent samples
        delta_decay: float = 0.1          # how fast delta decays back to zero when untouched
    ) -> None:
        self.alpha_baseline = alpha_baseline
        self.press_dip = press_dip
        self.release_band = release_band
        self.window = window
        self.delta_decay = delta_decay

        # internal state
        self.baseline: float | None = None
        self.delta: float = 0.0
        self.is_touched: bool = False
        self.press_buf: deque[int] = deque(maxlen=window)

    def reset(self) -> None:
        """Reset internal state (used if you want to re-baseline)."""
        self.baseline = None
        self.delta = 0.0
        self.is_touched = False
        self.press_buf.clear()

    def feed(self, val: int) -> tuple[float, bool]:
        """
        Process one raw integer reading for this cell.

        Returns:
            delta (float): processed delta (>= 0, decays to 0 when untouched)
            is_touched (bool): whether touch is currently detected
        """
        # push into detection buffer
        self.press_buf.append(val)

        # initialize baseline on first valid read
        if self.baseline is None:
            self.baseline = float(val)
            # first sample, nothing fancy yet
            return 0.0, False

        # ---- TOUCH DETECTION (on DIP START) ----
        if len(self.press_buf) > 1:
            prev_val = self.press_buf[-2]
        else:
            prev_val = val

        if (not self.is_touched) and (prev_val - val) > self.press_dip:
            self.is_touched = True

        # ---- RELEASE DETECTION (absolute hysteresis) ----
        if self.is_touched and abs(self.baseline - val) < self.release_band:
            self.is_touched = False

        # ---- BASELINE UPDATE (only when UNTOUCHED) ----
        if not self.is_touched:
            # exponential moving average toward current val
            self.baseline = (
                (1.0 - self.alpha_baseline) * self.baseline
                + self.alpha_baseline * float(val)
            )

            # sanity reset to avoid catastrophic drift
            if self.baseline < val / 20.0 or self.baseline > val * 20.0:
                self.baseline = float(val)

        # ---- DELTA UPDATE ----
        if not self.is_touched:
            # decay back toward 0 when untouched
            self.delta *= (1.0 - self.delta_decay)
            if abs(self.delta) < 1.0:
                self.delta = 0.0
        else:
            # "real" signal when touched
            self.delta = self.baseline - float(val)

        # clamp negative noise
        if self.delta < 0.0:
            self.delta = 0.0

        return self.delta, self.is_touched
