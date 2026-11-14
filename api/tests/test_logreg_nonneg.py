import inspect

import numpy as np
import pytest

from app.engine import logreg
from app.engine.logreg import fit_logistic, fit_logistic_nonneg, kkt_violation, sigmoid

# Output of the ORIGINAL solver on snapshot_data(); guards against behaviour drift.
SNAPSHOT_BIAS = -0.04726458827521216
SNAPSHOT_WEIGHTS = [1.4829422565742474, -0.9234129318077235, 0.11096515964369581]


# ---------------------------------------------------------------- deterministic datasets
def _hash(i: int) -> float:
    return ((i * 2654435761) % 1000003) / 1000003.0


def _labels(z: np.ndarray) -> np.ndarray:
    return np.array([1.0 if _hash(k) < sigmoid(z[k]) else 0.0 for k in range(len(z))])


def snapshot_data(n: int = 300):
    i = np.arange(n)
    X = np.column_stack([np.sin(0.37 * i), np.cos(0.11 * i), ((i * 7919) % 100) / 100.0])
    return X, _labels(1.5 * X[:, 0] - 1.0 * X[:, 1] + 0.8 * X[:, 2] - 0.4)


def collinear_data(n: int = 600):
    """x1 is x0 plus noise, so the free fit gives x1 a negative weight."""
    i = np.arange(n)
    x0 = np.sin(0.3 * i)
    x1 = x0 + 0.3 * np.cos(1.7 * i)
    x2 = np.cos(0.05 * i)
    return np.column_stack([x0, x1, x2]), _labels(2.0 * x0 - 1.5 * x1 + 0.5 * x2 - 0.3)


def imbalanced_data(n: int = 6000):
    i = np.arange(n)
    a, b = np.sin(0.011 * i), np.cos(0.07 * i)
    c = ((i * 7919) % 100) / 100.0
    X = np.column_stack([a, b, c, a * b])
    return X, _labels(-6.0 + 3.0 * a - 1.5 * b + 2.0 * c)


def weights_for(y: np.ndarray, scheme: str):
    n_pos = float(y.sum())
    n_neg = len(y) - n_pos
    if scheme == "none":
        return None
    factor = np.sqrt(n_neg / n_pos) if scheme == "mild" else n_neg / n_pos
    return np.where(y == 1, factor, 1.0)


# ---------------------------------------------------------------- independent references
def objective(X, y, bias, w, sw=None, l2=1.0) -> float:
    """The fit objective, written out here independently of the solver."""
    sw = np.ones(len(y)) if sw is None else np.asarray(sw, dtype=float)
    sw = sw / sw.mean()
    z = X @ w + bias
    return float(np.sum(sw * (np.logaddexp(0.0, z) - y * z)) + 0.5 * l2 * np.sum(w * w))


def gradient(X, y, bias, w, sw=None, l2=1.0):
    sw = np.ones(len(y)) if sw is None else np.asarray(sw, dtype=float)
    sw = sw / sw.mean()
    resid = sw * (sigmoid(X @ w + bias) - y)
    return resid.sum() / len(y), (X.T @ resid + l2 * w) / len(y)


def assert_kkt(X, y, bias, w, sw=None, l2=1.0, tol=1e-7):
    assert np.all(w >= 0.0), "primal feasibility"
    g_b, g_w = gradient(X, y, bias, w, sw, l2)
    assert abs(g_b) < tol, f"bias stationarity: {g_b}"
    for j, wj in enumerate(w):
        if wj > 1e-12:
            assert abs(g_w[j]) < tol, f"free weight {j} not stationary: {g_w[j]}"
        else:
            assert g_w[j] > -tol, f"boundary weight {j} has descent direction: {g_w[j]}"


# ---------------------------------------------------------------- existing behaviour
def test_signature_keeps_original_parameters_and_adds_keyword_only_flag():
    params = inspect.signature(fit_logistic).parameters
    assert list(params)[:6] == ["X", "y", "sample_weight", "l2", "max_iter", "tol"]
    flag = params["nonneg"]
    assert flag.kind is inspect.Parameter.KEYWORD_ONLY and flag.default is False


