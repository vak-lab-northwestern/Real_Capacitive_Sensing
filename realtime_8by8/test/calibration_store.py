# calibration_store.py

import json
from pathlib import Path
from typing import Dict, Tuple

CellKey = Tuple[int, int]
CalibDict = Dict[str, float]  # keys as "row,col" strings for JSON


def _key(row: int, col: int) -> str:
    return f"{row},{col}"


def load_max_deltas(path: str | Path) -> Dict[CellKey, float]:
    """
    Load per-cell max deltas from JSON file.

    Returns dict keyed by (row, col) → max_delta.
    If file doesn't exist, returns empty dict.
    """
    path = Path(path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data: CalibDict = json.load(f)

    out: Dict[CellKey, float] = {}
    for key_str, val in data.items():
        row_str, col_str = key_str.split(",")
        out[(int(row_str), int(col_str))] = float(val)

    return out


def save_max_deltas(path: str | Path, max_deltas: Dict[CellKey, float]) -> None:
    """
    Save per-cell max deltas to JSON file.

    Input dict is keyed by (row, col).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data: CalibDict = {}
    for (r, c), v in max_deltas.items():
        data[_key(r, c)] = float(v)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

