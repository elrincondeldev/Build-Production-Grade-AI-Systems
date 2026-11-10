"""Fingerprints for lineage: "which exact data / code / environment made this model?" 📖 Lessons 2.2 and 2.6."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pandas as pd


def file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    """Hash the bytes of a file (streaming, so it works for multi-GB files too)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def dataframe_sha256(df: pd.DataFrame) -> str:
    """Content hash of a DataFrame, independent of column order.

    Two files can differ in bytes (CSV quoting, float formatting) but hold the same
    data; this digest identifies the *content* the model was actually trained on.
    """
    canonical = df.reindex(sorted(df.columns), axis=1)
    row_hashes = pd.util.hash_pandas_object(canonical, index=False).to_numpy()
    return hashlib.sha256(row_hashes.tobytes()).hexdigest()


def git_state(cwd: Path | None = None) -> dict[str, str]:
    """Current commit and whether the working tree has uncommitted changes."""
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    commit = run("rev-parse", "HEAD") or "unknown (no commits yet?)"
    dirty = "true" if run("status", "--porcelain") else "false"
    return {"git_commit": commit, "git_dirty": dirty}
