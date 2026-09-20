"""Tests for engine.solve_frontier and the display helpers."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import config
import engine

# Distinct shares so a mixed-up index would be caught:
# equity (IL+US+EU) = 0.35, foreign (US+EU+Foreign_Bond) = 0.45, illiquid (both IL bonds) = 0.40
X = np.array([0.05, 0.20, 0.10, 0.15, 0.25, 0.15, 0.10])


def test_default_frontier_matches_batch_csv():
    frontier = engine.solve_frontier(
        "symmetric", "CPI", config.RISK_CATEGORY_EQUITY_CAP["medium"]
    )
    expected = pd.read_csv(
        os.path.join(config.OUTPUTS_FRONTIERS_DIR, "medium__CPI__symmetric.csv")
    )
    assert list(frontier["point"]) == list(expected["point"])
    np.testing.assert_allclose(frontier["risk"], expected["risk"], rtol=1e-6, atol=1e-12)
    np.testing.assert_allclose(frontier["achieved_return"], expected["achieved_return"], rtol=1e-6)
    np.testing.assert_allclose(
        np.vstack(frontier["x"]), expected[config.ASSET_NAMES].values, atol=1e-5
    )


def test_frontier_has_k_plus_two_points_and_rounded_weights():
    frontier = engine.solve_frontier("markowitz", "USD", 0.55, K=4)
    assert len(frontier) == 6
    for rounded in frontier["rounded_x"]:
        assert abs(np.sum(rounded) - 1.0) < 1e-9


def test_higher_equity_cap_never_lowers_max_return():
    low = engine.solve_frontier("symmetric", "CPI", 0.20)
    high = engine.solve_frontier("symmetric", "CPI", 0.75)
    max_low = low.loc[low["point"] == "max_return", "achieved_return"].iloc[0]
    max_high = high.loc[high["point"] == "max_return", "achieved_return"].iloc[0]
    assert max_high >= max_low - 1e-9


def test_gamma_changes_the_min_risk_portfolio():
    a = engine.solve_frontier("symmetric", "CPI", 0.55, gamma=0.0)
    b = engine.solve_frontier("symmetric", "CPI", 0.55, gamma=0.5)
    xa, xb = np.array(a.iloc[0]["x"]), np.array(b.iloc[0]["x"])
    assert np.max(np.abs(xa - xb)) > 1e-4


def test_eur_benchmark_solves():
    frontier = engine.solve_frontier("asymmetric", "EUR", 0.55)
    assert frontier["success"].all()


def test_all_zero_limits_raise_infeasible():
    with pytest.raises(engine.InfeasibleProfileError):
        engine.solve_frontier("symmetric", "CPI", 0.0, liquidity_cap=0.0, currency_cap=0.0)


def test_annualized_risk():
    assert engine.annualized_risk(0.0) == 0.0
    assert engine.annualized_risk(1.0 / 12.0) == pytest.approx(1.0)
    assert engine.annualized_risk(-1e-18) == 0.0


def test_constraint_usage():
    usage = engine.constraint_usage(X)
    assert usage["equity"] == pytest.approx(0.35)
    assert usage["foreign"] == pytest.approx(0.45)
    assert usage["illiquid"] == pytest.approx(0.40)


def test_compare_portfolios():
    current = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    table = engine.compare_portfolios(current, X)
    assert list(table.columns) == ["asset", "current", "proposed", "trade"]
    assert list(table["asset"]) == config.ASSET_NAMES
    assert table["trade"].iloc[-1] == pytest.approx(-0.90)   # Cash: 0.10 - 1.00
    assert table["trade"].abs().sum() == pytest.approx(1.8)


def test_portfolio_history_single_asset():
    x = np.zeros(config.N_ASSETS)
    x[config.ASSET_NAMES.index("IL_Equity")] = 1.0
    history = engine.portfolio_history(x, "CPI")
    inputs = engine.load_inputs()
    expected = 100.0 * (1.0 + inputs["r_table"]["IL_Equity"]).cumprod()
    np.testing.assert_allclose(history["Portfolio"].values, expected.values)
    assert list(history.columns) == ["Portfolio", "Benchmark"]
    assert len(history) == config.T_MONTHS
