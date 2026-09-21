"""Builds every constraint scipy needs, in the format scipy.optimize.minimize
expects: a list of dicts, each either

    {'type': 'eq',  'fun': f}   meaning f(x) must equal 0
    {'type': 'ineq','fun': f}   meaning f(x) must be >= 0

plus a separate bounds list for the simple x_i >= 0 (and <= 1) rules,
which scipy handles more efficiently as bounds rather than constraints.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import risk_measures as rm


def _indices_of(names: list[str]) -> np.ndarray:
    return np.array([config.ASSET_NAMES.index(n) for n in names])


EQUITY_ASSETS = ["IL_Equity", "US_Equity", "EU_Equity"]
EQUITY_IDX = _indices_of(EQUITY_ASSETS)
ILLIQUID_IDX = _indices_of(config.ILLIQUID_ASSETS)
FOREIGN_IDX = _indices_of(config.FOREIGN_ASSETS)


def bounds_no_short_selling(n_assets: int):
    """x_i in [0, 1] for every asset -- no short-selling, no leverage."""
    return [(0.0, 1.0) for _ in range(n_assets)]


def budget_constraint():
    return {"type": "eq", "fun": lambda x: np.sum(x) - 1.0}


def expected_return_constraint(rho: np.ndarray, target: float):
    return {"type": "eq", "fun": lambda x: rm.expected_return(x, rho) - target}


def equity_cap_constraint(cap: float):
    return {"type": "ineq", "fun": lambda x: cap - np.sum(x[EQUITY_IDX])}


def liquidity_constraint(cap: float):
    return {"type": "ineq", "fun": lambda x: cap - np.sum(x[ILLIQUID_IDX])}


def currency_constraint(cap: float):
    return {"type": "ineq", "fun": lambda x: cap - np.sum(x[FOREIGN_IDX])}


def turnover_constraint(existing_portfolio: np.ndarray, cap: float):
    return {"type": "ineq",
            "fun": lambda x: cap - np.sum(np.abs(x - existing_portfolio))}


def build_constraints(profile: dict, rho: np.ndarray, target_return: float = None):
    """profile is a dict produced by customer_profiles.py, containing keys:
       'liquidity_cap', 'currency_cap' (each optional; None = no limit),
       plus an optional 'equity_cap',
       and optionally 'turnover_cap' + 'existing_portfolio'.

    target_return: if given, adds the ExpRet = target_return equality
    constraint (this is the Step-4 case). If None, no return constraint is
    added (this is the Step-1 case: minimize risk only).
    """
    cons = [budget_constraint()]

    if profile.get("equity_cap") is not None:
        cons.append(equity_cap_constraint(profile["equity_cap"]))

    if profile.get("liquidity_cap") is not None:
        cons.append(liquidity_constraint(profile["liquidity_cap"]))
    if profile.get("currency_cap") is not None:
        cons.append(currency_constraint(profile["currency_cap"]))
    if profile.get("turnover_cap") is not None:
        cons.append(turnover_constraint(profile["existing_portfolio"], profile["turnover_cap"]))
    if target_return is not None:
        cons.append(expected_return_constraint(rho, target_return))

    return cons
