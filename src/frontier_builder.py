"""Builds one full efficient frontier for one fixed customer profile and
one chosen risk measure -- this is 'Loop B' from loop.md, implementing the
4-step procedure from the paper's Appendix ("Constructing an Efficient
Frontier"):

  1. Solve for the minimum-risk portfolio (ignore expected return).
  2. Solve for the maximum-return portfolio (ignore risk).
  3. Pick K evenly spaced target returns between steps 1 and 2's results.
  4. Solve K more problems: minimize risk subject to ExpRet = target_k.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import optimizer


def build_frontier(risk_measure: str, profile: dict, returns_table: np.ndarray,
                    benchmark_series: np.ndarray, weights: np.ndarray,
                    market_weights: np.ndarray, rho: np.ndarray,
                    gamma: float = None, K: int = None) -> pd.DataFrame:
    if gamma is None:
        gamma = config.GAMMA_TRACKING
    if K is None:
        K = config.K_FRONTIER_POINTS

    n_assets = returns_table.shape[1]
    rows = []

    # Step 1: minimum-risk portfolio, no return target.
    step1 = optimizer.solve_min_risk(
        risk_measure, returns_table, benchmark_series, weights,
        market_weights, gamma, profile, rho, n_assets,
    )
    rows.append({
        "point": "min_risk", "target_return": None,
        "achieved_return": step1["expected_return"], "risk": step1["risk"],
        "success": step1["success"], "x": step1["x"],
    })

    # Step 2: maximum-return portfolio, ignore risk.
    step2 = optimizer.solve_max_return(profile, rho, n_assets)
    # Its risk score isn't part of that solve's objective, but we still
    # want to know it for plotting the frontier, so we compute it now.
    import risk_measures as rm
    step2_risk = rm.compute_risk(risk_measure, step2["x"], returns_table, benchmark_series, weights)
    rows.append({
        "point": "max_return", "target_return": None,
        "achieved_return": step2["expected_return"], "risk": step2_risk,
        "success": step2["success"], "x": step2["x"],
    })

    # Step 3: K evenly spaced target returns between step 1 and step 2.
    low_ret = step1["expected_return"]
    high_ret = step2["expected_return"]
    if high_ret <= low_ret:
        raise ValueError(
            f"max-return portfolio's return ({high_ret:.4f}) is not above "
            f"the min-risk portfolio's return ({low_ret:.4f}) -- check "
            f"constraints/profile for '{profile['profile_id']}'."
        )
    targets = np.linspace(low_ret, high_ret, K + 2)[1:-1]  # exclude the two endpoints already solved

    # Step 4: solve K constrained problems, one per target return.
    for k, target in enumerate(targets, start=1):
        step4 = optimizer.solve_target_return(
            risk_measure, returns_table, benchmark_series, weights,
            market_weights, gamma, profile, rho, target, n_assets,
        )
        rows.append({
            "point": f"k={k}", "target_return": target,
            "achieved_return": step4["expected_return"], "risk": step4["risk"],
            "success": step4["success"], "x": step4["x"],
        })

    frontier = pd.DataFrame(rows)
    return frontier


def frontier_to_weight_table(frontier: pd.DataFrame) -> pd.DataFrame:
    """Expands the 'x' column (numpy arrays) into one column per asset."""
    weight_rows = []
    for _, row in frontier.iterrows():
        d = {name: w for name, w in zip(config.ASSET_NAMES, row["x"])}
        d["point"] = row["point"]
        d["risk"] = row["risk"]
        d["achieved_return"] = row["achieved_return"]
        weight_rows.append(d)
    return pd.DataFrame(weight_rows)
