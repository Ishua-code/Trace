"""Leakage-safe grouped cross-validation for TRACE link scoring."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT))

import numpy as np
from app.engine.features import (
    ALL_FEATURES,
    STRUCTURAL_FEATURES,
    TEXT_FEATURES,
    FeatureIndex,
    fit_idf,
)
from app.engine.logreg import (
    fit_logistic,
    fit_logistic_nonneg,
    predict_proba,
)
from seed.generate import SEED_DEFAULT, generate

from eval.cv import build_dev_pairs, check_folds, fold_arrays, make_folds
from eval.frozen_idf import dev_ncs
from eval.metrics import (
    average_precision,
    log_loss,
    operating_point,
    per_nc_report,
    roc_auc,
    select_threshold,
)

FEATURE_SETS = {
    "structural": STRUCTURAL_FEATURES,
    "text": TEXT_FEATURES,
    "both": ALL_FEATURES,
}


def validate_model(data, feature_names, fold_of, k, l2, nonneg, return_scores=False):
    dp = build_dev_pairs(data)
    fa, fb = fold_arrays(dp.pairs, fold_of)

    dev_objects = dev_ncs(data)
    nc_by_id = {nc.id: nc for nc in dev_objects}
    dev_objects = [nc_by_id[nc_id] for nc_id in dp.ids]

    oof = np.full(len(dp.y), np.nan)
    kkt_values = []
    fold_log_factors = []

    # Directional retrieval scores: each query uses its own held-out fold model.
    n = len(dp.ids)
    pos = {nc_id: i for i, nc_id in enumerate(dp.ids)}

    ia = np.fromiter(
         (pos[a] for a, _ in dp.pairs), dtype=int, count=len(dp.pairs)
    )
    ib = np.fromiter(
         (pos[b] for _, b in dp.pairs), dtype=int, count=len(dp.pairs)
    )

    retrieval_S = np.full((n, n), -np.inf)
    retrieval_Y = np.zeros((n, n), dtype=bool)
    retrieval_Y[ia, ib] = dp.y == 1
    retrieval_Y[ib, ia] = dp.y == 1

    for f in range(k):
        # Training pairs must not contain either endpoint from this fold.
        train = (fa != f) & (fb != f)

        # Every pair is scored by the fold of its smaller NC ID.
        validation = fa == f

        training_ids = [
            nc_id for nc_id in dp.ids if fold_of[nc_id] != f
        ]
        training_ncs = [nc_by_id[nc_id] for nc_id in training_ids]

        if not np.any(train) or not np.any(validation):
            raise ValueError(f"Fold {f} has no training or validation pairs")

        # Crucial: fit IDF using training-fold NCs only.
        fold_idf = fit_idf(training_ncs)

        # Include DEV NCs for pair scoring, but never TEST/GOLDEN NCs.
        index = FeatureIndex(dev_objects, idf=fold_idf)
        X = index.feature_matrix(dp.pairs, feature_names)

        X_train = X[train]
        y_train = dp.y[train]

        n_pos = float(y_train.sum())
        n_neg = len(y_train) - n_pos

        if n_pos == 0 or n_neg == 0:
            raise ValueError(f"Fold {f} training data has only one class")

        fold_log_factors.append(float(np.log(n_neg / n_pos)))
        sample_weight = np.where(
            y_train == 1,
            n_neg / n_pos,
            1.0,
        )

        if nonneg:
            bias, weights, info = fit_logistic_nonneg(
                X_train,
                y_train,
                sample_weight,
                l2=l2,
            )
            kkt_values.append(info["kkt"])
        else:
            bias, weights = fit_logistic(
                X_train,
                y_train,
                sample_weight,
                l2=l2,
            )

        oof[validation] = predict_proba(
            X[validation],
            bias,
            weights,
        )
        # Score every candidate for queries belonging to this held-out fold.
        query_pairs = (fa == f) | (fb == f)
        query_rows = np.flatnonzero(query_pairs)

        query_scores = predict_proba(
            X[query_pairs],
            bias,
            weights,
        )

        left_query = fa[query_rows] == f
        right_query = fb[query_rows] == f

        # Direction: left NC is the query.
        rows = query_rows[left_query]
        retrieval_S[ia[rows], ib[rows]] = query_scores[left_query]

        # Direction: right NC is the query.
        rows = query_rows[right_query]
        retrieval_S[ib[rows], ia[rows]] = query_scores[right_query]

        print(
            f"  fold {f + 1}/{k}: "
            f"train_pairs={int(train.sum())}, "
            f"scored_pairs={int(validation.sum())}, "
            f"IDF_docs={fold_idf.n_docs}"
        )

    if np.isnan(oof).any():
        raise AssertionError("Some DEV pairs have no OOF prediction")

    # Select threshold only from out-of-fold DEV predictions.
    selected = select_threshold(oof, dp.y)
    threshold = selected["threshold"]
    op = operating_point(oof, dp.y, threshold)

    if np.isneginf(retrieval_S[~np.eye(n, dtype=bool)]).any():
        raise AssertionError("Some query-candidate retrieval scores are missing")

    retrieval = per_nc_report(
        retrieval_S,
        retrieval_Y,
        threshold=threshold,
    )
    result = {
        "threshold": threshold,
        "roc_auc": roc_auc(oof, dp.y),
        "average_precision": average_precision(oof, dp.y),
        "log_loss": log_loss(oof, dp.y),
        "precision": op["precision"],
        "recall": op["recall"],
        "f1": op["f1"],
        "n_flagged": op["n_flagged"],
        "tp": op["tp"],
        "fp": op["fp"],
        "fn": op["fn"],
        "precision_at_1": retrieval["precision_at_1"],
        "hit_at_3": retrieval["hit_at_3"],
        "mrr": retrieval["mrr"],
        "retrieval_queries_with_mates": retrieval["n_queries_with_mates"],
        "retrieval_queries_without_mates": retrieval["n_queries_without_mates"],
        "retrieval_precision_at_3": retrieval["precision_at_3"],
        "retrieval_recall_at_3": retrieval["recall_at_3"],
        "best_f1": selected["best_f1"],
        "kkt_checks_by_fold": kkt_values,
    }
    if return_scores:  # extra outputs for threshold freezing; the default result is unchanged
        result["oof_scores"] = oof
        result["labels"] = dp.y
        result["fold_log_factors"] = fold_log_factors
        result["n_dev_ncs"] = n
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Leakage-safe grouped CV for TRACE link scoring"
    )
    parser.add_argument("--seed", type=int, default=SEED_DEFAULT)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument(
        "--features",
        choices=sorted(FEATURE_SETS),
        default="both",
    )
    parser.add_argument("--l2", type=float, default=1.0)
    parser.add_argument(
        "--nonneg",
        action="store_true",
        help="run only the non-negative model (default: run ordinary and non-negative)",
    )
    args = parser.parse_args()

    data = generate(args.seed)
    dp = build_dev_pairs(data)

    fold_of = make_folds(
        dp.group_of,
        dp.positives_by_group,
        args.folds,
        args.seed,
    )
    check_folds(dp, fold_of, args.folds)

    print(f"DEV NCs: {len(dp.ids)}")
    print(f"DEV pairs: {len(dp.pairs)}")
    print(f"DEV positive pairs: {dp.n_positive}")
    print(f"Grouped folds: {args.folds}")
    print(f"Features: {args.features}")

    feature_names = FEATURE_SETS[args.features]

    for nonneg in (True,) if args.nonneg else (False, True):
        name = "NON-NEGATIVE" if nonneg else "ORDINARY"

        print(f"\n===== {name} LOGISTIC REGRESSION =====")

        result = validate_model(
            data,
            feature_names,
            fold_of,
            args.folds,
            args.l2,
            nonneg,
        )

        for key, value in result.items():
            if isinstance(value, float):
                print(f"{key:20s}: {value:.6f}")
            else:
                print(f"{key:20s}: {value}")

    print("\nCV complete. No production weights were modified.")


if __name__ == "__main__":
    main()