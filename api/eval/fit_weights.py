"""Fit TRACE link weights on the DEV split only and freeze them in engine/weights.json.

Never touches the test or golden splits. Run from the repo root:
    python -m eval.fit_weights
Dev metrics printed here are IN-SAMPLE (training data); honest numbers come from eval.run.
"""
from __future__ import annotations

import argparse
import itertools
import sys
from datetime import date
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
)
from app.engine.logreg import (
    fit_logistic,
    fit_logistic_nonneg,
    predict_proba,
)
from app.engine.scoring import WEIGHTS_PATH, FrozenWeights, save_weights
from app.engine.store import pair_key
from seed.generate import SEED_DEFAULT, generate

from eval.frozen_idf import dev_ids_digest, dev_ncs, fit_dev_idf

FEATURE_SETS = {"structural": STRUCTURAL_FEATURES, "text": TEXT_FEATURES, "both": ALL_FEATURES}


def dev_pairs(data):
    """All unordered pairs of DEV NCs; label 1 when planted ground truth says related."""
    gt = data["ground_truth"]
    dev_ids = sorted(i for i, s in gt["splits"].items() if s == "dev")
    true = {pair_key(a, b) for a, b in gt["true_pairs"]}
    pairs = list(itertools.combinations(dev_ids, 2))
    y = np.array([1.0 if p in true else 0.0 for p in pairs])
    return pairs, y



def best_threshold(p, y):
    """Threshold with the best F1 (ties go to the higher threshold)."""
    best_f1, best_t, best = -1.0, 0.5, {}
    for t in np.round(np.arange(0.05, 0.991, 0.01), 2):
        pred = p >= t
        tp = float(np.sum(pred & (y == 1)))
        fp = float(np.sum(pred & (y == 0)))
        fn = float(np.sum(~pred & (y == 1)))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        if f1 >= best_f1:
            best_f1, best_t = f1, float(t)
            best = {"precision": prec, "recall": rec, "f1": f1}
    return best_t, best


def fit_for_features(
    data, feature_names, l2=1.0, index=None, nonneg=False, threshold_override=None
):
    dev_idf = fit_dev_idf(data)
    index = index or FeatureIndex(data["ncs"], idf=dev_idf)  # IDF uses text only, no labels
    pairs, y = dev_pairs(data)
    X = index.feature_matrix(pairs, feature_names)
    n_pos = float(y.sum())
    n_neg = len(y) - n_pos
    sw = np.where(y == 1, n_neg / n_pos, 1.0)  # balanced classes
    fit_info = None

    if nonneg:
        bias, w, fit_info = fit_logistic_nonneg(
            X, y, sw, l2=l2
        )
    else:
        bias, w = fit_logistic(X, y, sw, l2=l2)

    probabilities = predict_proba(X, bias, w)

    if threshold_override is None:
        threshold, stats = best_threshold(probabilities, y)
    else:
        if not 0.0 < threshold_override < 1.0:
            raise ValueError("threshold must be between 0 and 1")

        threshold = threshold_override
        pred = probabilities >= threshold
        tp = float(np.sum(pred & (y == 1)))
        fp = float(np.sum(pred & (y == 0)))
        fn = float(np.sum(~pred & (y == 1)))

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall else 0.0
        )
        stats = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    meta = {
        "trained_on_split": "dev",
        "excluded_splits": ["test", "golden"],
        "n_pairs": len(y),
        "n_positive": int(n_pos),
        "l2": l2,
        "class_weighting": "balanced",
        "seed": data["seed"],
        "fit_date": date.today().isoformat(),
        "dev_in_sample_precision": round(stats["precision"], 4),
        "dev_in_sample_recall": round(stats["recall"], 4),
        "dev_in_sample_f1": round(stats["f1"], 4),
        "score_note": "Relative link score, not a calibrated probability",
        "non_negative": nonneg,
        "dev_idf_sha256": dev_idf.digest,
        "dev_ids_sha256": dev_ids_digest(dev_ncs(data)),
        "kkt": fit_info["kkt"] if fit_info else None,
        "features": list(feature_names),
        "threshold_source": (
            "grouped_5_fold_oof" if threshold_override is not None else "in_sample"
        ),
    }

    return FrozenWeights(
        bias=bias,
        weights=dict(zip(feature_names, map(float, w))),
        threshold=threshold,
        meta=meta,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit TRACE link weights on the dev split")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    ap.add_argument("--features", choices=sorted(FEATURE_SETS), default="both")
    ap.add_argument("--l2", type=float, default=1.0)
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--nonneg",
        action="store_true",
        help="Constrain all feature weights to be non-negative",
    )
    args = ap.parse_args()

    fw = fit_for_features(
    generate(args.seed),
    FEATURE_SETS[args.features],
    l2=args.l2,
    nonneg=args.nonneg,
    threshold_override=args.threshold,
    )
    print(f"features={args.features}  bias={fw.bias:+.3f}  threshold={fw.threshold:.2f}")
    for name, w in sorted(fw.weights.items(), key=lambda kv: -abs(kv[1])):
        print(f"  {name:18s} {w:+.3f}")
    m = fw.meta
    print(f"dev pairs={m['n_pairs']} positives={m['n_positive']}  in-sample "
          f"P={m['dev_in_sample_precision']} R={m['dev_in_sample_recall']} "
          f"F1={m['dev_in_sample_f1']}")
    out = args.out or (str(WEIGHTS_PATH) if args.features == "both" else None)
    if out:
        all_weights = {name: 0.0 for name in ALL_FEATURES}
        all_weights.update(fw.weights)

        saved_fw = FrozenWeights(
            bias=fw.bias,
            weights=all_weights,
            threshold=fw.threshold,
            meta=fw.meta,
        )
        save_weights(saved_fw, out)
        print(f"wrote {out}")
    else:
        print("not saved (use --out to keep a copy)")


if __name__ == "__main__":
    main()