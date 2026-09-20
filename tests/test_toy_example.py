"""Hand-checkable sanity tests for risk_measures.py.

These use the exact tiny numeric example worked through by hand during
planning: 3 assets (Stocks, Bonds, Cash), 3 months, x = [0.4, 0.5, 0.1].
Every "expected" value below is computed independently with plain Python
loops (not by calling the functions under test), so this genuinely checks
the implementation rather than just re-running the same code twice.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import risk_measures as rm


# ---------------------------------------------------------------------------
# Toy data (ascending chronological order: row0=oldest ... row2=most recent)
# ---------------------------------------------------------------------------
R = np.array([
    [0.05,  0.01,  0.002],   # month 1
    [-0.03, 0.005, 0.002],   # month 2
    [0.02,  0.01,  0.002],   # month 3
])
X = np.array([0.4, 0.5, 0.1])
BCH = np.array([0.01, 0.01, 0.01])
EQUAL_WEIGHTS = np.array([1 / 3, 1 / 3, 1 / 3])


def independent_portfolio_returns():
    T, n = R.shape
    out = []
    for t in range(T):
        total = sum(R[t, i] * X[i] for i in range(n))
        out.append(total)
    return out


def independent_weighted_avg(values, weights):
    return sum(v * w for v, w in zip(values, weights))


def test_portfolio_return_series():
    expected = independent_portfolio_returns()
    got = rm.portfolio_return_series(X, R)
    for e, g in zip(expected, got):
        assert abs(e - g) < 1e-12, f"expected {e}, got {g}"
    # also matches the exact numbers worked out by hand in conversation
    assert abs(expected[0] - 0.0252) < 1e-9
    assert abs(expected[1] - (-0.0093)) < 1e-9
    assert abs(expected[2] - 0.0132) < 1e-9
    print("test_portfolio_return_series: PASS")


def test_symmetric_risk():
    portf = independent_portfolio_returns()
    gap = [portf[t] - BCH[t] for t in range(3)]
    avg_gap = independent_weighted_avg(gap, EQUAL_WEIGHTS)
    expected = independent_weighted_avg([(g - avg_gap) ** 2 for g in gap], EQUAL_WEIGHTS)

    got = rm.symmetric_risk(X, R, BCH, EQUAL_WEIGHTS)
    assert abs(expected - got) < 1e-12, f"expected {expected}, got {got}"
    print("test_symmetric_risk: PASS  (value =", got, ")")


def test_asymmetric_risk():
    portf = independent_portfolio_returns()
    gap = [portf[t] - BCH[t] for t in range(3)]
    clipped = [min(0.0, g) for g in gap]
    avg_clipped = independent_weighted_avg(clipped, EQUAL_WEIGHTS)
    expected = independent_weighted_avg([(c - avg_clipped) ** 2 for c in clipped], EQUAL_WEIGHTS)

    got = rm.asymmetric_risk(X, R, BCH, EQUAL_WEIGHTS)
    assert abs(expected - got) < 1e-12, f"expected {expected}, got {got}"
    print("test_asymmetric_risk: PASS  (value =", got, ")")


def test_markowitz_variance():
    portf = independent_portfolio_returns()
    mean = sum(portf) / len(portf)
    expected = sum((p - mean) ** 2 for p in portf) / (len(portf) - 1)

    got = rm.markowitz_variance(X, R)
    assert abs(expected - got) < 1e-12, f"expected {expected}, got {got}"
    print("test_markowitz_variance: PASS  (value =", got, ")")


def test_decaying_weights_matches_paper_example():
    weights = rm.decaying_weights(lam=0.95, T=36)
    assert abs(weights[-1] - 0.0594) < 1e-4, "most recent month should be 0.0594"
    assert abs(weights[0] - 0.0099) < 1e-4, "oldest month should be 0.0099"
    assert abs(weights.sum() - 1.0) < 1e-12, "weights must sum to 1"
    print("test_decaying_weights_matches_paper_example: PASS")


def test_expected_return_two_asset_example():
    # From ExpRet_Constraint_Explained.md: rho = [0.10, 0.04], target 0.045,
    # hand-solved answer was x_A = 0.08333..., x_B = 0.91667.
    rho = np.array([0.10, 0.04])
    x = np.array([0.005 / 0.06, 1 - 0.005 / 0.06])
    got = rm.expected_return(x, rho)
    assert abs(got - 0.045) < 1e-9, f"expected 0.045, got {got}"
    print("test_expected_return_two_asset_example: PASS")


def test_tracking_term():
    m = np.array([0.3, 0.5, 0.2])
    gamma = 0.1
    expected = gamma * ((0.4 - 0.3) ** 2 + (0.5 - 0.5) ** 2 + (0.1 - 0.2) ** 2)
    got = rm.tracking_term(X, m, gamma)
    assert abs(expected - got) < 1e-12
    print("test_tracking_term: PASS")


if __name__ == "__main__":
    test_portfolio_return_series()
    test_symmetric_risk()
    test_asymmetric_risk()
    test_markowitz_variance()
    test_decaying_weights_matches_paper_example()
    test_expected_return_two_asset_example()
    test_tracking_term()
    print("\nAll toy-example tests passed.")
