"""Combines a chosen risk measure with the market-tracking penalty into the
single number the solver actually minimizes:

    objective(x) = risk_measure(x)  +  gamma * sum_j (x_j - m_j)^2
"""

import numpy as np

import risk_measures as rm


def build_objective(risk_measure: str, returns_table: np.ndarray,
                     benchmark_series: np.ndarray, weights: np.ndarray,
                     market_weights: np.ndarray, gamma: float):
    """Returns a function f(x) -> float suitable for scipy.optimize.minimize."""

    def objective(x: np.ndarray) -> float:
        risk = rm.compute_risk(risk_measure, x, returns_table, benchmark_series, weights)
        track = rm.tracking_term(x, market_weights, gamma)
        return risk + track

    return objective


def build_negative_expected_return(rho: np.ndarray):
    """For the Step 2 problem ('maximize ExpRet'), scipy only minimizes, so
    we minimize the negative of ExpRet instead.
    """

    def objective(x: np.ndarray) -> float:
        return -rm.expected_return(x, rho)

    return objective



