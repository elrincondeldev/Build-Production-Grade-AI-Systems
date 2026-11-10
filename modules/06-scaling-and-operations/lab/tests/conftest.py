from pathlib import Path

import pytest

LAB_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def lab_dir() -> Path:
    return LAB_DIR
