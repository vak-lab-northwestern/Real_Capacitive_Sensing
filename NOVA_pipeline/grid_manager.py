# grid_manager.py

from typing import Dict, Tuple
from cell_pipeline import CellPipeline


CellKey = Tuple[int, int]  # (row, col)


class GridManager:
    """
    Manages a grid of CellPipeline instances, e.g. row=0, col=0..3.

    Usage:
        grid = GridManager(rows=1, cols=4)
        delta, touched = grid.feed(row, col, val)
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        **cell_kwargs
    ) -> None:
        self.rows = rows
        self.cols = cols
        self._cells: Dict[CellKey, CellPipeline] = {}

        # Pre-create grid (optional; we also lazy-create if needed)
        for r in range(rows):
            for c in range(cols):
                self._cells[(r, c)] = CellPipeline(**cell_kwargs)

    def _get_cell(self, row: int, col: int) -> CellPipeline:
        key = (row, col)
        if key not in self._cells:
            # Lazy-create if outside initial dims
            self._cells[key] = CellPipeline()
        return self._cells[key]

    def feed(self, row: int, col: int, val: int) -> tuple[float, bool]:
        """
        Route a raw reading to the appropriate cell pipeline.

        Returns:
            delta (float), is_touched (bool)
        """
        cell = self._get_cell(row, col)
        return cell.feed(val)

    def reset_cell(self, row: int, col: int) -> None:
        self._get_cell(row, col).reset()

    def iter_cells(self):
        """Yield (row, col, cell_pipeline_instance)."""
        for (r, c), cell in self._cells.items():
            yield r, c, cell
