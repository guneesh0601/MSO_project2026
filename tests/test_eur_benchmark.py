"""Checks that the Euro benchmark (the paper's 4th) is wired through config and the processed data."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import config
import returns_calculator


def test_eur_benchmark_is_configured():
    assert config.BENCHMARKS["EUR"]["id"] == "EURILS=X"
    assert config.BENCHMARKS["EUR"]["source"] == "yfinance"
    assert "EUR" in config.BENCHMARK_CHOICES


def test_benchmark_choices_match_benchmarks():
    assert set(config.BENCHMARK_CHOICES) == set(config.BENCHMARKS)


def test_processed_benchmarks_include_eur():
    _, bch = returns_calculator.load_processed()
    assert "EUR" in bch.columns
    assert len(bch) == config.T_MONTHS
    assert not bch["EUR"].isna().any()
