"""Ranking and operating-point metrics for link scoring. numpy only, offline use.

Everything is tie-aware: equal scores never get an arbitrary (and possibly flattering) order.
"""
from __future__ import annotations

import numpy as np

_EPS = 1e-15


def _logit(p: float) -> float:
    p = min(max(float(p), _EPS), 1.0 - _EPS)
    return float(np.log(p / (1.0 - p)))


def _sigmoid(z: float) -> float:
    return float(1.0 / (1.0 + np.exp(-z)))


def _check(scores, y):
    s = np.asarray(scores, dtype=float)
    t = np.asarray(y, dtype=float)
    if s.shape != t.shape or s.ndim != 1:
        raise ValueError("scores and labels must be 1-D arrays of equal length")
    n1 = float(t.sum())
    if n1 == 0 or n1 == len(t):
        raise ValueError("need both classes")
    return s, t, n1


def roc_auc(scores, y) -> float:
    """Area under the ROC curve with mid-rank handling of ties."""
    s, t, n1 = _check(scores, y)
    n0 = len(t) - n1
    order = np.argsort(s, kind="mergesort")
    _, inv, counts = np.unique(s[order], return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    mid_rank = np.cumsum(counts) - (counts - 1) / 2.0  # 1-based
    ranks = np.empty(len(s))
    ranks[order] = mid_rank[inv]
    return float((ranks[t == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def _curve(scores, y):
    """Precision/recall/F1 for every distinct threshold (flag score >= t), highest first."""
    s, t, n1 = _check(scores, y)
    order = np.argsort(-s, kind="mergesort")
    ss, tt = s[order], t[order]
    tp = np.cumsum(tt)
    fp = np.cumsum(1.0 - tt)
    last = np.r_[np.where(np.diff(ss) != 0)[0], len(ss) - 1]  # last row of each distinct score
    tp_k, fp_k = tp[last], fp[last]
    precision = tp_k / (tp_k + fp_k)
    recall = tp_k / n1
    denom = precision + recall
    f1 = np.divide(2 * precision * recall, denom, out=np.zeros_like(denom), where=denom > 0)
    return ss[last], precision, recall, f1


def average_precision(scores, y) -> float:
    """AUPRC as average precision (step-wise, no interpolation)."""
    _, precision, recall, _ = _curve(scores, y)
    prev = np.r_[0.0, recall[:-1]]
    return float(np.sum((recall - prev) * precision))


def log_loss(prob, y) -> float:
    p = np.clip(np.asarray(prob, dtype=float), _EPS, 1.0 - _EPS)
    t = np.asarray(y, dtype=float)
    return float(-np.mean(t * np.log(p) + (1.0 - t) * np.log(1.0 - p)))


def operating_point(scores, y, threshold: float) -> dict:
    s = np.asarray(scores, dtype=float)
    t = np.asarray(y, dtype=float)
    flag = s >= threshold
    tp = float(np.sum(flag & (t == 1)))
    fp = float(np.sum(flag & (t == 0)))
    fn = float(np.sum(~flag & (t == 1)))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"threshold": float(threshold), "precision": prec, "recall": rec, "f1": f1,
            "n_flagged": int(flag.sum()), "tp": int(tp), "fp": int(fp), "fn": int(fn)}


def select_threshold(scores, y, plateau: float = 0.01) -> dict:
    """Pre-committed rule: take the F1-maximising region, then its logit-space midpoint.

    The region is the contiguous run of distinct score thresholds around the best F1 whose
    F1 is within `plateau` (relative) of the best. Any threshold t in
    (next lower observed score, highest score in the run] flags a set from that run, so the
    midpoint of that interval is the threshold with the widest margin on both sides.
    Candidates are observed scores, so there is no artificial cap.
    """
    thr, _, _, f1 = _curve(scores, y)
    best = float(f1.max())
    m = int(np.argmax(f1))
    ok = f1 >= (1.0 - plateau) * best
    lo = hi = m
    while lo - 1 >= 0 and ok[lo - 1]:
        lo -= 1
    while hi + 1 < len(f1) and ok[hi + 1]:
        hi += 1
    high_t = float(thr[lo])                                   # thresholds descend: lo is highest
    low_t = float(thr[hi + 1]) if hi + 1 < len(thr) else float(thr[hi])   # exclusive bound
    if low_t >= high_t:
        chosen = high_t
    else:
        chosen = min(_sigmoid((_logit(high_t) + _logit(low_t)) / 2.0), high_t)
    op = operating_point(scores, y, chosen)
    return {"threshold": chosen, "f1": op["f1"], "precision": op["precision"],
            "recall": op["recall"], "best_f1": best, "best_threshold": float(thr[m]),
            "plateau_low": low_t, "plateau_high": high_t}


def per_nc_report(S, Y, ks=(1, 3, 5), threshold: float | None = None) -> dict:
    """Per-NC retrieval quality from a dense symmetric score matrix.

    S[i, j] is the score between NC i and NC j (diagonal ignored). Y[i, j] is True for a true
    pair. Every NC is a query against ALL other NCs, as find_related does at runtime. Ties are
    broken against the true mates, so ties can never flatter the result.
    """
    S = np.array(S, dtype=float)
    Y = np.asarray(Y, dtype=bool)
    n = len(S)
    np.fill_diagonal(S, -np.inf)
    has_mates = Y.any(axis=1)
    out: dict = {"n_queries_with_mates": int(has_mates.sum()),
                 "n_queries_without_mates": int((~has_mates).sum())}
    p_at = {k: [] for k in ks}
    r_at = {k: [] for k in ks}
    h_at = {k: [] for k in ks}
    rr = []
    for q in np.where(has_mates)[0]:
        cand = np.array([j for j in range(n) if j != q])
        order = cand[np.lexsort((Y[q, cand].astype(int), -S[q, cand]))]
        hits = Y[q, order]
        mates = int(hits.sum())
        for k in ks:
            h = int(hits[:k].sum())
            p_at[k].append(h / k)
            r_at[k].append(h / mates)
            h_at[k].append(float(h > 0))
        rr.append(1.0 / (int(np.argmax(hits)) + 1))
    for k in ks:
        out[f"precision_at_{k}"] = float(np.mean(p_at[k])) if p_at[k] else 0.0
        out[f"recall_at_{k}"] = float(np.mean(r_at[k])) if r_at[k] else 0.0
        out[f"hit_at_{k}"] = float(np.mean(h_at[k])) if h_at[k] else 0.0
    out["mrr"] = float(np.mean(rr)) if rr else 0.0

    if threshold is not None:
        flagged = S >= threshold
        returned = flagged.sum(axis=1)
        no = ~has_mates
        out["threshold"] = float(threshold)
        out["mean_links_no_mate_queries"] = float(returned[no].mean()) if no.any() else 0.0
        out["frac_no_mate_queries_alerted"] = float((returned[no] > 0).mean()) if no.any() else 0.0
        mq = has_mates
        tp = (flagged & Y).sum(axis=1)
        with_links = mq & (returned > 0)
        out["precision_at_threshold"] = (
            float((tp[with_links] / returned[with_links]).mean()) if with_links.any() else 0.0
        )
        mates_n = Y.sum(axis=1)
        out["recall_at_threshold"] = float((tp[mq] / mates_n[mq]).mean()) if mq.any() else 0.0
        out["frac_mate_queries_with_any_link"] = float((returned[mq] > 0).mean()) if mq.any() else 0.0
    return out