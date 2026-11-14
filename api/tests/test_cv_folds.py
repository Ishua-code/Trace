import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pytest
from eval.cv import (
    build_dev_pairs,
    check_folds,
    fold_arrays,
    make_folds,
    pair_matrices,
    run_oof,
)
from seed.generate import generate

K = 5
REPEAT_SEEDS = (0, 1, 2)
GOLDEN = {"NC-0361", "NC-0377", "NC-0390", "NC-0412", "NC-0401", "NC-0408"}


@pytest.fixture(scope="module")
def data():
    return generate(42)


@pytest.fixture(scope="module")
def dp(data):
    return build_dev_pairs(data)


def test_only_dev_ncs_are_used(data, dp):
    splits = data["ground_truth"]["splits"]
    assert all(splits[i] == "dev" for i in dp.ids)
    assert not (GOLDEN & set(dp.ids))
    assert not any(a in GOLDEN or b in GOLDEN for a, b in dp.pairs)
    test_ids = {i for i, s in splits.items() if s == "test"}
    assert not (test_ids & set(dp.ids))


def test_pairs_are_ordered_unique_and_complete(dp):
    n = len(dp.ids)
    assert len(dp.pairs) == n * (n - 1) // 2 == len(set(dp.pairs))
    assert all(a < b for a, b in dp.pairs)
    assert dp.y.sum() == dp.n_positive > 0


def test_real_seed_counts(dp):
    # numbers reported from the dev diagnostics run on seed 42
    assert len(dp.pairs) == 87990 and dp.n_positive == 122


def test_matches_existing_dev_pairs(data, dp):
    from eval.fit_weights import dev_pairs

    pairs, y = dev_pairs(data)
    assert pairs == dp.pairs and np.array_equal(y, dp.y)


def test_groups_cover_dev_and_keep_clusters_together(data, dp):
    assert set(dp.group_of) == set(dp.ids)
    for c in data["ground_truth"]["clusters"]:
        if c["split"] == "dev":
            assert {dp.group_of[m] for m in c["members"]} == {c["id"]}
    assert sum(dp.positives_by_group.values()) == dp.n_positive


@pytest.mark.parametrize("seed", REPEAT_SEEDS)
def test_fold_guarantees_hold_for_every_repeat(dp, seed):
    fold_of = make_folds(dp.group_of, dp.positives_by_group, K, seed)
    assert set(fold_of) == set(dp.ids) and set(fold_of.values()) == set(range(K))
    check_folds(dp, fold_of, K)                      # raises on any leakage


@pytest.mark.parametrize("seed", REPEAT_SEEDS)
def test_each_pair_scored_once_and_never_trained_on_its_heldout_ncs(dp, seed):
    fold_of = make_folds(dp.group_of, dp.positives_by_group, K, seed)
    fa, fb = fold_arrays(dp.pairs, fold_of)
    scored = sum((fa == f).astype(int) for f in range(K))
    assert np.all(scored == 1)                                   # exactly once per repeat
    for f in range(K):
        train = (fa != f) & (fb != f)
        held_ncs = {nc for nc, g in fold_of.items() if g == f}
        held_groups = {dp.group_of[nc] for nc in held_ncs}
        idx = np.where(train)[0]
        used = {dp.pairs[i][0] for i in idx} | {dp.pairs[i][1] for i in idx}
        assert not (used & held_ncs)                              # no held-out NC in training
        assert not ({dp.group_of[nc] for nc in used} & held_groups)   # nor its cluster or decoys
        assert np.all(fa[dp.y == 1] == fb[dp.y == 1])             # positives held out together


def test_repeats_differ_but_each_is_deterministic(dp):
    a = make_folds(dp.group_of, dp.positives_by_group, K, 0)
    assert a == make_folds(dp.group_of, dp.positives_by_group, K, 0)
    assert a != make_folds(dp.group_of, dp.positives_by_group, K, 1)


def test_positives_are_balanced_across_folds(dp):
    fold_of = make_folds(dp.group_of, dp.positives_by_group, K, 0)
    fa, _ = fold_arrays(dp.pairs, fold_of)
    per_fold = [int(dp.y[fa == f].sum()) for f in range(K)]
    assert min(per_fold) > 0 and max(per_fold) <= 2 * dp.n_positive / K


def test_check_folds_catches_a_broken_assignment(dp):
    fold_of = make_folds(dp.group_of, dp.positives_by_group, K, 0)
    cluster_nc = next(nc for nc, g in dp.group_of.items() if g in dp.positives_by_group)
    broken = dict(fold_of)
    broken[cluster_nc] = (fold_of[cluster_nc] + 1) % K          # split a cluster across folds
    with pytest.raises(AssertionError):
        check_folds(dp, broken, K)


def test_run_oof_scores_every_pair_with_the_right_model(dp):
    fold_of = make_folds(dp.group_of, dp.positives_by_group, K, 0)
    fa, fb = fold_arrays(dp.pairs, fold_of)
    X = np.arange(len(dp.pairs), dtype=float).reshape(-1, 1)
    calls = []

    def fit(Xtr, ytr):
        calls.append(len(ytr))
        tag = float(len(calls))
        return lambda Xte: np.full(len(Xte), tag)

    scores, models = run_oof(X, dp.y, fa, fb, K, fit)
    assert len(models) == K and not np.isnan(scores).any()
    for f in range(K):
        assert np.all(scores[fa == f] == f + 1)                  # scored by fold f's own model


def test_pair_matrices_roundtrip(dp):
    values = np.arange(len(dp.pairs), dtype=float)
    S, Y = pair_matrices(dp.ids, dp.pairs, values, dp.y)
    assert np.allclose(S, S.T) and np.array_equal(Y, Y.T)
    assert int(Y.sum()) == 2 * dp.n_positive
    i, j = dp.ids.index(dp.pairs[10][0]), dp.ids.index(dp.pairs[10][1])
    assert S[i, j] == 10.0 and S[j, i] == 10.0