import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pytest
from app.engine.scoring import WEIGHTS_PATH

from eval.freeze_threshold import THRESHOLD_SOURCE, apply_threshold, compute_threshold
from eval.metrics import operating_point, threshold_for_recall

S = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
Y = np.array([1, 0, 1, 0, 1])  # recall by threshold: 0.9 -> 1/3, 0.7 -> 2/3, 0.5 -> 1


# ---------------------------------------------------------------- the rule itself
def test_picks_the_highest_threshold_that_reaches_the_target():
    r = threshold_for_recall(S, Y, 0.6)
    assert r["score_at_target"] == pytest.approx(0.7) and r["next_lower_score"] == pytest.approx(0.6)
    assert 0.6 < r["threshold"] <= 0.7  # the middle of the gap, not an observed score
    assert r["recall"] == pytest.approx(2 / 3) and r["n_flagged"] == 3
    assert r["precision"] == pytest.approx(2 / 3)


def test_target_of_one_flags_down_to_the_last_positive():
    r = threshold_for_recall(S, Y, 1.0)
    assert r["recall"] == 1.0 and r["threshold"] == pytest.approx(0.5) and r["n_flagged"] == 5


def test_low_target_flags_only_the_top():
    r = threshold_for_recall(S, Y, 0.3)
    assert 0.8 < r["threshold"] <= 0.9 and r["n_flagged"] == 1 and r["recall"] == pytest.approx(1 / 3)


def test_ties_are_flagged_together():
    r = threshold_for_recall(np.array([0.5, 0.5, 0.4]), np.array([1, 0, 1]), 0.5)
    assert r["n_flagged"] == 2 and r["recall"] == pytest.approx(0.5)


def test_recall_is_really_reached_at_the_returned_threshold():
    rng = np.random.default_rng(3)
    y = (rng.random(4000) < 0.03).astype(float)
    s = 1 / (1 + np.exp(-(rng.normal(size=4000) + 2.5 * y - 3)))
    for target in (0.3, 0.5, 0.7, 0.9, 1.0):
        r = threshold_for_recall(s, y, target)
        assert operating_point(s, y, r["threshold"])["recall"] >= target - 1e-9
        assert r["recall"] >= target - 1e-9


def test_survives_float_roundtrip_near_one():
    r = threshold_for_recall(np.array([0.9999999, 0.5]), np.array([1, 0]), 1.0)
    assert operating_point(np.array([0.9999999, 0.5]), np.array([1, 0]), r["threshold"])["recall"] == 1.0


@pytest.mark.parametrize("target", [0.0, -0.1, 1.2])
def test_rejects_invalid_targets(target):
    with pytest.raises(ValueError):
        threshold_for_recall(S, Y, target)


def test_needs_both_classes():
    with pytest.raises(ValueError):
        threshold_for_recall(S, np.ones(5), 0.5)


# ---------------------------------------------------------------- freezing into weights.json
@pytest.fixture(scope="module")
def weights():
    return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))


def test_apply_changes_only_the_threshold_and_its_meta(weights):
    found = {"threshold": 0.5, "recall_target": 0.7, "oof_recall": 0.71, "oof_precision": 0.1,
             "oof_links_per_nc": 3.0, "scale_shift_logit": 0.2}
    out = apply_threshold(weights, found)
    assert out["bias"] == weights["bias"] and out["weights"] == weights["weights"]
    assert out["threshold"] == 0.5 and out["meta"]["threshold_source"] == THRESHOLD_SOURCE
    assert weights["threshold"] != 0.5  # the input was not modified
    for key in ("features", "l2", "seed", "trained_on_split", "excluded_splits"):
        assert out["meta"][key] == weights["meta"][key]


def test_frozen_threshold_is_reproducible_from_dev_oof_scores(weights):
    meta = weights["meta"]
    assert meta["threshold_source"] == THRESHOLD_SOURCE
    assert meta["trained_on_split"] == "dev" and {"test", "golden"} <= set(meta["excluded_splits"])
    found = compute_threshold(weights, meta["threshold_recall_target"])
    assert found["threshold"] == weights["threshold"]  # same rule, same DEV data, same number
    assert found["oof_recall"] >= meta["threshold_recall_target"] - 1e-9
    assert round(found["oof_precision"], 4) == meta["threshold_oof_precision"]