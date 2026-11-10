import numpy as np

from kestrel_fraud.costs import CostModel, best_threshold, expected_cost, sweep


def test_expected_cost_counts_each_outcome():
    y = np.array([1, 1, 0, 0])
    scores = np.array([0.9, 0.2, 0.8, 0.1])
    amounts = np.array([100.0, 50.0, 20.0, 30.0])
    costs = CostModel(review_cost=5, friction_cost=3, loss_multiplier=1)
    # threshold 0.5: flag txn 0 (fraud caught) and txn 2 (false alarm); miss txn 1 (€50)
    assert expected_cost(y, scores, amounts, 0.5, costs) == 5 * 2 + 3 * 1 + 50


def test_sweep_picks_known_optimum_on_toy_case():
    # One €1,000 fraud scored 0.3 and four legit transactions scored 0.4–0.7.
    y = np.array([1, 0, 0, 0, 0])
    scores = np.array([0.3, 0.4, 0.5, 0.6, 0.7])
    amounts = np.array([1000.0, 10, 10, 10, 10])
    costs = CostModel(review_cost=5, friction_cost=3)
    table = sweep(y, scores, amounts, costs, thresholds=np.array([0.25, 0.35, 0.45, 0.55, 0.65, 0.75]))
    # Flagging everything (t=0.25) costs 5·5 + 3·4 = 37 € and catches the €1,000 fraud.
    # Any higher threshold misses it and costs ≥ €1,000.
    assert best_threshold(table) == 0.25
    assert table.loc[table.threshold == 0.25, "cost"].item() == 37


def test_cheap_fraud_means_higher_threshold():
    # If missed fraud is cheap (€2), the best policy is to flag nothing.
    y = np.array([1, 0, 0])
    scores = np.array([0.9, 0.8, 0.1])
    amounts = np.array([2.0, 10, 10])
    table = sweep(y, scores, amounts, CostModel(), thresholds=np.array([0.05, 0.5, 0.95]))
    assert best_threshold(table) == 0.95
