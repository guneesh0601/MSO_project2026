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
    frontier = engine.solve_frontier("symmetric", "CPI")
    expected = pd.read_csv(
        os.path.join(config.OUTPUTS_FRONTIERS_DIR, "CPI__symmetric.csv")
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


# ---------------------------------------------------------------------------
# Multiple benchmarks (paper p. 41 / p. 47 risk measure 3)
# ---------------------------------------------------------------------------
def test_full_weight_on_one_benchmark_matches_the_plain_name():
    plain = engine.solve_frontier("symmetric", "CPI", 0.55)
    weighted = engine.solve_frontier("symmetric", {"CPI": 1.0}, 0.55)
    np.testing.assert_allclose(plain["risk"], weighted["risk"])
    np.testing.assert_allclose(np.vstack(plain["x"]), np.vstack(weighted["x"]))


def test_benchmark_series_is_the_weighted_sum():
    table = engine.load_inputs()["bch_table"]
    expected = 0.6 * table["CPI"].values + 0.4 * table["USD"].values
    np.testing.assert_allclose(engine.benchmark_series({"CPI": 0.6, "USD": 0.4}), expected)
    # a tuple of pairs (hashable, used as the UI's cache key) means the same thing
    np.testing.assert_allclose(engine.benchmark_series((("CPI", 0.6), ("USD", 0.4))), expected)


def test_benchmark_series_single_name_is_the_column():
    table = engine.load_inputs()["bch_table"]
    np.testing.assert_allclose(engine.benchmark_series("EUR"), table["EUR"].values)


@pytest.mark.parametrize("bad", [
    {"CPI": 0.5, "USD": 0.4},        # totals 90%
    {"CPI": 1.2, "USD": -0.2},       # negative weight
    {"NOPE": 1.0},                   # unknown benchmark
    {},                              # nothing chosen
])
def test_invalid_benchmark_weights_are_rejected(bad):
    with pytest.raises(ValueError):
        engine.benchmark_series(bad)


def test_blended_benchmark_changes_the_symmetric_frontier():
    single = engine.solve_frontier("symmetric", "CPI", 0.55)
    blend = engine.solve_frontier("symmetric", {"CPI": 0.5, "USD": 0.5}, 0.55)
    assert not np.allclose(single["risk"].values, blend["risk"].values)


def test_markowitz_ignores_the_benchmark():
    a = engine.solve_frontier("markowitz", "CPI", 0.55)
    b = engine.solve_frontier("markowitz", "USD", 0.55)
    np.testing.assert_allclose(a["risk"].values, b["risk"].values)


def test_portfolio_history_uses_the_blended_benchmark():
    x = np.full(config.N_ASSETS, 1.0 / config.N_ASSETS)
    history = engine.portfolio_history(x, {"CPI": 0.5, "USD": 0.5})
    table = engine.load_inputs()["bch_table"]
    blended = 0.5 * table["CPI"].values + 0.5 * table["USD"].values
    np.testing.assert_allclose(history["Benchmark"].values, 100.0 * np.cumprod(1.0 + blended))


def test_monthly_returns_are_portfret_and_bchret():
    x = np.full(config.N_ASSETS, 1.0 / config.N_ASSETS)
    monthly = engine.monthly_returns(x, {"CPI": 0.5, "USD": 0.5})
    inputs = engine.load_inputs()
    table = inputs["bch_table"]
    np.testing.assert_allclose(monthly["Portfolio"].values, inputs["r_table"].values @ x)
    np.testing.assert_allclose(
        monthly["Benchmark"].values, 0.5 * table["CPI"].values + 0.5 * table["USD"].values
    )
    assert list(monthly.columns) == ["Portfolio", "Benchmark"]
    assert len(monthly) == config.T_MONTHS


# ---------------------------------------------------------------------------
# Risk level picks the frontier point; there is no equity cap by default
# ---------------------------------------------------------------------------
def test_frontier_position_spreads_the_five_levels_evenly():
    levels = config.RISK_LEVEL_CHOICES
    assert [engine.frontier_position(level, 12) for level in levels] == [1, 4, 7, 9, 12]
    assert [engine.frontier_position(level, 5) for level in levels] == [1, 2, 3, 4, 5]
    assert engine.frontier_position("low", 30) == 1
    assert engine.frontier_position("high", 30) == 30


def test_frontier_position_is_always_a_valid_point():
    for n_points in range(2, 33):
        for level in config.RISK_LEVEL_CHOICES:
            assert 1 <= engine.frontier_position(level, n_points) <= n_points


def test_no_equity_cap_by_default():
    default = engine.solve_frontier("symmetric", "CPI")
    explicit_no_cap = engine.solve_frontier("symmetric", "CPI", 1.0)
    np.testing.assert_allclose(default["risk"], explicit_no_cap["risk"])
    # with no cap the maximum-return end is 100% in the highest-forecast asset (Euro equities)
    top = np.array(default.loc[default["point"] == "max_return", "x"].iloc[0])
    assert top[config.ASSET_NAMES.index("EU_Equity")] > 0.99


def test_constraints_do_not_require_an_equity_cap():
    import constraints as cons_mod
    rho = engine.load_inputs()["rho"].values
    cons = cons_mod.build_constraints({"liquidity_cap": 0.4, "currency_cap": 1.0}, rho)
    assert len(cons) == 3          # budget + liquidity + currency
    with_cap = cons_mod.build_constraints(
        {"equity_cap": 0.5, "liquidity_cap": 0.4, "currency_cap": 1.0}, rho)
    assert len(with_cap) == 4
