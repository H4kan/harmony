# core/runs.py
from __future__ import annotations

from pathlib import Path
import re

_RUN_RE = re.compile(r"^run(\d+)$", re.IGNORECASE)

def next_run_dir(base_dir: str) -> Path:
    """
    Zwraca ścieżkę do kolejnego folderu runN w base_dir.
    Tworzy base_dir jeśli nie istnieje.
    """
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)

    max_n = 0
    for p in base.iterdir():
        if p.is_dir():
            m = _RUN_RE.match(p.name)
            if m:
                max_n = max(max_n, int(m.group(1)))

    run_dir = base / f"run{max_n + 1}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir

def latest_run_dir(base_dir: str) -> Path:
    """
    Zwraca ścieżkę do najnowszego runN w base_dir.
    """
    base = Path(base_dir)
    if not base.exists():
        raise FileNotFoundError(f"Base dir not found: {base_dir}")

    max_n = 0
    latest = None
    for p in base.iterdir():
        if p.is_dir():
            m = _RUN_RE.match(p.name)
            if m:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
                    latest = p

    if latest is None:
        raise FileNotFoundError(f"No runN folders in: {base_dir}")

    return latest