def test_default_path_is_unchanged():
    X, y = snapshot_data()
    bias, w = fit_logistic(X, y)
    assert bias == pytest.approx(SNAPSHOT_BIAS, abs=1e-9)
    assert w == pytest.approx(SNAPSHOT_WEIGHTS, abs=1e-9)
    bias2, w2 = fit_logistic(X, y, nonneg=False)
    assert bias2 == bias and np.array_equal(w2, w)


def test_needs_both_classes_in_both_modes():
    X = np.zeros((5, 2))
    for nonneg in (False, True):
        with pytest.raises(ValueError):
            fit_logistic(X, np.ones(5), nonneg=nonneg)


# ---------------------------------------------------------------- non-negative mode
def test_matches_unconstrained_fit_when_it_is_already_non_negative():
    X, y = snapshot_data()
    X = X * np.array([1.0, -1.0, 1.0])  # flips the negative relationship
    free_b, free_w = fit_logistic(X, y)
    assert np.all(free_w > 0)
    bias, w, info = fit_logistic_nonneg(X, y)
    assert bias == pytest.approx(free_b, abs=1e-9) and w == pytest.approx(free_w, abs=1e-9)
    assert info["at_zero"] == [] and info["outer_iterations"] == 1


def test_negative_weight_is_refitted_not_clipped():
    X, y = collinear_data()
    free_b, free_w = fit_logistic(X, y)
    assert free_w[1] < -0.1  # the free solution really is infeasible
    bias, w, info = fit_logistic_nonneg(X, y)

    assert np.all(w >= 0.0) and w[1] == 0.0 and info["at_zero"] == [1]
    assert_kkt(X, y, bias, w)

    clipped = np.maximum(free_w, 0.0)
    f_free = objective(X, y, free_b, free_w)
    f_nonneg = objective(X, y, bias, w)
    f_clipped = objective(X, y, free_b, clipped)
    assert f_nonneg >= f_free - 1e-9  # a constraint cannot beat the free optimum
    assert f_nonneg < f_clipped - 1e-3  # and it clearly beats clip-to-zero
    assert w[0] != pytest.approx(clipped[0], abs=1e-3)  # the other weights compensated


def test_kkt_check_rejects_the_clipped_solution_and_infeasible_points():
    X, y = collinear_data()
    free_b, free_w = fit_logistic(X, y)
    clipped = kkt_violation(X, y, free_b, np.maximum(free_w, 0.0))
    assert clipped["max"] > 1e-4
    infeasible = kkt_violation(X, y, free_b, free_w)
    assert infeasible["negative_weight"] == pytest.approx(-free_w[1])
    assert infeasible["max"] > 0.1
    bias, w, _ = fit_logistic_nonneg(X, y)
    assert kkt_violation(X, y, bias, w)["max"] < 1e-7


def test_kkt_check_detects_a_released_boundary_weight():
    # a weight at 0 whose gradient says "grow me" violates dual feasibility
    i = np.arange(400)
    x = np.sin(0.2 * i)
    y = _labels(2.0 * x)
    X = x.reshape(-1, 1)
    bias, _ = fit_logistic(X[:, :0], y)  # bias-only fit with the weight stuck at 0
    report = kkt_violation(X, y, bias, np.array([0.0]))
    assert report["active_violation"] > 1e-3


def test_no_feasible_improvement_in_random_directions():
    X, y = collinear_data()
    bias, w, _ = fit_logistic_nonneg(X, y)
    best = objective(X, y, bias, w)
    rng = np.random.default_rng(7)
    for _ in range(400):
        scale = rng.choice([1e-3, 1e-2, 1e-1, 0.3])
        w2 = np.maximum(w + scale * rng.normal(size=w.shape), 0.0)  # feasible by construction
        b2 = bias + scale * rng.normal()
        assert objective(X, y, b2, w2) >= best - 1e-9


