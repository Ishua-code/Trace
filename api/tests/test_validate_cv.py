import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pytest
from app.engine.features import STRUCTURAL_FEATURES

from eval import validate_cv
from eval.cv import build_dev_pairs, make_folds
from seed.generate import generate

K = 5


@pytest.fixture(scope="module")
def data():
    return generate(42)


@pytest.fixture(scope="module")
def setup(data):
    dp = build_dev_pairs(data)
    return dp, make_folds(dp.group_of, dp.positives_by_group, K, 42)


def _run(data, setup, nonneg):
    """Run validate_model once, recording every fit, IDF fit and index it performs."""
    _, fold_of = setup
    rec = {"ordinary": 0, "nonneg": 0, "weights": [], "idf_ids": [], "index_ids": []}
    real_ord, real_nn = validate_cv.fit_logistic, validate_cv.fit_logistic_nonneg
    real_idf, real_index = validate_cv.fit_idf, validate_cv.FeatureIndex

    def ordinary(*args, **kwargs):
        rec["ordinary"] += 1
        bias, weights = real_ord(*args, **kwargs)
        rec["weights"].append(np.array(weights))
        return bias, weights

    def nonneg_fit(*args, **kwargs):
        rec["nonneg"] += 1
        out = real_nn(*args, **kwargs)
        rec["weights"].append(np.array(out[1]))
        return out

    def idf(ncs):
        ncs = list(ncs)
        rec["idf_ids"].append({nc.id for nc in ncs})
        return real_idf(ncs)

    def index(ncs, **kwargs):
        ncs = list(ncs)
        rec["index_ids"].append({nc.id for nc in ncs})
        return real_index(ncs, **kwargs)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(validate_cv, "fit_logistic", ordinary)
        mp.setattr(validate_cv, "fit_logistic_nonneg", nonneg_fit)
        mp.setattr(validate_cv, "fit_idf", idf)
        mp.setattr(validate_cv, "FeatureIndex", index)
        result = validate_cv.validate_model(data, STRUCTURAL_FEATURES, fold_of, K, 1.0, nonneg)
    return result, rec


@pytest.fixture(scope="module")
def ordinary_run(data, setup):
    return _run(data, setup, nonneg=False)


@pytest.fixture(scope="module")
def nonneg_run(data, setup):
    return _run(data, setup, nonneg=True)


def test_nonneg_mode_uses_only_the_nonneg_solver(nonneg_run):
    result, rec = nonneg_run
    assert rec["nonneg"] == K and rec["ordinary"] == 0  # the ordinary fit must not overwrite it
    assert all(np.all(w >= 0.0) for w in rec["weights"])
    assert any(np.any(w == 0.0) for w in rec["weights"])  # the constraint really binds
    assert len(result["kkt_checks_by_fold"]) == K
    assert all(k["max"] < 1e-6 for k in result["kkt_checks_by_fold"])


def test_ordinary_mode_uses_only_the_ordinary_solver(ordinary_run):
    result, rec = ordinary_run
    assert rec["ordinary"] == K and rec["nonneg"] == 0
    assert any(np.any(w < 0.0) for w in rec["weights"])  # unconstrained fit goes negative
    assert result["kkt_checks_by_fold"] == []


def test_the_two_modes_give_different_scores(ordinary_run, nonneg_run):
    assert abs(ordinary_run[0]["average_precision"] - nonneg_run[0]["average_precision"]) > 1e-3
    assert ordinary_run[0]["threshold"] != nonneg_run[0]["threshold"]


@pytest.mark.parametrize("which", ["ordinary", "nonneg"])
def test_fold_idf_uses_only_training_fold_dev_ncs(data, setup, request, which):
    dp, fold_of = setup
    _, rec = request.getfixturevalue(f"{which}_run")
    splits = data["ground_truth"]["splits"]
    dev_ids = {i for i, s in splits.items() if s == "dev"}
    assert dev_ids == set(dp.ids)
    expected = [{i for i in dp.ids if fold_of[i] != f} for f in range(K)]
    assert rec["idf_ids"] == expected  # fold f's IDF sees exactly the NCs outside fold f
    for ids in rec["idf_ids"]:
        assert ids <= dev_ids and not any(splits[i] != "dev" for i in ids)


@pytest.mark.parametrize("which", ["ordinary", "nonneg"])
def test_scoring_index_never_contains_test_or_golden_ncs(data, setup, request, which):
    dp, _ = setup
    _, rec = request.getfixturevalue(f"{which}_run")
    assert len(rec["index_ids"]) == K
    assert all(ids == set(dp.ids) for ids in rec["index_ids"])


def test_cli_nonneg_flag_runs_only_the_nonneg_model(monkeypatch, capsys):
    argv = ["validate_cv", "--features", "structural", "--nonneg", "--folds", "5", "--seed", "42"]
    monkeypatch.setattr(sys, "argv", argv)
    validate_cv.main()
    out = capsys.readouterr().out
    assert "NON-NEGATIVE LOGISTIC REGRESSION" in out and "ORDINARY" not in out