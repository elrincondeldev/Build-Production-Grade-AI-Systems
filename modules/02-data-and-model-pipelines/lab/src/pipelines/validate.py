"""Schema + validation gate for the fraud transactions table.

A *gate* is a step that stops the pipeline when data is bad, instead of
silently training a worse model. 📖 Lesson 2.1.

Two kinds of checks:
- **Row-level** (one bad row): wrong type, out of range, unknown category, null.
  Policy: quarantine bad rows if they are rare, fail if there are too many.
- **Dataset-level** (the batch as a whole): missing columns, duplicate IDs,
  label rate outside expected bounds, too few rows. Policy: always fail.

We implement it with plain pandas so you can read every line. In production you
would likely use Pandera, Great Expectations or Soda; the ideas are identical.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd

MERCHANT_CATEGORIES = {
    "grocery", "restaurants", "fuel", "online_retail", "electronics",
    "travel", "gaming", "crypto_exchange", "pharmacy", "utilities",
}

Availability = Literal["at_decision", "post_label", "identifier", "label"]


@dataclass(frozen=True)
class Column:
    name: str
    dtype: Literal["int", "float", "str", "category"]
    nullable: bool = False
    min: float | None = None
    max: float | None = None
    allowed: frozenset[str] | None = None
    # Dataset-level distribution check: the batch median must fall in this range.
    # Catches unit changes (cents vs euros) that per-row range checks mostly miss.
    median_between: tuple[float, float] | None = None
    # When is this value known? Only `at_decision` columns may become features.
    # This one field is the cheapest leakage defence there is (📖 lesson 2.2).
    available: Availability = "at_decision"


SCHEMA: tuple[Column, ...] = (
    Column("transaction_id", "str", available="identifier"),
    Column("timestamp", "str", available="identifier"),
    Column("customer_id", "str", available="identifier"),
    Column("amount", "float", min=0.01, max=50_000, median_between=(10.0, 100.0)),
    Column("merchant_category", "category", allowed=frozenset(MERCHANT_CATEGORIES)),
    Column("hour", "int", min=0, max=23),
    Column("is_online", "int", min=0, max=1),
    Column("country", "str"),
    Column("country_mismatch", "int", min=0, max=1),
    Column("card_age_days", "int", min=0, max=20_000),
    Column("txn_count_24h", "int", min=0, max=500),
    Column("avg_amount_30d", "float", min=0.0, max=50_000),
    Column("device_is_new", "int", min=0, max=1),
    Column("distance_from_home_km", "float", min=0.0, max=20_000),
    Column("chargeback_filed", "int", min=0, max=1, available="post_label"),
    Column("is_fraud", "int", min=0, max=1, available="label"),
)

SCHEMA_BY_NAME = {c.name: c for c in SCHEMA}


@dataclass
class ValidationReport:
    rows_in: int
    rows_valid: int
    dataset_errors: list[str] = field(default_factory=list)
    row_errors: dict[str, int] = field(default_factory=dict)  # check name -> failing rows
    warnings: list[str] = field(default_factory=list)

    @property
    def bad_row_fraction(self) -> float:
        return 0.0 if self.rows_in == 0 else 1 - self.rows_valid / self.rows_in

    def summary(self) -> str:
        lines = [f"rows_in={self.rows_in} rows_valid={self.rows_valid} bad_fraction={self.bad_row_fraction:.4%}"]
        lines += [f"  DATASET ERROR: {e}" for e in self.dataset_errors]
        lines += [f"  row check failed: {k} ({v} rows)" for k, v in self.row_errors.items()]
        lines += [f"  warning: {w}" for w in self.warnings]
        return "\n".join(lines)


class DataValidationError(Exception):
    """Raised by the gate. The pipeline must stop: do not catch and continue."""

    def __init__(self, report: ValidationReport):
        super().__init__("Data validation gate FAILED\n" + report.summary())
        self.report = report


def _row_mask(df: pd.DataFrame, col: Column) -> dict[str, pd.Series]:
    """Return {check_name: boolean Series of *bad* rows} for one column."""
    s = df[col.name]
    bad: dict[str, pd.Series] = {}
    if not col.nullable:
        bad[f"{col.name}:null"] = s.isna()
    if col.dtype in ("int", "float"):
        numeric = pd.to_numeric(s, errors="coerce")
        bad[f"{col.name}:not_numeric"] = numeric.isna() & s.notna()
        if col.dtype == "int":
            bad[f"{col.name}:not_integer"] = numeric.notna() & (numeric % 1 != 0)
        if col.min is not None:
            bad[f"{col.name}:below_min"] = numeric < col.min
        if col.max is not None:
            bad[f"{col.name}:above_max"] = numeric > col.max
    if col.allowed is not None:
        bad[f"{col.name}:unknown_value"] = s.notna() & ~s.astype(str).isin(col.allowed)
    return bad


def validate(
    df: pd.DataFrame,
    *,
    min_rows: int = 1_000,
    label_rate_bounds: tuple[float, float] = (0.001, 0.10),
) -> tuple[ValidationReport, pd.DataFrame, pd.DataFrame]:
    """Validate a raw batch. Returns (report, valid_rows, quarantined_rows)."""
    report = ValidationReport(rows_in=len(df), rows_valid=0)

    missing = [c.name for c in SCHEMA if c.name not in df.columns]
    if missing:
        report.dataset_errors.append(f"missing columns: {missing}")
        return report, df.iloc[0:0], df
    extra = sorted(set(df.columns) - set(SCHEMA_BY_NAME))
    if extra:
        report.warnings.append(f"unexpected columns ignored: {extra}")

    any_bad = pd.Series(False, index=df.index)
    for col in SCHEMA:
        for name, mask in _row_mask(df, col).items():
            mask = mask.fillna(False)
            n = int(mask.sum())
            if n:
                report.row_errors[name] = n
                any_bad |= mask

    dupes = int(df["transaction_id"].duplicated().sum())
    if dupes:
        report.dataset_errors.append(f"{dupes} duplicate transaction_id values (is ingestion replaying events?)")

    valid, quarantined = df[~any_bad].copy(), df[any_bad].copy()

    for col in SCHEMA:
        if col.median_between and len(valid):
            med = float(pd.to_numeric(valid[col.name]).median())
            lo, hi = col.median_between
            if not lo <= med <= hi:
                report.dataset_errors.append(
                    f"{col.name} median {med:,.2f} outside expected [{lo:,.2f}, {hi:,.2f}] (unit change? upstream bug?)"
                )
    report.rows_valid = len(valid)

    if len(valid) < min_rows:
        report.dataset_errors.append(f"only {len(valid)} valid rows, need at least {min_rows}")
    elif "is_fraud" in valid:
        rate = float(pd.to_numeric(valid["is_fraud"]).mean())
        lo, hi = label_rate_bounds
        if not lo <= rate <= hi:
            report.dataset_errors.append(f"fraud rate {rate:.3%} outside expected bounds [{lo:.1%}, {hi:.1%}]")

    # Cast valid rows to the schema types so downstream code can trust them.
    for col in SCHEMA:
        if col.dtype == "int":
            valid[col.name] = pd.to_numeric(valid[col.name]).astype("int64")
        elif col.dtype == "float":
            valid[col.name] = pd.to_numeric(valid[col.name]).astype("float64")
        else:
            valid[col.name] = valid[col.name].astype(str)
    return report, valid, quarantined


def gate(df: pd.DataFrame, *, max_bad_row_fraction: float = 0.01, **kwargs) -> pd.DataFrame:
    """The gate: return clean rows, or raise DataValidationError and stop the pipeline."""
    report, valid, _ = validate(df, **kwargs)
    if report.bad_row_fraction > max_bad_row_fraction:
        report.dataset_errors.append(
            f"{report.bad_row_fraction:.2%} of rows failed checks (max allowed {max_bad_row_fraction:.2%})"
        )
    if report.dataset_errors:
        raise DataValidationError(report)
    return valid


def feature_columns() -> list[str]:
    """Columns that are allowed to be model inputs, according to the schema contract."""
    return [c.name for c in SCHEMA if c.available == "at_decision" and c.name != "country"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a transactions CSV")
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    report, _, _ = validate(df)
    print(report.summary())
    try:
        gate(df)
        print("✅ gate PASSED")
    except DataValidationError:
        print("❌ gate FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
