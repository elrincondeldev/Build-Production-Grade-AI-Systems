import pytest
from sklearn.metrics import cohen_kappa_score

from evals.judge import FakeJudge
from evals.judge_calibration import calibrate, cohen_kappa, load_rows


def test_kappa_matches_sklearn():
    a = [True, True, False, True, False, False, True, True]
    b = [True, False, False, True, False, True, True, True]
    assert cohen_kappa(a, b) == pytest.approx(cohen_kappa_score(a, b))


def test_kappa_perfect_and_chance():
    assert cohen_kappa([True, False, True], [True, False, True]) == 1.0
    # A judge that always says "pass" agrees often by luck but has zero skill.
    human = [True] * 9 + [False]
    always_pass = [True] * 10
    assert cohen_kappa(human, always_pass) == 0.0


def test_fake_judge_on_human_labels_is_imperfect_but_useful():
    report = calibrate(FakeJudge(), load_rows())
    assert report["n"] == 20
    assert 0.2 < report["kappa"] < 0.8  # some skill, far from trustworthy alone
    ids = {d["id"] for d in report["disagreements"]}
    assert "h03" in ids  # same words, opposite meaning: word overlap can't see it
