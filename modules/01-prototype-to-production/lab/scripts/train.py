"""Thin wrapper so you can run `uv run python scripts/train.py`. The logic lives in
src/kestrel_fraud/training.py so tests can import it."""

from kestrel_fraud.training import main

if __name__ == "__main__":
    main()
