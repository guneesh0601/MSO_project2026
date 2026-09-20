"""Turns raw downloaded prices/rates into the r_{t,i} returns table and the
benchmark return series (BchRet).

Formulas used (all explained in plain English in ExpRet_Constraint_Explained.md
and the earlier project conversation):

  Simple return from a price series:
      r_t = (Price_t - Price_{t-1}) / Price_{t-1}

  Rate-quoted assets (cash, deposits, the interest-rate benchmark):
  these are already an annualized percentage rate, not a price, so the
  monthly return is just that rate converted to a monthly figure:
      r_t = (rate_t / 100) / 12

  Israeli government bonds (no clean free price series available -- see
  Data_Sources_Plan.md, item 8): approximated from the 10-year government
  bond YIELD series using a standard duration-based conversion:
      r_t = (yield_t / 100) / 12  -  duration * ((yield_t - yield_{t-1}) / 100)
  The first term is the "carry" (income you'd earn from holding a bond at
  that yield for a month); the second term is the approximate price change
  caused by the yield moving, using modified duration. This is a clearly
  labeled approximation, not an observed market price.

  CPI-linked variant: the unlinked-bond approximation above, PLUS that
  month's realized CPI inflation added on top (since CPI-linked bonds are
  designed to compensate holders for inflation in addition to their real
  yield). This is also a labeled approximation.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import data_loader


def simple_return(price: pd.Series) -> pd.Series:
    return price.pct_change().dropna()


def rate_to_monthly_return(rate_percent: pd.Series) -> pd.Series:
    return (rate_percent / 100.0) / 12.0


def bond_return_from_yield(yield_percent: pd.Series, duration_years: float) -> pd.Series:
    yield_decimal = yield_percent / 100.0
    carry = yield_decimal / 12.0
    yield_change = yield_decimal.diff()
    price_effect = -duration_years * yield_change
    total = (carry + price_effect).dropna()
    return total


def build_asset_returns() -> pd.DataFrame:
    """Build the full r_{t,i} table: rows = months (ascending date order),
    columns = asset names in config.ASSET_NAMES order.
    """
    columns = {}

    for name, spec in config.ASSETS.items():
        kind = spec["kind"]

        if spec["source"] == "yfinance":
            price = data_loader.load_raw_series(name)
            columns[name] = simple_return(price)

        elif spec["source"] == "fred" and kind == "cash":
            rate = data_loader.load_raw_series(name)
            columns[name] = rate_to_monthly_return(rate)

        elif spec["source"] == "derived" and name == "IL_Bond_Unlinked":
            yield_series = data_loader.load_raw_series("FRED_IL_10Y_YIELD")
            columns[name] = bond_return_from_yield(
                yield_series, config.ASSUMED_BOND_DURATION_YEARS
            )

        elif spec["source"] == "derived" and name == "IL_Bond_Linked":
            yield_series = data_loader.load_raw_series("FRED_IL_10Y_YIELD")
            unlinked = bond_return_from_yield(
                yield_series, config.ASSUMED_BOND_DURATION_YEARS
            )
            cpi = data_loader.load_raw_series("FRED_IL_CPI")
            cpi_inflation = simple_return(cpi)
            combined = unlinked.add(cpi_inflation, fill_value=0.0)
            columns[name] = combined.dropna()

        else:
            raise ValueError(f"Don't know how to build returns for asset '{name}'")

    table = pd.DataFrame(columns)
    table = table.sort_index()
    return table


def build_benchmark_returns() -> pd.DataFrame:
    """Build the BchRet series for every benchmark in config.BENCHMARKS."""
    columns = {}

    for name, spec in config.BENCHMARKS.items():
        raw = data_loader.load_raw_series(f"BCH_{name}")
        if name in ("CPI", "USD"):
            columns[name] = simple_return(raw)
        elif name == "ILS_RATE":
            columns[name] = rate_to_monthly_return(raw)
        else:
            raise ValueError(f"Don't know how to build benchmark returns for '{name}'")

    table = pd.DataFrame(columns)
    table = table.sort_index()
    return table


def align_and_trim(asset_returns: pd.DataFrame, benchmark_returns: pd.DataFrame,
                    t_months: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Find the common date range both tables actually have data for, drop
    any rows with missing values in either table, and keep only the most
    recent t_months rows. Rows stay in ascending chronological order
    (oldest first, most recent last).
    """
    combined = asset_returns.join(benchmark_returns, how="inner")
    combined = combined.dropna()

    if len(combined) < t_months:
        raise ValueError(
            f"Only {len(combined)} months of fully-overlapping data available, "
            f"need {t_months}. The binding constraint is almost certainly the "
            f"Israeli CPI series (see Data_Sources_Plan.md) -- reduce T_MONTHS "
            f"in config.py or find a fresher CPI source."
        )

    trimmed = combined.iloc[-t_months:]
    n_assets = asset_returns.shape[1]
    return trimmed.iloc[:, :n_assets], trimmed.iloc[:, n_assets:]


def build_and_save() -> tuple[pd.DataFrame, pd.DataFrame]:
    asset_returns = build_asset_returns()
    benchmark_returns = build_benchmark_returns()

    print(f"Asset returns before alignment: {asset_returns.shape[0]} rows, "
          f"{asset_returns.index.min().date()} -> {asset_returns.index.max().date()}")
    print(f"Benchmark returns before alignment: {benchmark_returns.shape[0]} rows, "
          f"{benchmark_returns.index.min().date()} -> {benchmark_returns.index.max().date()}")

    r_table, bch_table = align_and_trim(asset_returns, benchmark_returns, config.T_MONTHS)

    print(f"After alignment and trimming to last {config.T_MONTHS} common months: "
          f"{r_table.index.min().date()} -> {r_table.index.max().date()}")

    r_path = os.path.join(config.DATA_PROCESSED_DIR, "asset_returns.csv")
    bch_path = os.path.join(config.DATA_PROCESSED_DIR, "benchmark_returns.csv")
    r_table.to_csv(r_path, index_label="date")
    bch_table.to_csv(bch_path, index_label="date")
    print(f"Saved: {r_path}")
    print(f"Saved: {bch_path}")

    return r_table, bch_table


def load_processed() -> tuple[pd.DataFrame, pd.DataFrame]:
    r_path = os.path.join(config.DATA_PROCESSED_DIR, "asset_returns.csv")
    bch_path = os.path.join(config.DATA_PROCESSED_DIR, "benchmark_returns.csv")
    r_table = pd.read_csv(r_path, index_col="date", parse_dates=True)
    bch_table = pd.read_csv(bch_path, index_col="date", parse_dates=True)
    return r_table, bch_table


if __name__ == "__main__":
    build_and_save()