def test_relationships_that_are_all_negative_give_all_zero_weights():
    i = np.arange(500)
    y = np.array([1.0 if _hash(k) < 0.3 else 0.0 for k in i])
    X = np.column_stack([-y + 0.5 * np.sin(0.7 * i), -2.0 * y + 0.3 * np.cos(0.3 * i)])
    _, free_w = fit_logistic(X, y)
    assert np.all(free_w < 0)
    bias, w, info = fit_logistic_nonneg(X, y)
    assert np.all(w == 0.0) and info["at_zero"] == [0, 1]
    assert bias == pytest.approx(
        np.log(y.mean() / (1 - y.mean())), abs=1e-6
    )  # prevalence logit
    assert_kkt(X, y, bias, w)


def test_bias_stays_unconstrained_and_prevalence_is_respected():
    X, y = imbalanced_data()
    bias, w, _ = fit_logistic_nonneg(X, y)
    assert bias < -3.0 and np.all(w >= 0.0)
    assert 10 < y.sum() < 0.05 * len(y)


@pytest.mark.parametrize("scheme", ["none", "mild", "balanced"])
@pytest.mark.parametrize("l2", [1e-3, 1.0, 100.0])
def test_converges_and_satisfies_kkt_under_weighting_and_regularisation(scheme, l2):
    X, y = imbalanced_data()
    sw = weights_for(y, scheme)
    bias, w, info = fit_logistic_nonneg(X, y, sw, l2=l2)
    d = X.shape[1]
    assert info["outer_iterations"] <= 4 * d + 4
    assert np.all(w >= 0.0) and np.all(np.isfinite(w)) and np.isfinite(bias)
    assert info["kkt"]["max"] < 1e-6
    assert_kkt(X, y, bias, w, sw, l2, tol=2e-6)
    free_b, free_w = fit_logistic(X, y, sw, l2=l2)
    assert objective(X, y, bias, w, sw, l2) >= objective(X, y, free_b, free_w, sw, l2) - 1e-7


def test_public_flag_matches_dedicated_function_and_is_deterministic():
    X, y = collinear_data()
    b1, w1 = fit_logistic(X, y, nonneg=True)
    b2, w2, _ = fit_logistic_nonneg(X, y)
    b3, w3 = fit_logistic(X, y, nonneg=True)
    assert b1 == b2 == b3 and np.array_equal(w1, w2) and np.array_equal(w1, w3)


def test_weight_wrongly_fixed_at_zero_is_released_again(monkeypatch):
    # In 30,000 random trials the release step was never needed on organic data, so it is
    # exercised by injecting an infeasible first fit that forces x0 to be removed wrongly.
    X, y = snapshot_data()
    X = X * np.array([1.0, -1.0, 1.0])
    free_b, free_w = fit_logistic(X, y)
    assert np.all(free_w > 0)
    real_fit = logreg.fit_logistic
    calls = []

    def flaky_fit(Xc, yc, *args, **kwargs):
        calls.append(Xc.shape[1])
        bias, w = real_fit(Xc, yc, *args, **kwargs)
        if len(calls) == 1:
            w = w.copy()
            w[0] = -1.0  # pretend x0 came out negative
        return bias, w

    monkeypatch.setattr(logreg, "fit_logistic", flaky_fit)
    bias, w, info = fit_logistic_nonneg(X, y)
    assert calls == [3, 2, 3]  # fit, drop x0, release x0 and refit
    assert info["released"] == 1
    assert bias == pytest.approx(free_b, abs=1e-9) and w == pytest.approx(free_w, abs=1e-9)
    assert_kkt(X, y, bias, w)


def test_gives_up_loudly_instead_of_returning_a_bad_point(monkeypatch):
    X, y = collinear_data()
    with pytest.raises(RuntimeError, match="did not converge"):
        fit_logistic_nonneg(X, y, max_outer=1)  # needs a second round to drop x1
    monkeypatch.setattr(logreg, "kkt_violation", lambda *a, **k: {"max": 1.0})
    with pytest.raises(RuntimeError, match="KKT"):
        fit_logistic_nonneg(X, y)