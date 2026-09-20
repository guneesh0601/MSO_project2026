"""Shared engine for the batch pipeline (main.py) and the CRM dashboard (app.py).

Two responsibilities:
  1. Data preparation: make sure raw downloads, processed return tables and
     forecasts exist, and load them.
  2. Solving: build one efficient frontier for one customer profile
     (solve_frontier) plus small helpers for displaying the result.

Nothing here mutates config; every tunable is a function argument that
defaults to the config value.
"""

import os
import sys
from functools import lru_cache

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import constraints
import data_loader
import forecasts
import frontier_builder
import returns_calculator
import risk_measures as rm
import rounding


class InfeasibleProfileError(ValueError):
    """The chosen limits leave (almost) no room to build a frontier."""


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------
def _raw_names() -> list[str]:
    """Names of every raw series the pipeline needs (file names in data/raw/)."""
    names = [n for n, spec in config.ASSETS.items() if spec["source"] in ("yfinance", "fred")]
    names += [f"BCH_{n}" for n in config.BENCHMARKS]
    names += ["FRED_IL_10Y_YIELD", "FRED_IL_CPI"]
    return names


def raw_data_missing() -> list[str]:
    return [
        n for n in _raw_names()
        if not os.path.exists(os.path.join(config.DATA_RAW_DIR, f"{n}.csv"))
    ]


def processed_data_stale() -> bool:
    """True if a processed file is missing, or benchmark_returns.csv does not
    yet have a column for every benchmark in config.BENCHMARKS."""
    r_path = os.path.join(config.DATA_PROCESSED_DIR, "asset_returns.csv")
    b_path = os.path.join(config.DATA_PROCESSED_DIR, "benchmark_returns.csv")
    f_path = os.path.join(config.DATA_PROCESSED_DIR, "forecasts.csv")
    if not all(os.path.exists(p) for p in (r_path, b_path, f_path)):
        return True
    header = set(pd.read_csv(b_path, nrows=0).columns)
    return not set(config.BENCHMARKS) <= header


def ensure_data() -> None:
    """Download and build whatever is missing. Safe to call repeatedly."""
    if raw_data_missing():
        data_loader.download_all_raw_data()   # skips files already on disk

    if processed_data_stale():
        r_table, _ = returns_calculator.build_and_save()
        forecasts_path = os.path.join(config.DATA_PROCESSED_DIR, "forecasts.csv")
        if not os.path.exists(forecasts_path):
            forecasts.build_and_save(r_table)

    load_inputs.cache_clear()


@lru_cache(maxsize=1)
def load_inputs() -> dict:
    r_table, bch_table = returns_calculator.load_processed()
    return {
        "r_table": r_table[config.ASSET_NAMES],
        "bch_table": bch_table,
        "rho": forecasts.load_forecasts()[config.ASSET_NAMES],
        "market_w": np.array([config.MARKET_PORTFOLIO[n] for n in config.ASSET_NAMES]),
    }


def data_window() -> tuple[pd.Timestamp, pd.Timestamp]:
    index = load_inputs()["r_table"].index
    return index.min(), index.max()


# ---------------------------------------------------------------------------
# Solving
# ---------------------------------------------------------------------------
MIN_RETURN_SPREAD = 1e-6   # below this the "frontier" is a single portfolio


def solve_frontier(risk_measure: str, benchmark: str, equity_cap: float,
                   liquidity_cap: float = None, currency_cap: float = None,
                   gamma: float = None, lambda_decay: float = None, K: int = None,
                   profile_id: str = "custom") -> pd.DataFrame:
    """Build one efficient frontier for one customer profile.

    Caps are fractions (0.55 = 55%). Any argument left as None takes its
    config.py default. Raises InfeasibleProfileError when the limits leave
    no room for more than one portfolio.
    """
    inputs = load_inputs()
    if liquidity_cap is None:
        liquidity_cap = config.LIQUIDITY_CAP_DEFAULT
    if currency_cap is None:
        currency_cap = config.CURRENCY_CAP_DEFAULT
    if lambda_decay is None:
        lambda_decay = config.LAMBDA_DECAY

    profile = {
        "profile_id": profile_id,
        "equity_cap": equity_cap,
        "liquidity_cap": liquidity_cap,
        "currency_cap": currency_cap,
        "turnover_cap": None,
    }
    weights = rm.decaying_weights(lambda_decay, config.T_MONTHS)
    message = (
        f"The limits (equity {equity_cap:.0%}, illiquid {liquidity_cap:.0%}, "
        f"foreign currency {currency_cap:.0%}) leave room for only one portfolio."
    )

    try:
        frontier = frontier_builder.build_frontier(
            risk_measure, profile, inputs["r_table"].values,
            inputs["bch_table"][benchmark].values, weights,
            inputs["market_w"], inputs["rho"].values, gamma=gamma, K=K,
        )
    except ValueError as exc:
        raise InfeasibleProfileError(message) from exc

    spread = frontier["achieved_return"].max() - frontier["achieved_return"].min()
    if spread < MIN_RETURN_SPREAD:
        raise InfeasibleProfileError(message)

    frontier["rounded_x"] = frontier["x"].apply(
        lambda x: rounding.largest_remainder_round(np.array(x), grid=0.01)
    )
    return frontier


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def annualized_risk(risk_score: float) -> float:
    """Convert a monthly risk score (a variance) to an annualized
    standard-deviation-style figure. A monotonic display transform only."""
    return float(np.sqrt(12.0 * max(risk_score, 0.0)))


def constraint_usage(x) -> dict:
    """Share of the portfolio in equities, foreign-currency and illiquid assets."""
    x = np.asarray(x, dtype=float)
    return {
        "equity": float(x[constraints.EQUITY_IDX].sum()),
        "foreign": float(x[constraints.FOREIGN_IDX].sum()),
        "illiquid": float(x[constraints.ILLIQUID_IDX].sum()),
    }


def compare_portfolios(current, proposed) -> pd.DataFrame:
    current = np.asarray(current, dtype=float)
    proposed = np.asarray(proposed, dtype=float)
    return pd.DataFrame({
        "asset": config.ASSET_NAMES,
        "current": current,
        "proposed": proposed,
        "trade": proposed - current,
    })


def portfolio_history(x, benchmark: str) -> pd.DataFrame:
    """Growth of 100 invested at the start of the 36-month window, for the
    portfolio and for the benchmark. Historical and in-sample."""
    inputs = load_inputs()
    portfolio = inputs["r_table"].values @ np.asarray(x, dtype=float)
    return pd.DataFrame(
        {
            "Portfolio": 100.0 * np.cumprod(1.0 + portfolio),
            "Benchmark": 100.0 * np.cumprod(1.0 + inputs["bch_table"][benchmark].values),
        },
        index=inputs["r_table"].index,
    )
