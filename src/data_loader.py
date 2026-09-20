"""Downloads raw monthly price/level data for every asset and benchmark.

This file does pure data-fetching only -- no return calculations, no
formulas. Every series is saved as its own CSV under data/raw/ so the
download step never needs to be repeated unless we want fresher data.

Two sources are used:
  - Yahoo Finance (via yfinance) for equities, ETFs, and FX rates.
  - FRED (via pandas_datareader) for Israeli CPI and interest-rate series.

Known limitation (verified, not hidden): the FRED series ISRCPIALLMINMEI
(Israeli CPI) stops updating around March 2025, well behind "today". This
loader simply fetches full available history for every series; the
alignment step in returns_calculator.py is responsible for finding the
most recent 36 months that all needed series actually have in common.
"""

import os
import sys
import datetime

import pandas as pd
import yfinance as yf
import pandas_datareader.data as web

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


def _raw_path(name: str) -> str:
    return os.path.join(config.DATA_RAW_DIR, f"{name}.csv")


def fetch_yfinance_monthly(ticker: str, years_back: int) -> pd.Series:
    """Fetch monthly adjusted-close data for one Yahoo Finance ticker."""
    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=365 * years_back)
    data = yf.download(
        ticker, start=start, end=end, interval="1mo",
        auto_adjust=True, progress=False,
    )
    if data.empty:
        raise ValueError(f"yfinance returned no data for ticker '{ticker}'")
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close.name = ticker
    return close.dropna()


def fetch_fred_monthly(series_id: str, years_back: int) -> pd.Series:
    """Fetch monthly data for one FRED series."""
    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=365 * years_back)
    data = web.DataReader(series_id, "fred", start, end)
    if data.empty:
        raise ValueError(f"FRED returned no data for series '{series_id}'")
    series = data.iloc[:, 0]
    series.index = pd.to_datetime(series.index)
    series.name = series_id
    return series.dropna()


def fetch_series(source: str, identifier: str, years_back: int) -> pd.Series:
    if source == "yfinance":
        return fetch_yfinance_monthly(identifier, years_back)
    if source == "fred":
        return fetch_fred_monthly(identifier, years_back)
    raise ValueError(f"Unknown data source '{source}'")


def download_all_raw_data(force: bool = False) -> None:
    """Download every series needed by config.ASSETS and config.BENCHMARKS,
    plus the extra FRED series used to derive the Israeli bond proxies,
    and save each one as its own CSV under data/raw/.
    """
    years_back = max(config.HISTORY_YEARS_BUFFER, config.T_MONTHS // 12 + 2)

    jobs = {}  # name -> (source, identifier)

    for name, spec in config.ASSETS.items():
        if spec["source"] in ("yfinance", "fred"):
            jobs[name] = (spec["source"], spec["id"])

    for name, spec in config.BENCHMARKS.items():
        jobs[f"BCH_{name}"] = (spec["source"], spec["id"])

    jobs["FRED_IL_10Y_YIELD"] = ("fred", config.FRED_IL_10Y_YIELD)
    jobs["FRED_IL_CPI"] = ("fred", config.FRED_IL_CPI)

    print(f"Downloading {len(jobs)} raw series (years_back={years_back})...")
    failures = []
    for name, (source, identifier) in jobs.items():
        out_path = _raw_path(name)
        if os.path.exists(out_path) and not force:
            print(f"  [skip]  {name:20s} already downloaded")
            continue
        try:
            series = fetch_series(source, identifier, years_back)
            series.to_frame(name="value").to_csv(out_path, index_label="date")
            print(f"  [ok]    {name:20s} {series.index.min().date()} -> "
                  f"{series.index.max().date()}  ({len(series)} points)")
        except Exception as exc:
            failures.append((name, str(exc)))
            print(f"  [FAIL]  {name:20s} {exc}")

    if failures:
        print("\nSome series failed to download:")
        for name, err in failures:
            print(f"  - {name}: {err}")
        raise RuntimeError(
            f"{len(failures)} series failed to download; see log above."
        )

    print("All raw data downloaded successfully.")


def load_raw_series(name: str) -> pd.Series:
    """Load a previously-downloaded raw series from data/raw/<name>.csv."""
    path = _raw_path(name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Raw data for '{name}' not found at {path}. "
            f"Run download_all_raw_data() first."
        )
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    return df["value"]


if __name__ == "__main__":
    download_all_raw_data()
