# grid_manager.py (patched to correctly pre-create a 4×4 grid)

from typing import Dict, Tuple
from cell_pipeline import CellPipeline

CellKey = Tuple[int, int]  # (row, col)

class GridManager:
    """
    Manages a 4×4 grid of CellPipeline instances.
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        **cell_kwargs
    ) -> None:
        self.rows = rows
        self.cols = cols

        # was mismatched earlier, now fixed to match your real container
        self._cells: Dict[CellKey, CellPipeline] = {}

        # Pre-create 4×4 grid (16 pipelines) using provided kwargs
        for r in range(rows):
            for c in range(cols):
                self._cells[(r, c)] = CellPipeline(**cell_kwargs)

    def _get_cell(self, row: int, col: int) -> CellPipeline:
        key = (row, col)
        if key not in self._cells:
            # Lazy-create if outside initial dims
            self.cells[key] = CellPipeline()  # unchanged conceptually
        return self._cells[key]

    def feed(self, row: int, col: int, val: int) -> tuple[float, bool]:
        """
        Route a raw reading to the appropriate cell pipeline.
        """
        cell = self._get_cell(row, col)
        return cell.feed(val)

    def reset_cell(self, row: int, col: int) -> None:
        self._get_cell(row, col).reset()

    def iter_cells(self):
        """Yield (row, col, cell pipeline)."""
        for (r, c), cell in self._cells.items():
            yield r, c, cell
