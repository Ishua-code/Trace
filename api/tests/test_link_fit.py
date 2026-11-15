import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest

np = pytest.importorskip("numpy")

from app.engine.features import ALL_FEATURES, STRUCTURAL_FEATURES, FeatureIndex
from app.engine.logreg import fit_logistic, predict_proba

from eval.fit_weights import best_threshold, dev_pairs, fit_for_features
from seed.generate import generate


def test_logistic_recovers_a_linear_rule():
    rng = np.random.default_rng(0)
    X = rng.random((400, 3))
    y = (X[:, 0] + 0.5 * X[:, 1] > 0.9).astype(float)
    bias, w = fit_logistic(X, y, l2=0.1)
    acc = np.mean((predict_proba(X, bias, w) >= 0.5) == (y == 1))
    assert acc > 0.9 and w[0] > 0 and w[1] > 0 and abs(w[2]) < w[0]


def test_logistic_needs_both_classes():
    with pytest.raises(ValueError):
        fit_logistic(np.zeros((5, 2)), np.ones(5))


def test_best_threshold():
    t, stats = best_threshold(np.array([0.9, 0.8, 0.2, 0.1]), np.array([1.0, 1.0, 0.0, 0.0]))
    assert 0.2 < t <= 0.8 and stats["f1"] == pytest.approx(1.0)


@pytest.fixture(scope="module")
def data():
    return generate(42)


def test_dev_pairs_use_only_dev_ncs(data):
    gt = data["ground_truth"]
    pairs, y = dev_pairs(data)
    assert all(gt["splits"][i] == "dev" for p in pairs for i in p)
    expected = sum(1 for a, b in gt["true_pairs"]
                   if gt["splits"][a] == "dev" and gt["splits"][b] == "dev")
    assert int(y.sum()) == expected > 0
    assert not ({"NC-0412", "NC-0377", "NC-0390", "NC-0361"} & {i for p in pairs for i in p})


def test_fit_runs_for_each_feature_set(data):
    index = FeatureIndex(data["ncs"])
    for names in (ALL_FEATURES, STRUCTURAL_FEATURES):
        fw = fit_for_features(data, names, index=index)
        assert set(fw.weights) == set(names)
        assert all(np.isfinite(v) for v in fw.weights.values()) and np.isfinite(fw.bias)
        assert 0 < fw.threshold < 1
        assert fw.meta["trained_on_split"] == "dev" and "golden" in fw.meta["excluded_splits"]