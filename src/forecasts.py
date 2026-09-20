"""Builds the expected-future-return forecast vector, rho.

IMPORTANT, as emphasized throughout this project's planning docs: rho is
NOT simply "the historical average return." The paper is explicit that
forecasts come from the bank's own forecasting committee, independent of
the historical data used for risk measurement. We don't have that
committee, so we use a simple, clearly documented substitute rule:

    rho_i (annual) = w * (annualized historical mean return of asset i)
                     + (1 - w) * (current risk-free rate + a premium
                                   that depends on the asset's kind)

with w = 0.5 (an even blend, our own assumption). The second half of the
blend anchors the forecast to a sensible risk/return ordering (equities
should be forecast to earn more than cash) even if the recent historical
window happened to be unusually good or bad for some asset class.

This file is intentionally simple and clearly labeled as an assumption,
per Reproduction_Plan.md, Section 9.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

BLEND_WEIGHT_HISTORICAL = 0.5

PREMIUM_BY_KIND = {
    "equity": 0.05,   # +5% over the risk-free rate, annualized
    "bond": 0.015,    # +1.5% over the risk-free rate, annualized
    "cash": 0.0,      # cash earns approximately the risk-free rate itself
}


def annualize_monthly_mean(monthly_mean_return: float) -> float:
    return (1.0 + monthly_mean_return) ** 12 - 1.0


def build_forecasts(asset_returns: pd.DataFrame) -> pd.Series:
    """Returns a pandas Series indexed by asset name, giving the annual
    expected-return forecast rho_i for every asset in config.ASSET_NAMES.
    """
    monthly_means = asset_returns.mean(axis=0)
    annualized_hist = monthly_means.apply(annualize_monthly_mean)

    cash_annual_hist = annualized_hist["Cash"]
    risk_free_rate = cash_annual_hist

    rho = {}
    for name in config.ASSET_NAMES:
        kind = config.ASSETS[name]["kind"]
        premium_anchor = risk_free_rate + PREMIUM_BY_KIND[kind]
        blended = (
            BLEND_WEIGHT_HISTORICAL * annualized_hist[name]
            + (1 - BLEND_WEIGHT_HISTORICAL) * premium_anchor
        )
        rho[name] = blended

    return pd.Series(rho)[config.ASSET_NAMES]


def build_and_save(asset_returns: pd.DataFrame) -> pd.Series:
    rho = build_forecasts(asset_returns)
    out_path = os.path.join(config.DATA_PROCESSED_DIR, "forecasts.csv")
    rho.to_frame(name="rho_annual").to_csv(out_path, index_label="asset")
    print(f"Saved forecasts to {out_path}")
    print(rho.apply(lambda x: f"{x:+.2%}"))
    return rho


def load_forecasts() -> pd.Series:
    path = os.path.join(config.DATA_PROCESSED_DIR, "forecasts.csv")
    df = pd.read_csv(path, index_col="asset")
    return df["rho_annual"]


if __name__ == "__main__":
    import returns_calculator
    r_table, _ = returns_calculator.load_processed()
    build_and_save(r_table)
