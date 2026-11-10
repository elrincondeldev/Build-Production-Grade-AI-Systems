# Reproducibility record · fraud-classifier

> Fill this in for your `@champion` model (📖 [lesson 2.6](../06-experiment-tracking-and-reproducibility.md)). Everything below must come from MLflow or from git, **not from memory**. If you can't fill a field, that's the finding: fix the pipeline so it's logged automatically.

## Identity

| Field | Value | Where to find it |
|---|---|---|
| Registered model / version | `fraud-classifier` v__ | MLflow → Models |
| Aliases at time of writing | `@champion` | `uv run python -m pipelines.registry` |
| MLflow run ID | | Model version page → Source run |
| Date trained | | Run page |

## The checklist

| ✔ | Item | Value | MLflow location |
|---|---|---|---|
| ☐ | Code commit | | tag `git_commit` |
| ☐ | Working tree clean? | | tag `git_dirty` (must be `false` for a production model) |
| ☐ | Raw data digest (sha256) | | tag `raw_file_sha256` |
| ☐ | Validated data digest | | tag `validated_data_sha256` |
| ☐ | Data recipe | `datasets/fraud/generate.py --rows ___ --seed ___ --scenario baseline` | `lineage.json` → `generator` |
| ☐ | Environment lock (uv.lock sha256) | | tag `uv_lock_sha256` |
| ☐ | Seed(s) | | param `seed` |
| ☐ | Features used | | param `features` |
| ☐ | Hyperparameters | | params `learning_rate`, `max_depth`, `max_iter`, `l2_regularization` |
| ☐ | Split | temporal 70/15/15 | `lineage.json` → `split` |
| ☐ | Command | `uv run python -m pipelines.train --rows ___ --seed ___ --trials ___` | params `rows`, `seed`, `trials` |
| ☐ | Artifact link | `models:/fraud-classifier/__` | Run → Artifacts → `model` |

## Metrics

| Metric | Value |
|---|---|
| best_val_pr_auc | |
| test_pr_auc | |
| test_roc_auc | |
| test_base_rate | |

## Rebuild test

1. `git checkout <commit>` (or confirm you're on it).
2. Confirm `sha256sum uv.lock` (or `shasum -a 256 uv.lock` on macOS) matches `uv_lock_sha256`, then `uv sync --frozen`.
3. Run the command above.
4. Compare:

| | Original run | Rebuild | Match? |
|---|---|---|---|
| validated_data_sha256 | | | |
| best params | | | |
| test_pr_auc | | | |

## Reflection (2–3 sentences)

What would break this record in a real company (data in a warehouse instead of a generator, GPU training, a shared MLflow server)? What would you add?
