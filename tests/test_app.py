"""Headless UI tests using Streamlit's AppTest. No browser needed."""

import os
import sys

from streamlit.testing.v1 import AppTest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
import config
import ui_labels

APP = os.path.join(ROOT, "src", "app.py")


def _run() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    return at


def _metric(at: AppTest, label: str) -> str:
    return [m for m in at.metric if m.label == label][0].value


def test_labels_cover_every_config_key():
    assert set(ui_labels.ASSETS) == set(config.ASSET_NAMES)
    assert set(ui_labels.BENCHMARKS) == set(config.BENCHMARK_CHOICES)
    assert set(ui_labels.RISK_LEVELS) == set(config.RISK_LEVEL_CHOICES)
    assert set(ui_labels.RISK_MEASURES) == set(config.RISK_MEASURES)


def test_discrete_level_lists_contain_the_defaults():
    assert config.LIQUIDITY_CAP_DEFAULT in config.LIQUIDITY_LEVELS
    assert config.CURRENCY_CAP_DEFAULT in config.CURRENCY_LEVELS


def test_app_loads_with_config_defaults():
    at = _run()
    assert not at.exception
    assert at.select_slider(key="risk_level").value == "medium"
    assert at.slider(key="equity_cap").value == 55      # 'medium' preset
    assert at.select_slider(key="liquidity_cap").value == 40
    assert at.select_slider(key="currency_cap").value == 100
    assert at.selectbox(key="benchmark").value == "CPI"
    assert at.multiselect(key="risk_measures").value == list(config.RISK_MEASURES)


def test_discrete_sliders_offer_only_the_configured_stops():
    at = _run()
    assert len(at.select_slider(key="risk_level").options) == len(config.RISK_LEVEL_CHOICES)
    assert len(at.select_slider(key="liquidity_cap").options) == len(config.LIQUIDITY_LEVELS)
    assert len(at.select_slider(key="currency_cap").options) == len(config.CURRENCY_LEVELS)


def test_risk_level_preset_sets_equity_slider():
    at = _run()
    at.select_slider(key="risk_level").set_value("low").run()
    assert not at.exception
    assert at.slider(key="equity_cap").value == 20


def test_slider_can_override_the_preset():
    at = _run()
    at.slider(key="equity_cap").set_value(63).run()
    assert not at.exception
    assert at.slider(key="equity_cap").value == 63
    assert at.select_slider(key="risk_level").value == "medium"


def test_changing_equity_cap_changes_the_recommendation():
    at = _run()
    before = _metric(at, "Expected annual return")
    at.slider(key="equity_cap").set_value(10).run()
    assert not at.exception
    assert _metric(at, "Expected annual return") != before


def test_reset_restores_defaults():
    at = _run()
    at.slider(key="equity_cap").set_value(90).run()
    at.select_slider(key="liquidity_cap").set_value(20).run()
    at.button(key="reset").click().run()
    assert at.slider(key="equity_cap").value == 55
    assert at.select_slider(key="liquidity_cap").value == 40


def test_infeasible_limits_show_message_not_traceback():
    at = _run()
    at.slider(key="equity_cap").set_value(0)
    at.select_slider(key="liquidity_cap").set_value(0)
    at.select_slider(key="currency_cap").set_value(0)
    at.run()
    assert not at.exception
    assert any("only one portfolio" in e.value for e in at.error)


def test_history_tab_shows_portfolio_and_benchmark_totals():
    at = _run()
    assert not at.exception
    assert _metric(at, "Portfolio, total over window").endswith("%")
    assert _metric(at, "Benchmark, total over window").endswith("%")


def test_current_portfolio_not_summing_to_100_shows_message():
    at = _run()
    at.number_input(key="cur_IL_Equity").set_value(30).run()
    assert not at.exception
    assert any("100%" in e.value for e in at.error)


def test_current_portfolio_summing_to_100_shows_total_change():
    at = _run()
    at.number_input(key="cur_Cash").set_value(100).run()
    assert not at.exception
    assert not at.error
    assert _metric(at, "Total change (sum of absolute weight changes)").endswith("%")
