"""NC-grouped cross-validation for pairwise link scoring. numpy + stdlib only.

Why NC-level grouping: a pair (a, b) shares NCs with thousands of other pairs, so splitting
pairs at random would let the same NC sit in both training and validation.

Groups: each DEV cluster is one group; each DEV decoy joins the DEV cluster it resembles;
every other DEV NC is its own group. TEST and GOLDEN NCs are never read here.

Scoring rule: every dev pair is scored exactly once, by the fold of its smaller NC id. That
keeps the real base rate (scoring only in-fold pairs would inflate precision about 25x).
A positive pair lies inside one cluster, so both its NCs are always held out together.
"""
from __future__ import annotations

import itertools
import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


def _key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


@dataclass(frozen=True)
class DevPairs:
    ids: list[str]
    pairs: list[tuple[str, str]]          # (a, b) with a < b
    y: np.ndarray
    group_of: dict[str, str]
    positives_by_group: dict[str, int]

    @property
    def n_positive(self) -> int:
        return int(self.y.sum())


def build_dev_pairs(data: dict) -> DevPairs:
    gt = data["ground_truth"]
    ids = sorted(i for i, s in gt["splits"].items() if s == "dev")
    dev = set(ids)
    dev_clusters = {c["id"]: c for c in gt["clusters"] if c["split"] == "dev"}

    group_of: dict[str, str] = {}
    for cid, c in dev_clusters.items():
        for m in c["members"]:
            if m not in dev:
                raise AssertionError(f"dev cluster {cid} has a non-dev member")
            group_of[m] = cid
    for i in ids:
        if i in group_of:
            continue
        d = gt["decoys"].get(i)
        group_of[i] = d["resembles"] if d is not None and d["resembles"] in dev_clusters else i

    true = {_key(a, b) for a, b in gt["true_pairs"]}
    for a, b in true:
        if (a in dev) != (b in dev):
            raise AssertionError("a true pair straddles the dev boundary")

    pairs = list(itertools.combinations(ids, 2))
    y = np.fromiter((1.0 if p in true else 0.0 for p in pairs), dtype=float, count=len(pairs))
    pos_by_group: dict[str, int] = {}
    for a, b in pairs:
        if (a, b) in true:
            pos_by_group[group_of[a]] = pos_by_group.get(group_of[a], 0) + 1
    return DevPairs(ids, pairs, y, group_of, pos_by_group)


def make_folds(group_of: dict[str, str], positives_by_group: dict[str, int], k: int, seed: int) -> dict[str, int]:
    """Assign whole groups to folds. Clusters are balanced by positive pairs, the rest by size."""
    rng = random.Random(seed)
    members: dict[str, list[str]] = {}
    for nc, g in group_of.items():
        members.setdefault(g, []).append(nc)
    cluster_groups = [g for g in members if positives_by_group.get(g, 0) > 0]
    cluster_set = set(cluster_groups)
    other_groups = [g for g in members if g not in cluster_set]
    if len(cluster_groups) < k:
        raise ValueError(f"need at least {k} clusters for {k} folds, have {len(cluster_groups)}")

    rng.shuffle(cluster_groups)
    cluster_groups.sort(key=lambda g: -positives_by_group[g])      # stable: shuffle breaks ties
    fold_pos = [0] * k
    fold_n = [0] * k
    fold_of_group: dict[str, int] = {}
    for g in cluster_groups:
        f = min(range(k), key=lambda i: (fold_pos[i], fold_n[i], i))
        fold_of_group[g] = f
        fold_pos[f] += positives_by_group[g]
        fold_n[f] += len(members[g])
    rng.shuffle(other_groups)
    for g in other_groups:
        f = min(range(k), key=lambda i: (fold_n[i], i))
        fold_of_group[g] = f
        fold_n[f] += len(members[g])
    return {nc: fold_of_group[g] for nc, g in group_of.items()}


def fold_arrays(pairs: list[tuple[str, str]], fold_of: dict[str, int]) -> tuple[np.ndarray, np.ndarray]:
    fa = np.fromiter((fold_of[a] for a, _ in pairs), dtype=int, count=len(pairs))
    fb = np.fromiter((fold_of[b] for _, b in pairs), dtype=int, count=len(pairs))
    return fa, fb


def check_folds(dp: DevPairs, fold_of: dict[str, int], k: int) -> None:
    """Raise AssertionError unless every leakage guarantee holds."""
    fa, fb = fold_arrays(dp.pairs, fold_of)
    # 1. no group spans two folds
    seen: dict[str, int] = {}
    for nc, g in dp.group_of.items():
        if seen.setdefault(g, fold_of[nc]) != fold_of[nc]:
            raise AssertionError(f"group {g} spans folds")
    # 2. every pair is scored exactly once across the k folds
    scored = np.zeros(len(dp.pairs), dtype=int)
    for f in range(k):
        scored += (fa == f)
    if not np.all(scored == 1):
        raise AssertionError("some pair is scored zero or several times")
    # 3. positives are fully held out together (both NCs in one fold)
    if np.any(fa[dp.y == 1] != fb[dp.y == 1]):
        raise AssertionError("a positive pair is split across folds")
    # 4. training pairs never contain a held-out NC, so no held-out group is ever trained on
    for f in range(k):
        train = (fa != f) & (fb != f)
        held_groups = {g for nc, g in dp.group_of.items() if fold_of[nc] == f}
        for idx in np.where(train)[0][:: max(1, int(train.sum()) // 5000)]:
            a, b = dp.pairs[idx]
            if dp.group_of[a] in held_groups or dp.group_of[b] in held_groups:
                raise AssertionError("a held-out group appears in training pairs")
        if train.sum() and not np.any(dp.y[train] == 1):
            raise AssertionError("a training set has no positive pairs")


def run_oof(X: np.ndarray, y: np.ndarray, fa: np.ndarray, fb: np.ndarray, k: int,
            fit: Callable[[np.ndarray, np.ndarray], Callable[[np.ndarray], np.ndarray]]):
    """Out-of-fold scores. `fit(X_train, y_train)` returns a function mapping X to scores.

    Returns (scores, models). models[f] is the model that scored the rows with fa == f.
    """
    scores = np.full(len(y), np.nan)
    models = []
    for f in range(k):
        train = (fa != f) & (fb != f)
        model = fit(X[train], y[train])
        rows = fa == f
        scores[rows] = model(X[rows])
        models.append(model)
    if np.isnan(scores).any():
        raise AssertionError("some pairs were never scored")
    return scores, models


def pair_matrices(ids: list[str], pairs: list[tuple[str, str]], values: np.ndarray, y: np.ndarray):
    """Dense symmetric score and label matrices for per-NC retrieval metrics."""
    pos = {nc: i for i, nc in enumerate(ids)}
    n = len(ids)
    S = np.full((n, n), -np.inf)
    Y = np.zeros((n, n), dtype=bool)
    ia = np.fromiter((pos[a] for a, _ in pairs), dtype=int, count=len(pairs))
    ib = np.fromiter((pos[b] for _, b in pairs), dtype=int, count=len(pairs))
    S[ia, ib] = values
    S[ib, ia] = values
    Y[ia, ib] = y == 1
    Y[ib, ia] = y == 1
    return S, Y