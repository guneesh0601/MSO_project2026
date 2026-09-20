"""Tests for engine's data-gap detection. No network: uses temp dirs."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import config
import engine


def test_raw_data_missing_reports_absent_benchmark(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_RAW_DIR", str(tmp_path))
    for name in engine._raw_names():
        if name != "BCH_EUR":
            (tmp_path / f"{name}.csv").write_text("date,value\n")
    assert engine.raw_data_missing() == ["BCH_EUR"]


def _write_processed(tmp_path, benchmark_header):
    (tmp_path / "asset_returns.csv").write_text("date,IL_Equity\n")
    (tmp_path / "benchmark_returns.csv").write_text(f"{benchmark_header}\n")
    (tmp_path / "forecasts.csv").write_text("asset,rho_annual\n")


def test_processed_data_stale_when_benchmark_column_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_PROCESSED_DIR", str(tmp_path))
    _write_processed(tmp_path, "date,CPI,USD,ILS_RATE")
    assert engine.processed_data_stale() is True


def test_processed_data_fresh_when_all_benchmarks_present(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_PROCESSED_DIR", str(tmp_path))
    _write_processed(tmp_path, "date,CPI,USD,ILS_RATE,EUR")
    assert engine.processed_data_stale() is False


def test_processed_data_stale_when_files_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_PROCESSED_DIR", str(tmp_path))
    assert engine.processed_data_stale() is True


def test_real_data_directory_is_complete():
    assert engine.raw_data_missing() == []
    assert engine.processed_data_stale() is False


def test_load_inputs_shapes_and_order():
    inputs = engine.load_inputs()
    assert list(inputs["r_table"].columns) == config.ASSET_NAMES
    assert len(inputs["r_table"]) == config.T_MONTHS
    assert len(inputs["bch_table"]) == config.T_MONTHS
    assert list(inputs["rho"].index) == config.ASSET_NAMES
    assert abs(inputs["market_w"].sum() - 1.0) < 1e-9


def test_data_window_is_ordered():
    start, end = engine.data_window()
    assert start < end
