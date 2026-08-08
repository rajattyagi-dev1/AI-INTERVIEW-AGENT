"""
Data loader for curriculum.json and candidates.json.

Reads from the authoritative data/ directory at the project root.
Both datasets are loaded once at module import time and exposed as
module-level constants. All other modules import from here.

Path resolution uses pathlib so it works regardless of the working
directory from which uvicorn is launched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Project root is three levels up from this file:
#   backend/data/loader.py  →  backend/data/  →  backend/  →  project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"


def _load_json(filename: str) -> Any:
    path = _DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Required data file not found: {path}\n"
            f"Expected location: {_DATA_DIR}"
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# curriculum: dict with keys "cohort", "modules", "days"
# Keyed lookup: curriculum_by_day[7] → full day record
# ---------------------------------------------------------------------------
curriculum: dict[str, Any] = _load_json("curriculum.json")

curriculum_by_day: dict[int, dict[str, Any]] = {
    day["day"]: day for day in curriculum["days"]
}

modules: list[dict[str, Any]] = curriculum["modules"]


# ---------------------------------------------------------------------------
# candidates: list of candidate dicts
# Keyed lookup: candidates_by_id["CAND-001"] → full candidate record
# ---------------------------------------------------------------------------
_candidates_raw: dict[str, Any] = _load_json("candidates.json")

candidates: list[dict[str, Any]] = _candidates_raw["candidates"]

candidates_by_id: dict[str, dict[str, Any]] = {
    c["member"]["id"]: c for c in candidates
}
