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
