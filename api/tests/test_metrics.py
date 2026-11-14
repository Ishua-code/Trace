import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest
from eval.metrics import (
    average_precision,
    log_loss,
    operating_point,
    per_nc_report,
    roc_auc,
    select_threshold,
)

SCORES = np.array([0.9, 0.8, 0.7, 0.6])
LABELS = np.array([1, 0, 1, 0])


def test_average_precision_hand_computed():
    assert average_precision(SCORES, LABELS) == pytest.approx(0.5 * 1.0 + 0.5 * (2 / 3))


def test_ties_do_not_depend_on_order():
    flat = np.full(4, 0.5)
    assert average_precision(flat, LABELS) == pytest.approx(0.5)
    assert average_precision(flat, LABELS[::-1]) == pytest.approx(0.5)
    assert roc_auc(flat, LABELS) == pytest.approx(0.5)


def test_roc_auc_hand_computed():
    assert roc_auc(SCORES, LABELS) == pytest.approx(0.75)
    assert roc_auc(-SCORES, LABELS) == pytest.approx(0.25)


def test_perfect_and_random_rankings():
    y = np.array([1, 1, 0, 0, 0, 0])
    assert average_precision(np.array([6, 5, 4, 3, 2, 1.0]), y) == pytest.approx(1.0)
    assert roc_auc(np.array([6, 5, 4, 3, 2, 1.0]), y) == pytest.approx(1.0)


def test_needs_both_classes():
    with pytest.raises(ValueError):
        average_precision(np.array([0.1, 0.2]), np.array([1, 1]))
    with pytest.raises(ValueError):
        roc_auc(np.array([0.1, 0.2]), np.array([0, 0]))


def test_log_loss():
    assert log_loss(np.array([0.9, 0.1]), np.array([1, 0])) == pytest.approx(-np.log(0.9))
    assert np.isfinite(log_loss(np.array([1.0, 0.0]), np.array([0, 1])))   # clipped, no inf


def test_operating_point():
    op = operating_point(SCORES, LABELS, 0.75)
    assert (op["tp"], op["fp"], op["fn"], op["n_flagged"]) == (1, 1, 1, 2)
    assert op["precision"] == pytest.approx(0.5) and op["recall"] == pytest.approx(0.5)
    assert operating_point(SCORES, LABELS, 2.0)["f1"] == 0.0


def test_select_threshold_toy():
    r = select_threshold(np.array([0.9, 0.8, 0.2, 0.1]), np.array([1, 1, 0, 0]))
    assert r["f1"] == pytest.approx(1.0) and 0.2 < r["threshold"] <= 0.8


def test_select_threshold_is_not_capped_at_099():
    s = np.array([0.99999, 0.9999, 0.999, 0.9, 0.5, 0.4])
    y = np.array([1, 1, 0, 0, 0, 0])
    r = select_threshold(s, y)
    assert r["threshold"] > 0.99 and r["f1"] == pytest.approx(1.0)


def test_select_threshold_takes_the_middle_of_the_plateau():
    # F1 is 1.0 for any cut in (0.4, 0.9]; the rule picks the middle of that gap (logit space)
    s = np.array([0.95, 0.9, 0.4, 0.35, 0.05])
    y = np.array([1, 1, 0, 0, 0])
    r = select_threshold(s, y, plateau=0.01)
    assert r["plateau_low"] == pytest.approx(0.4) and r["plateau_high"] == pytest.approx(0.9)
    assert 0.4 < r["threshold"] < 0.9
    assert r["f1"] == pytest.approx(1.0) and r["best_threshold"] == pytest.approx(0.9)


def test_select_threshold_survives_float_roundtrip_at_the_top():
    s = np.array([0.9999, 0.9999999, 0.5, 0.2])
    y = np.array([1, 1, 0, 0])
    r = select_threshold(s, y)
    assert r["f1"] == pytest.approx(1.0) and r["recall"] == pytest.approx(1.0)


def test_select_threshold_wide_plateau_uses_the_whole_run():
    # with a loose tolerance several thresholds count as "best"; the choice lies in the gap
    # below the whole run, not at its edge
    s = np.array([0.9, 0.8, 0.7, 0.6, 0.2, 0.1])
    y = np.array([1, 1, 1, 0, 1, 0])
    r = select_threshold(s, y, plateau=0.2)
    assert r["plateau_low"] < r["threshold"] <= r["plateau_high"]
    assert r["f1"] >= 0.8 * r["best_f1"]


def _toy():
    # NCs 0..3; only 0-1 are a true pair
    S = np.array([
        [0.0, 0.9, 0.5, 0.1],
        [0.9, 0.0, 0.4, 0.2],
        [0.5, 0.4, 0.0, 0.3],
        [0.1, 0.2, 0.3, 0.0],
    ])
    Y = np.zeros((4, 4), dtype=bool)
    Y[0, 1] = Y[1, 0] = True
    return S, Y


def test_per_nc_report_hand_computed():
    S, Y = _toy()
    r = per_nc_report(S, Y, ks=(1, 3), threshold=0.45)
    assert r["n_queries_with_mates"] == 2 and r["n_queries_without_mates"] == 2
    assert r["precision_at_1"] == 1.0 and r["recall_at_1"] == 1.0 and r["hit_at_1"] == 1.0
    assert r["precision_at_3"] == pytest.approx(1 / 3) and r["recall_at_3"] == 1.0
    assert r["mrr"] == 1.0
    assert r["mean_links_no_mate_queries"] == pytest.approx(0.5)      # NC 2 sees NC 0, NC 3 none
    assert r["frac_no_mate_queries_alerted"] == pytest.approx(0.5)
    assert r["precision_at_threshold"] == pytest.approx(0.75)    # NC 0: 1 of 2, NC 1: 1 of 1
    assert r["recall_at_threshold"] == 1.0 and r["frac_mate_queries_with_any_link"] == 1.0


def test_per_nc_ties_are_broken_against_the_true_mate():
    S = np.array([[0.0, 0.5, 0.5], [0.5, 0.0, 0.1], [0.5, 0.1, 0.0]])
    Y = np.zeros((3, 3), dtype=bool)
    Y[0, 1] = Y[1, 0] = True
    r = per_nc_report(S, Y, ks=(1,))
    assert r["precision_at_1"] == pytest.approx(0.5)       # NC 0: tie loses; NC 1: wins
    assert r["mrr"] == pytest.approx((0.5 + 1.0) / 2)


def test_per_nc_report_does_not_mutate_input():
    S, Y = _toy()
    before = S.copy()
    per_nc_report(S, Y)
    assert np.array_equal(S, before)