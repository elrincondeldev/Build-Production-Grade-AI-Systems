"""Versioned model artifacts with sha256 verification (📖 lesson 1.5).

Layout written by ``training.py``::

    artifacts/fraud-model/
      LATEST                      <- text file containing the newest version
      20261110T153000Z-1a2b3c4d/
        model.joblib              <- the serialized estimator
        metadata.json             <- sha256, data digest, git commit, features, metrics…

Why verify the hash *before* loading? joblib and pickle files can execute
arbitrary code when loaded. The checksum proves the file is byte-for-byte the
one the training job produced, and catches truncated or corrupted copies.
It is not a signature: anyone who can rewrite both files can fake it
(Module 5 discusses signing).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from ..domain.features import FEATURE_NAMES

MODEL_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"
LATEST_POINTER = "LATEST"


class ArtifactError(Exception):
    """Base class for artifact problems."""


class ArtifactNotFound(ArtifactError):
    pass


class ArtifactIntegrityError(ArtifactError):
    """The model file does not match the checksum recorded at training time."""


class ArtifactIncompatible(ArtifactError):
    """The artifact was trained with a different feature contract than this code."""


@dataclass(frozen=True)
class LoadedModel:
    model: Any
    version: str
    metadata: dict[str, Any]
    path: Path


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_version(model_dir: Path, version: str) -> Path:
    """Map 'latest' (or an explicit version) to a directory."""
    if version == "latest":
        pointer = model_dir / LATEST_POINTER
        if not pointer.exists():
            raise ArtifactNotFound(f"no {LATEST_POINTER} pointer in {model_dir}; run the training script first")
        version = pointer.read_text().strip()
    path = model_dir / version
    if not (path / MODEL_FILENAME).exists() or not (path / METADATA_FILENAME).exists():
        raise ArtifactNotFound(f"artifact {path} is missing {MODEL_FILENAME} or {METADATA_FILENAME}")
    return path


def load_artifact(model_dir: Path, version: str = "latest") -> LoadedModel:
    path = resolve_version(Path(model_dir), version)
    metadata = json.loads((path / METADATA_FILENAME).read_text())

    expected = metadata.get("model_sha256")
    actual = sha256_file(path / MODEL_FILENAME)
    if expected != actual:
        raise ArtifactIntegrityError(
            f"checksum mismatch for {path / MODEL_FILENAME}: metadata says {expected}, file is {actual}"
        )

    trained_features = tuple(metadata.get("features", []))
    if trained_features != FEATURE_NAMES:
        raise ArtifactIncompatible(
            "artifact feature list differs from the serving code's FEATURE_NAMES; "
            "this would cause training/serving skew. Retrain or deploy matching code."
        )

    # Only now, after the integrity check, do we deserialize.
    model = joblib.load(path / MODEL_FILENAME)
    return LoadedModel(model=model, version=metadata["version"], metadata=metadata, path=path)
