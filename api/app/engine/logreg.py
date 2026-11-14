"""Weighted L2-regularised logistic regression (Newton / IRLS) in numpy.

Offline use only (fitting and eval); the runtime scoring path does not import numpy.
"""
from __future__ import annotations

import numpy as np


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


def _loss(A, y, sw, reg, w) -> float:
    z = A @ w
    ll = np.logaddexp(0.0, z) - y * z
    return float(np.sum(sw * ll) + 0.5 * np.sum(reg * w * w))


def fit_logistic(
    X,
    y,
    sample_weight=None,
    l2: float = 1.0,
    max_iter: int = 50,
    tol: float = 1e-8,
    *,
    nonneg: bool = False,
):
    """Return (bias, weights). The bias is not regularised.

    nonneg=True constrains every weight to be >= 0 (the bias stays free); it is solved
    exactly by fit_logistic_nonneg and verified against the KKT conditions.
    """
    if nonneg:
        bias, weights, _ = fit_logistic_nonneg(X, y, sample_weight, l2, max_iter, tol)
        return bias, weights
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, d = X.shape
    if n == 0 or y.min() == y.max():
        raise ValueError("need rows from both classes")
    sw = np.ones(n) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    sw = sw / sw.mean()
    A = np.hstack([np.ones((n, 1)), X])
    reg = np.full(d + 1, float(l2))
    reg[0] = 0.0
    w = np.zeros(d + 1)
    for _ in range(max_iter):
        p = sigmoid(A @ w)
        grad = A.T @ (sw * (p - y)) + reg * w
        s = sw * p * (1.0 - p)
        H = (A.T * s) @ A + np.diag(reg)
        H[np.diag_indices(d + 1)] += 1e-9
        step = np.linalg.solve(H, grad)
        cur = _loss(A, y, sw, reg, w)
        t = 1.0
        for _ in range(20):
            cand = w - t * step
            if _loss(A, y, sw, reg, cand) <= cur + 1e-12:
                break
            t *= 0.5
        w = cand
        if np.max(np.abs(t * step)) < tol:
            break
    return float(w[0]), w[1:].copy()


def predict_proba(X, bias: float, weights) -> np.ndarray:
    return sigmoid(np.asarray(X, dtype=float) @ np.asarray(weights, dtype=float) + bias)


# ---------------------------------------------------------------- non-negative fitting
_NEG_TOL = 1e-10  # a free weight below -_NEG_TOL is a real violation, not rounding noise
_ACTIVE_TOL = 1e-12  # weights at or below this count as sitting on the w >= 0 boundary


def _gradient(X, y, sw, bias, w, l2):
    """Gradient of the fit objective (weighted log-loss + 0.5 * l2 * |w|^2), per parameter."""
    resid = sw * (sigmoid(X @ w + bias) - y)
    return float(resid.sum()), X.T @ resid + l2 * w


def kkt_violation(X, y, bias, weights, sample_weight=None, l2: float = 1.0) -> dict:
    """How far (bias, weights) is from satisfying the KKT conditions of the non-negative fit.

    For  min f(b, w)  subject to  w >= 0  the conditions are:
      stationarity of the bias        df/db = 0
      free weights (w > 0)            df/dw_j = 0
      weights on the boundary (w = 0) df/dw_j >= 0   (dual feasibility)
      primal feasibility              w_j >= 0
    Gradients are divided by n so tolerances do not depend on the dataset size. The gradient
    is computed here from the objective itself, independently of the solver.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(weights, dtype=float)
    n = len(y)
    sw = np.ones(n) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    sw = sw / sw.mean()
    g_b, g_w = _gradient(X, y, sw, float(bias), w, float(l2))
    active = w <= _ACTIVE_TOL
    free = ~active
    out = {
        "bias_grad": abs(g_b) / n,
        "free_grad": float(np.max(np.abs(g_w[free]))) / n if free.any() else 0.0,
        "active_violation": float(max(0.0, -np.min(g_w[active]))) / n if active.any() else 0.0,
        "negative_weight": float(max(0.0, -np.min(w))) if len(w) else 0.0,
    }
    out["max"] = max(out.values())
    return out


def fit_logistic_nonneg(
    X,
    y,
    sample_weight=None,
    l2: float = 1.0,
    max_iter: int = 50,
    tol: float = 1e-8,
    kkt_tol: float = 1e-6,
    max_outer: int | None = None,
):
    """Exact non-negative L2 logistic fit by an active-set method. Returns (bias, weights, info).

    Weights with a negative coefficient are not clipped: the most negative one is fixed at 0
    and the remaining weights are refitted (so they can compensate). A fixed weight whose
    gradient shows the objective would improve by letting it grow is released again. The loop
    ends only when the KKT conditions hold, and the result is verified with kkt_violation;
    the solver raises RuntimeError rather than return a point that fails the check.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, d = X.shape
    if n == 0 or y.min() == y.max():
        raise ValueError("need rows from both classes")
    sw = np.ones(n) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    sw = sw / sw.mean()
    limit = max_outer if max_outer is not None else 4 * d + 4
    free = list(range(d))
    released = 0
    for outer in range(1, limit + 1):
        cols = np.array(sorted(free), dtype=int)
        bias, w_free = fit_logistic(X[:, cols], y, sample_weight, l2, max_iter, tol)
        w = np.zeros(d)
        w[cols] = w_free
        negative = [j for j in free if w[j] < -_NEG_TOL]
        if negative:
            free.remove(min(negative, key=lambda j: w[j]))
            continue
        w[w < 0.0] = 0.0  # only rounding noise (>= -1e-10) can remain here
        _, grad = _gradient(X, y, sw, bias, w, float(l2))
        fixed = [j for j in range(d) if j not in free]
        if fixed:
            worst = min(fixed, key=lambda j: grad[j])
            if grad[worst] / n < -kkt_tol:  # objective still improves if w[worst] grows
                free.append(worst)
                released += 1
                continue
        report = kkt_violation(X, y, bias, w, sample_weight, l2)
        if report["max"] > kkt_tol:
            raise RuntimeError(f"non-negative fit failed its KKT check: {report}")
        info = {
            "outer_iterations": outer,
            "released": released,
            "kkt": report,
            "at_zero": sorted(j for j in range(d) if w[j] <= _ACTIVE_TOL),
        }
        return float(bias), w, info
    raise RuntimeError(f"non-negative active-set search did not converge in {limit} rounds")