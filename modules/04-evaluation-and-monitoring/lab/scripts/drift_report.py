"""Detect drift three ways. 📖 Lesson 4.5.

1. Input (data) drift: PSI + KS per feature, baseline vs a new month.
2. Concept drift: invisible to input metrics, visible only in labelled performance.
3. Embedding drift: are users asking the docs-assistant about new topics?

    uv run python scripts/drift_report.py
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from sklearn.metrics import average_precision_score, recall_score

from kestrel_docs.adapters.embeddings import HashEmbedder
from kestrel_docs.config import REPO_ROOT
from kestrel_docs.domain.handbook import load_handbook
from kestrel_docs.domain.text import content_tokens
from kestrel_fraud.data import CATEGORICAL_FEATURES, FEATURES, LABEL, NUMERIC_FEATURES, load_transactions
from kestrel_fraud.drift import centroid_cosine_distance, ks_test, psi_categorical, psi_label, psi_numeric
from kestrel_fraud.pipeline import LAB_DIR, train_or_load

QUERIES = LAB_DIR / "evals" / "data"


def feature_drift_table(reference, current) -> list[tuple[str, float, float | None]]:
    rows = []
    for col in NUMERIC_FEATURES:
        ks_stat, _ = ks_test(reference[col].to_numpy(), current[col].to_numpy())
        rows.append((col, psi_numeric(reference[col], current[col]), ks_stat))
    for col in CATEGORICAL_FEATURES:
        rows.append((col, psi_categorical(reference[col], current[col]), None))
    return sorted(rows, key=lambda r: r[1], reverse=True)


def read_queries(path: Path) -> list[str]:
    return [q.strip() for q in path.read_text(encoding="utf-8").splitlines() if q.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=20_000, help="rows per new-month scenario")
    parser.add_argument("--threshold", type=float, default=0.5, help="decision threshold for recall")
    parser.add_argument("--coverage", type=float, default=0.25, help="min similarity to count as covered")
    args = parser.parse_args()

    model, train_df, test_df = train_or_load()
    scenarios = {
        "baseline (holdout)": test_df,
        "data_drift": load_transactions("data_drift", rows=args.rows, seed=7),
        "concept_drift": load_transactions("concept_drift", rows=args.rows, seed=7),
    }

    print("=" * 72)
    print("1) INPUT DRIFT — PSI and KS per feature vs the training data")
    print("=" * 72)
    for name in ("data_drift", "concept_drift"):
        print(f"\n[{name}]")
        print(f"  {'feature':<24}{'PSI':>8}  {'status':<10}{'KS':>7}")
        for col, psi, ks in feature_drift_table(train_df, scenarios[name]):
            ks_txt = f"{ks:.3f}" if ks is not None else "  —"
            print(f"  {col:<24}{psi:>8.3f}  {psi_label(psi):<10}{ks_txt:>7}")

    print("\n" + "=" * 72)
    print("2) PERFORMANCE ON LABELLED DATA — the only way to see concept drift")
    print("=" * 72)
    print(f"  {'scenario':<22}{'fraud rate':>11}{'PR-AUC':>9}{'recall@' + str(args.threshold):>12}")
    for name, df in scenarios.items():
        scores = model.predict_proba(df[FEATURES])[:, 1]
        y = df[LABEL].to_numpy()
        recall = recall_score(y, scores >= args.threshold)
        print(f"  {name:<22}{y.mean():>11.3%}{average_precision_score(y, scores):>9.3f}{recall:>12.2f}")

    print("\n" + "=" * 72)
    print("3) EMBEDDING DRIFT — what are users asking the docs-assistant?")
    print("=" * 72)
    embedder = HashEmbedder()
    chunks = load_handbook(REPO_ROOT / "datasets" / "handbook")
    doc_vecs = embedder.embed([f"{c.title} {c.text}" for c in chunks])
    for label, path in (("week 37", QUERIES / "queries_week_37.txt"), ("week 45", QUERIES / "queries_week_45.txt")):
        queries = read_queries(path)
        q_vecs = embedder.embed(queries)
        best = (q_vecs @ doc_vecs.T).max(axis=1)  # similarity to the closest handbook chunk
        print(f"  {label}: mean best-match similarity = {best.mean():.2f}   "
              f"out-of-coverage (< {args.coverage}) = {(best < args.coverage).mean():.0%}")
    week_a = read_queries(QUERIES / "queries_week_37.txt")
    week_b = read_queries(QUERIES / "queries_week_45.txt")
    dist = centroid_cosine_distance(embedder.embed(week_a), embedder.embed(week_b))
    print(f"  centroid cosine distance week 37 → week 45 = {dist:.2f}")
    print(f"  emerging terms in week 45: {', '.join(emerging_terms(week_a, week_b))}")
    print("\n  Read: users now ask about things the handbook does not cover. That is a")
    print("  content gap (write docs) or a scope decision (refuse politely), not a model bug.")


def emerging_terms(old: list[str], new: list[str], top: int = 5) -> list[str]:
    """Words that are frequent in the new queries but absent from the old ones."""
    old_vocab = {t for q in old for t in content_tokens(q)}
    counts = Counter(t for q in new for t in content_tokens(q) if t not in old_vocab)
    return [f"{t} ×{n}" for t, n in counts.most_common(top)]


if __name__ == "__main__":
    main()
