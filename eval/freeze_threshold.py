"""Choose the link threshold from DEV out-of-fold scores with a pre-committed recall target.

The weights are NOT changed. Only `threshold` and a few meta fields are rewritten, and only with
--write. The rule uses DEV pairs only (grouped 5-fold OOF); TEST and GOLDEN are never read.

    python -m eval.freeze_threshold --recall-target 0.7            # dry run, prints the numbers
    python -m eval.freeze_threshold --recall-target 0.7 --write    # updates weights.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT))

from app.engine.scoring import WEIGHTS_PATH

from eval.cv import build_dev_pairs, check_folds, make_folds
from eval.metrics import threshold_for_recall
from eval.validate_cv import validate_model
from seed.generate import generate

THRESHOLD_SOURCE = "grouped_5_fold_oof_recall_target"


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def compute_threshold(weights: dict, recall_target: float, folds: int = 5) -> dict:
    """Threshold for the model described by a weights.json payload, from DEV OOF scores only."""
    meta = weights["meta"]
    if meta.get("class_weighting") != "balanced":
        raise ValueError("only balanced class weighting is supported")
    data = generate(meta["seed"])
    dp = build_dev_pairs(data)
    fold_of = make_folds(dp.group_of, dp.positives_by_group, folds, meta["seed"])
    check_folds(dp, fold_of, folds)
    result = validate_model(
        data, meta["features"], fold_of, folds, meta["l2"], bool(meta["non_negative"]),
        return_scores=True,
    )
    picked = threshold_for_recall(result["oof_scores"], result["labels"], recall_target)
    # Fold models were trained on fewer pairs than the final model, so their balanced-weight
    # scores sit at a slightly different level. Shift by the difference in log class ratio.
    full_log_factor = math.log((meta["n_pairs"] - meta["n_positive"]) / meta["n_positive"])
    shift = full_log_factor - sum(result["fold_log_factors"]) / len(result["fold_log_factors"])
    threshold = round(_sigmoid(_logit(picked["threshold"]) + shift), 4)
    return {
        "threshold": threshold,
        "recall_target": recall_target,
        "oof_threshold": picked["threshold"],
        "oof_recall": picked["recall"],
        "oof_precision": picked["precision"],
        "oof_flagged_pairs": picked["n_flagged"],
        "oof_links_per_nc": 2.0 * picked["n_flagged"] / result["n_dev_ncs"],
        "scale_shift_logit": shift,
    }


def apply_threshold(weights: dict, found: dict) -> dict:
    """Return a copy of the payload with the new threshold; weights and bias are untouched."""
    out = json.loads(json.dumps(weights))
    out["threshold"] = found["threshold"]
    out["meta"].update(
        {
            "threshold_source": THRESHOLD_SOURCE,
            "threshold_recall_target": found["recall_target"],
            "threshold_oof_recall": round(found["oof_recall"], 4),
            "threshold_oof_precision": round(found["oof_precision"], 4),
            "threshold_oof_links_per_nc": round(found["oof_links_per_nc"], 3),
            "threshold_scale_shift_logit": round(found["scale_shift_logit"], 4),
        }
    )
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Freeze the link threshold from DEV OOF scores")
    parser.add_argument("--recall-target", type=float, required=True)
    parser.add_argument("--weights", default=str(WEIGHTS_PATH))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--write", action="store_true", help="rewrite the weights file")
    args = parser.parse_args(argv)

    path = Path(args.weights)
    weights = json.loads(path.read_text(encoding="utf-8"))
    found = compute_threshold(weights, args.recall_target, args.folds)
    print(f"old threshold: {weights['threshold']}  ({weights['meta'].get('threshold_source')})")
    for key, value in found.items():
        print(f"{key:20s}: {value:.6f}" if isinstance(value, float) else f"{key:20s}: {value}")
    if args.write:
        path.write_text(json.dumps(apply_threshold(weights, found), indent=2), encoding="utf-8")
        print(f"wrote {path} (weights and bias unchanged)")
    else:
        print("dry run: nothing written (use --write)")


if __name__ == "__main__":
    main()