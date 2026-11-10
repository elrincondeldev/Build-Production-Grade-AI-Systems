"""Locate shared course data no matter where you run commands from."""

from __future__ import annotations

import os
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """Walk up from this file until we find the repo's `datasets/` folder.

    Why not a fixed `parents[N]`? Because learners copy labs around. Walking up is
    robust, and `KESTREL_REPO_ROOT` lets you override it explicitly.
    """
    override = os.getenv("KESTREL_REPO_ROOT")
    if override:
        return Path(override).resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "datasets" / "fraud" / "generate.py").exists():
            return parent
    raise FileNotFoundError("Could not find the repo root (a folder containing datasets/). Set KESTREL_REPO_ROOT.")


def data_dir() -> Path:
    """Where this lab writes generated data (git-ignored)."""
    path = Path(os.getenv("KESTREL_LAB_DATA_DIR", LAB_DIR / "data"))
    path.mkdir(parents=True, exist_ok=True)
    return path
