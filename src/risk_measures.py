"""The core mathematical formulas: PortfRet, ExpRet, the three risk
measures, and the decay-weight vector.

All functions take x as a 1-D numpy array of portfolio weights, in the
same asset order as config.ASSET_NAMES. Return tables are 2-D numpy
arrays (T rows x n columns), in ascending chronological order (row 0 =
oldest month, row T-1 = most recent month) -- this ordering convention is
what decaying_weights() assumes.

Every formula here was worked through by hand with tiny numeric examples
during planning (see ExpRet_Constraint_Explained.md and the project
conversation); tests/test_toy_example.py checks these implementations
against those exact hand calculations.
"""

import numpy as np


def portfolio_return_series(x: np.ndarray, returns_table: np.ndarray) -> np.ndarray:
    """PortfRet_t = sum_i r_{t,i} * x_i, for every month t."""
    return returns_table @ x


def expected_return(x: np.ndarray, rho: np.ndarray) -> float:
    """ExpRet = sum_i rho_i * x_i."""
    return float(rho @ x)


def decaying_weights(lam: float, T: int) -> np.ndarray:
    """omega_t, in ascending chronological order (index 0 = oldest month,
    index T-1 = most recent month). Verified against the paper's own
    worked example (lambda=0.95, T=36 -> omega for most recent = 0.0594,
    omega for oldest = 0.0099).
    """
    exponents = np.arange(T - 1, -1, -1)   # T-1, T-2, ..., 0  (index0->oldest gets biggest exponent)
    raw = lam ** exponents
    return raw / raw.sum()


def weighted_average(series: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(weights * series))


def symmetric_risk(x: np.ndarray, returns_table: np.ndarray,
                    benchmark_series: np.ndarray, weights: np.ndarray) -> float:
    """Sum_t omega_t * [ (PortfRet_t - BchRet_t) - Av(PortfRet_t - BchRet_t) ]^2."""
    portf = portfolio_return_series(x, returns_table)
    gap = portf - benchmark_series
    avg_gap = weighted_average(gap, weights)
    return weighted_average((gap - avg_gap) ** 2, weights)


def asymmetric_risk(x: np.ndarray, returns_table: np.ndarray,
                     benchmark_series: np.ndarray, weights: np.ndarray) -> float:
    """Same as symmetric_risk, but the gap is first clipped so that any
    month the portfolio beat the benchmark counts as zero (only
    underperformance counts as risk).
    """
    portf = portfolio_return_series(x, returns_table)
    gap = portf - benchmark_series
    downside_gap = np.minimum(0.0, gap)
    avg_downside = weighted_average(downside_gap, weights)
    return weighted_average((downside_gap - avg_downside) ** 2, weights)


def markowitz_variance(x: np.ndarray, returns_table: np.ndarray) -> float:
    """Classical portfolio variance, computed WITHOUT ever building an
    explicit covariance matrix -- exactly the trick the paper describes:
    build the single PortfRet_t series first, then take its own variance.
    """
    portf = portfolio_return_series(x, returns_table)
    T = len(portf)
    mean = portf.mean()
    return float(np.sum((portf - mean) ** 2) / (T - 1))


def tracking_term(x: np.ndarray, market_weights: np.ndarray, gamma: float) -> float:
    """gamma * sum_j (x_j - m_j)^2."""
    return gamma * float(np.sum((x - market_weights) ** 2))


RISK_FUNCTIONS = {
    "symmetric": symmetric_risk,
    "asymmetric": asymmetric_risk,
    "markowitz": markowitz_variance,
}


def compute_risk(risk_measure: str, x: np.ndarray, returns_table: np.ndarray,
                  benchmark_series: np.ndarray, weights: np.ndarray) -> float:
    if risk_measure == "markowitz":
        return markowitz_variance(x, returns_table)
    if risk_measure in ("symmetric", "asymmetric"):
        return RISK_FUNCTIONS[risk_measure](x, returns_table, benchmark_series, weights)
    raise ValueError(f"Unknown risk measure '{risk_measure}'")
