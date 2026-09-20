"""Wraps scipy.optimize.minimize -- this file plays the role GAMS+MINOS
played in the original paper, minus the modeling-language layer: we just
hand scipy a plain Python objective function and a list of constraints,
and let its internal gradient-based search (SLSQP) do the work described
in loop.md as "Loop C".

Implements the three problem types from the paper's Appendix:
  - solve_min_risk   : Step 1 (lowest-risk portfolio, ignore return)
  - solve_max_return : Step 2 (highest-return portfolio, ignore risk)
  - solve_target_return : Step 4 (minimize risk s.t. ExpRet = target),
                          run once per intermediate frontier point.
"""

import numpy as np
from scipy.optimize import minimize

import constraints as cons_mod
import objective as obj_mod
import risk_measures as rm


def _equal_weights(n_assets: int) -> np.ndarray:
    return np.full(n_assets, 1.0 / n_assets)


def solve_min_risk(risk_measure, returns_table, benchmark_series, weights,
                    market_weights, gamma, profile, rho, n_assets, x0=None):
    if x0 is None:
        x0 = _equal_weights(n_assets)

    f = obj_mod.build_objective(risk_measure, returns_table, benchmark_series,
                                 weights, market_weights, gamma)
    con_list = cons_mod.build_constraints(profile, rho, target_return=None)
    bounds = cons_mod.bounds_no_short_selling(n_assets)

    result = minimize(f, x0, method="SLSQP", bounds=bounds,
                       constraints=con_list, options={"maxiter": 500, "ftol": 1e-12})
    x = result.x
    return {
        "x": x,
        "success": result.success,
        "message": result.message,
        "risk": rm.compute_risk(risk_measure, x, returns_table, benchmark_series, weights),
        "expected_return": rm.expected_return(x, rho),
    }


def solve_max_return(profile, rho, n_assets, x0=None):
    if x0 is None:
        x0 = _equal_weights(n_assets)

    f = obj_mod.build_negative_expected_return(rho)
    con_list = cons_mod.build_constraints(profile, rho, target_return=None)
    bounds = cons_mod.bounds_no_short_selling(n_assets)

    result = minimize(f, x0, method="SLSQP", bounds=bounds,
                       constraints=con_list, options={"maxiter": 500, "ftol": 1e-12})
    x = result.x
    return {
        "x": x,
        "success": result.success,
        "message": result.message,
        "expected_return": rm.expected_return(x, rho),
    }


def solve_target_return(risk_measure, returns_table, benchmark_series, weights,
                         market_weights, gamma, profile, rho, target_return,
                         n_assets, x0=None):
    if x0 is None:
        x0 = _equal_weights(n_assets)

    f = obj_mod.build_objective(risk_measure, returns_table, benchmark_series,
                                 weights, market_weights, gamma)
    con_list = cons_mod.build_constraints(profile, rho, target_return=target_return)
    bounds = cons_mod.bounds_no_short_selling(n_assets)

    result = minimize(f, x0, method="SLSQP", bounds=bounds,
                       constraints=con_list, options={"maxiter": 500, "ftol": 1e-12})
    x = result.x
    return {
        "x": x,
        "success": result.success,
        "message": result.message,
        "risk": rm.compute_risk(risk_measure, x, returns_table, benchmark_series, weights),
        "expected_return": rm.expected_return(x, rho),
        "target_return": target_return,
    }
