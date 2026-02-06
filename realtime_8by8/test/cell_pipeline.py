class CellPipeline:
    def __init__(
        self,
        alpha_baseline=0.02,
        press_dip=60,
        release_band=15,
    ):
        self.alpha_baseline = alpha_baseline
        self.press_dip = press_dip
        self.release_band = release_band

        self.baseline = None
        self.last_val = None
        self.is_touched = False

    def feed(self, val: int):
        # ---- FIRST SAMPLE ----
        if self.baseline is None:
            self.baseline = float(val)
            self.last_val = val
            return 0.0, False

        # ---- DELTA (same cell, previous frame) ----
        delta = float(val - self.last_val)

        # ---- PRESSURE ----
        pressure = self.baseline - val
        if pressure < 0:
            pressure = 0.0

        # ---- TOUCH FSM ----
        if not self.is_touched:
            if pressure > self.press_dip:
                self.is_touched = True
        else:
            if pressure < self.release_band:
                self.is_touched = False

        # ---- BASELINE UPDATE ----
        if not self.is_touched:
            self.baseline = (
                (1.0 - self.alpha_baseline) * self.baseline
                + self.alpha_baseline * float(val)
            )

        # ---- UPDATE LAST ----
        self.last_val = val

        return delta, self.is_touched
