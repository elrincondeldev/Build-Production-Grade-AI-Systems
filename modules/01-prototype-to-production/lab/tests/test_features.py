from kestrel_fraud.domain.features import (
    FEATURE_NAMES,
    FORBIDDEN_COLUMNS,
    InvalidTransaction,
    Transaction,
    build_feature_vector,
    transaction_from_csv_row,
)

import pytest

from .conftest import VALID_TXN


def test_vector_matches_feature_names():
    assert len(build_feature_vector(Transaction(**VALID_TXN))) == len(FEATURE_NAMES)


def test_unknown_category_is_rejected():
    with pytest.raises(InvalidTransaction):
        build_feature_vector(Transaction(**{**VALID_TXN, "merchant_category": "casino"}))


def test_training_and_serving_build_identical_rows():
    """Training/serving parity: a CSV row and an API payload for the same transaction
    must produce exactly the same feature vector."""
    csv_row = {k: str(int(v)) if isinstance(v, bool) else str(v) for k, v in VALID_TXN.items()}
    csv_row.update(chargeback_filed="1", is_fraud="1", timestamp="2026-01-01T00:00:00", country="FR")
    assert build_feature_vector(transaction_from_csv_row(csv_row)) == build_feature_vector(Transaction(**VALID_TXN))


class _TrapRow(dict):
    def __getitem__(self, key):
        if key in FORBIDDEN_COLUMNS - {"transaction_id"}:
            raise AssertionError(f"training code read forbidden column {key!r}: label leakage!")
        return super().__getitem__(key)


def test_training_never_reads_leaky_columns():
    row = {k: str(int(v)) if isinstance(v, bool) else str(v) for k, v in VALID_TXN.items()}
    row.update(chargeback_filed="1", is_fraud="1")
    transaction_from_csv_row(_TrapRow(row))  # raises if a forbidden column is touched
