# Opti-Money CRM Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Streamlit dashboard for bank relationship managers (CRM) that solves and displays an Opti-Money efficient frontier live from interactive controls (including a slider-based equity cap), and add the paper's 4th (Euro) benchmark.

**Architecture:** A new `src/engine.py` holds data preparation and `solve_frontier(...)`, a thin wrapper over the existing `frontier_builder.build_frontier`. Both `main.py` (batch) and the new `src/app.py` (UI) call it, so they share one code path. The UI never mutates `config` globals; every control starts at its `config.py` default.

**Tech Stack:** Python, numpy, pandas, scipy (existing); Streamlit + Altair (new UI); pytest (dev only, for tests).

**Spec:** `docs/superpowers/specs/2026-09-20-crm-streamlit-ui-design.md`

## Global Constraints

- Run all commands from the project root `c:/Users/Guneesh Gupta/MSO project`. Commands are written for Git Bash (the Bash tool); in Windows PowerShell 5.1 replace `&&` with `;`.
- Streamlit app entry point is `src/app.py`, started with `streamlit run src/app.py`.
- Nothing the CRM types is persisted; no files are written by the UI (downloads are browser downloads only).
- The UI must not mutate `config` globals. `gamma`, `K`, `lambda_decay` are passed as function arguments.
- Every UI default comes from an existing `config.py` constant (`RISK_CATEGORY_EQUITY_CAP`, `LIQUIDITY_CAP_DEFAULT`, `CURRENCY_CAP_DEFAULT`, `GAMMA_TRACKING`, `LAMBDA_DECAY`, `K_FRONTIER_POINTS`). The only UI-owned defaults are risk level `"medium"` and benchmark `"CPI"`.
- Discrete customer answers (risk level, liquidity limit, currency limit) use `st.select_slider`, so a released handle always rests on a valid stop (dropping it between stops snaps to the nearest one). The allowed stops live in `config.LIQUIDITY_LEVELS` and `config.CURRENCY_LEVELS` (the paper says only "a few discrete levels", so the values are a documented assumption, like the category equity caps) and must contain the existing defaults. The equity cap stays a free 0-100 slider (whole percentages) as the CRM's fine-tuning override of the risk-level preset.
- Euro benchmark key is `"EUR"`, Yahoo ticker `EURILS=X`, source `yfinance`.
- `config.py` keeps model identifiers only; friendly display names live in `src/ui_labels.py`.
- With all-default inputs, `engine.solve_frontier("symmetric", "CPI", 0.55)` must reproduce the existing `outputs/frontiers/medium__CPI__symmetric.csv`.
- Footer text, verbatim: `Illustrative reproduction built on public proxy data (Yahoo Finance, FRED); not investment advice.`
- New dependency: `streamlit` (Altair ships with it). `pytest` is dev-only.
- Every commit message ends with the trailer `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` (pass it as a second `-m`).
- Data note: the Israeli CPI series stops around March 2025, so the 36-month window ends then. This is existing behavior; the UI shows the actual window dates.

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/config.py` | modify | add `EUR` benchmark + choice |
| `src/returns_calculator.py` | modify | treat `EUR` like `CPI`/`USD` |
| `src/engine.py` | create | data prep (`ensure_data` etc.), `solve_frontier`, display helpers |
| `src/main.py` | modify | batch run through `engine` |
| `src/ui_labels.py` | create | friendly labels for assets, benchmarks, risk levels, risk measures |
| `src/app.py` | create | Streamlit UI only |
| `tests/test_eur_benchmark.py` | create | EUR config + data checks |
| `tests/test_engine_data.py` | create | data-gap detection (no network) |
| `tests/test_engine_solve.py` | create | solve regression + helpers |
| `tests/test_app.py` | create | headless `AppTest` UI tests |
| `README.md`, spec | modify | run instructions, spec amendments |

---

### Task 1: Euro benchmark

**Files:**
- Modify: `src/config.py:55-59` and `src/config.py:103`
- Modify: `src/returns_calculator.py:105`
- Test: `tests/test_eur_benchmark.py`

**Interfaces:**
- Produces: `config.BENCHMARKS["EUR"]`, `"EUR"` in `config.BENCHMARK_CHOICES`, and a processed `data/processed/benchmark_returns.csv` with columns `CPI, USD, ILS_RATE, EUR` (36 rows). Later tasks rely on the `"EUR"` column.

- [ ] **Step 1: Make sure pytest is available**

Run: `python -m pytest --version`
If it reports "No module named pytest": `pip install pytest`

- [ ] **Step 2: Write the failing test**

Create `tests/test_eur_benchmark.py`:

```python
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
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python -m pytest tests/test_eur_benchmark.py -v`
Expected: 3 FAIL (`KeyError: 'EUR'` / assertion errors).

- [ ] **Step 4: Implement**

In `src/config.py`, replace the `BENCHMARKS` block:

```python
BENCHMARKS = {
    "CPI":       {"source": "fred",     "id": "ISRCPIALLMINMEI"},
    "USD":       {"source": "yfinance", "id": "USDILS=X"},
    "ILS_RATE":  {"source": "fred",     "id": "IR3TIB01ILM156N"},
    "EUR":       {"source": "yfinance", "id": "EURILS=X"},
}
```

and replace the `BENCHMARK_CHOICES` line:

```python
BENCHMARK_CHOICES = ["CPI", "USD", "ILS_RATE", "EUR"]
```

In `src/returns_calculator.py`, change the branch in `build_benchmark_returns`:

```python
        if name in ("CPI", "USD", "EUR"):
            columns[name] = simple_return(raw)
```

- [ ] **Step 5: Download the EUR series and rebuild the processed benchmark file**

Run (the first command skips files already on disk, so it only fetches `BCH_EUR.csv`):

```
python src/data_loader.py
python src/returns_calculator.py
```

Expected: `[ok]    BCH_EUR ...` in the first output; the second prints "After alignment and trimming to last 36 common months" and saves both files.

- [ ] **Step 6: Run the tests and check nothing else in the data changed**

Run: `python -m pytest tests/test_eur_benchmark.py -v`
Expected: 3 PASS.

Run: `git status --short data`
Expected: `data/raw/BCH_EUR.csv` new (untracked) and `data/processed/benchmark_returns.csv` modified. `data/processed/asset_returns.csv` must NOT appear as modified (the window is unchanged). If it does, stop and investigate before continuing.

- [ ] **Step 7: Commit**

```bash
git add src/config.py src/returns_calculator.py tests/test_eur_benchmark.py data/raw/BCH_EUR.csv data/processed/benchmark_returns.csv
git commit -m "feat: add Euro (EUR/ILS) as the paper's 4th benchmark" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Engine data layer

**Files:**
- Create: `src/engine.py`
- Test: `tests/test_engine_data.py`

**Interfaces:**
- Produces (all in `src/engine.py`):
  - `raw_data_missing() -> list[str]`: names of required raw series with no CSV in `config.DATA_RAW_DIR`.
  - `processed_data_stale() -> bool`: True if any processed file is missing or `benchmark_returns.csv` lacks a benchmark column.
  - `ensure_data() -> None`: downloads/builds whatever is missing, then clears the `load_inputs` cache.
  - `load_inputs() -> dict` with keys `"r_table"` (DataFrame, columns in `config.ASSET_NAMES` order), `"bch_table"` (DataFrame), `"rho"` (Series indexed by asset), `"market_w"` (ndarray); cached.
  - `data_window() -> tuple[pd.Timestamp, pd.Timestamp]`: first and last month of the 36-month window.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_data.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_engine_data.py -v`
Expected: FAIL/ERROR (`ModuleNotFoundError: No module named 'engine'`).

- [ ] **Step 3: Implement the data layer**

Create `src/engine.py`:

```python
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
```

- [ ] **Step 4: Run to verify they pass**

Run: `python -m pytest tests/test_engine_data.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/engine.py tests/test_engine_data.py
git commit -m "feat: add engine data layer with benchmark-aware data checks" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Engine solving and display helpers

**Files:**
- Modify: `src/engine.py` (append after `data_window`)
- Test: `tests/test_engine_solve.py`

**Interfaces:**
- Consumes: `load_inputs()`, `InfeasibleProfileError` from Task 2.
- Produces (in `src/engine.py`):
  - `solve_frontier(risk_measure: str, benchmark: str, equity_cap: float, liquidity_cap: float | None = None, currency_cap: float | None = None, gamma: float | None = None, lambda_decay: float | None = None, K: int | None = None, profile_id: str = "custom") -> pd.DataFrame`. Caps are fractions (0.55 = 55%); `None` means the config default. Columns: `point, target_return, achieved_return, risk, success, x, rounded_x`; rows in solve order (`min_risk`, `max_return`, `k=1..K`). Raises `InfeasibleProfileError`.
  - `annualized_risk(risk_score: float) -> float`: `sqrt(12 * risk)`.
  - `constraint_usage(x) -> dict` with keys `"equity"`, `"foreign"`, `"illiquid"` (fractions).
  - `compare_portfolios(current, proposed) -> pd.DataFrame` with columns `asset, current, proposed, trade`.
  - `portfolio_history(x, benchmark: str) -> pd.DataFrame` indexed by month with columns `Portfolio`, `Benchmark` (growth of 100).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_solve.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_engine_solve.py -v`
Expected: all FAIL (`AttributeError: module 'engine' has no attribute 'solve_frontier'`).

- [ ] **Step 3: Implement**

Append to `src/engine.py`:

```python


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
```

- [ ] **Step 4: Run to verify they pass**

Run: `python -m pytest tests/test_engine_solve.py -v`
Expected: 10 PASS.

If `test_all_zero_limits_raise_infeasible` does not raise, print `engine.solve_frontier` internals for those caps (`achieved_return` spread) and adjust `MIN_RETURN_SPREAD` or the check; do not loosen the test. If `test_default_frontier_matches_batch_csv` fails on weights only, compare `rtol`/`atol` against the size of the mismatch before widening; a mismatch above 1e-3 means the engine is wired differently from the batch run (check `T_MONTHS`, decay weights and the `rho` scale).

- [ ] **Step 5: Commit**

```bash
git add src/engine.py tests/test_engine_solve.py
git commit -m "feat: add engine.solve_frontier and display helpers" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Batch pipeline through the engine, regenerate outputs

**Files:**
- Modify (full rewrite of the top of the file): `src/main.py`
- Regenerate: `outputs/frontiers/*.csv`, `outputs/plots/*.png`

**Interfaces:**
- Consumes: `engine.ensure_data()`, `engine.solve_frontier(...)` from Tasks 2-3.

- [ ] **Step 1: Replace `src/main.py`**

```python
"""Runs the full Opti-Money reproduction pipeline, start to finish:

  1. Make sure raw data, returns, benchmarks and forecasts exist
     (engine.ensure_data).
  2. Build the list of customer profiles (Loop A).
  3. For each profile, for each risk measure, build the efficient frontier
     (Loop B, via engine.solve_frontier) and round each portfolio to clean
     percentages.
  4. Save all results as CSVs, and plot risk-vs-return frontiers per profile.
"""

import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import customer_profiles
import engine
import frontier_builder


def run_all():
    engine.ensure_data()

    profiles = customer_profiles.build_profiles()

    all_frontiers = {}   # (profile_id, risk_measure) -> DataFrame

    start_time = time.time()
    total = len(profiles) * len(config.RISK_MEASURES)
    done = 0

    for profile in profiles:
        for risk_measure in config.RISK_MEASURES:
            frontier = engine.solve_frontier(
                risk_measure, profile["benchmark"], profile["equity_cap"],
                profile["liquidity_cap"], profile["currency_cap"],
                profile_id=profile["profile_id"],
            )

            all_frontiers[(profile["profile_id"], risk_measure)] = frontier

            out_name = f"{profile['profile_id']}__{risk_measure}.csv"
            out_path = os.path.join(config.OUTPUTS_FRONTIERS_DIR, out_name)
            weight_table = frontier_builder.frontier_to_weight_table(frontier)
            weight_table.to_csv(out_path, index=False)

            done += 1
            if not frontier["success"].all():
                print(f"  WARNING: some points did not converge for "
                      f"{profile['profile_id']} / {risk_measure}")

        elapsed = time.time() - start_time
        print(f"[{done}/{total} risk-measure runs done, "
              f"{elapsed:.1f}s elapsed] finished profile '{profile['profile_id']}'")

    plot_frontiers(all_frontiers, profiles)
    print(f"\nDone. {len(profiles)} profiles x {len(config.RISK_MEASURES)} risk "
          f"measures = {total} frontiers built and saved to "
          f"{config.OUTPUTS_FRONTIERS_DIR}")
    return all_frontiers


def plot_frontiers(all_frontiers: dict, profiles: list[dict]):
    colors = {"symmetric": "tab:blue", "asymmetric": "tab:orange", "markowitz": "tab:green"}

    for profile in profiles:
        pid = profile["profile_id"]
        fig, ax = plt.subplots(figsize=(6, 4.5))
        for risk_measure in config.RISK_MEASURES:
            frontier = all_frontiers[(pid, risk_measure)]
            f_sorted = frontier.sort_values("achieved_return")
            ax.plot(f_sorted["risk"], f_sorted["achieved_return"],
                    marker="o", label=risk_measure, color=colors[risk_measure])

        ax.set_xlabel("Risk")
        ax.set_ylabel("Expected annual return")
        ax.set_title(f"Efficient frontier: {pid}")
        ax.legend()
        fig.tight_layout()

        out_path = os.path.join(config.OUTPUTS_PLOTS_DIR, f"{pid}.png")
        fig.savefig(out_path, dpi=120)
        plt.close(fig)

    print(f"Saved {len(profiles)} frontier plots to {config.OUTPUTS_PLOTS_DIR}")


if __name__ == "__main__":
    run_all()
```

- [ ] **Step 2: Run the batch**

Run: `python src/main.py`
Expected: 20 "finished profile" lines, then `Done. 20 profiles x 3 risk measures = 60 frontiers built`, no `WARNING` lines. Takes several seconds.

- [ ] **Step 3: Verify the 45 existing frontiers are unchanged and 15 new ones exist**

Run: `git status --short outputs`
Expected: only new (untracked, `??`) files: 15 new CSVs (`*__EUR__*.csv` for 5 risk levels x 3 measures) and 5 new PNGs (`*__EUR.png`). No ` M` lines for existing CSVs.

If existing CSVs show as modified, run `git diff --stat outputs/frontiers | head` and `git diff outputs/frontiers/medium__CPI__symmetric.csv | head -20`. Whitespace/line-ending only differences are acceptable (mention them in the commit); numeric differences mean the refactor changed results, so stop and debug. Modified PNGs alone are acceptable if their CSVs are unchanged.

- [ ] **Step 4: Run the full test suite so far**

Run: `python -m pytest tests -v && python tests/test_toy_example.py`
Expected: all PASS; last line "All toy-example tests passed."

- [ ] **Step 5: Commit**

```bash
git add src/main.py outputs
git commit -m "refactor: run batch through engine; regenerate outputs with 4 benchmarks (60 frontiers)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Streamlit app core (sidebar, frontier, recommended portfolio)

**Files:**
- Modify: `src/config.py` (after the `TURNOVER_CAP_DEFAULT` line)
- Create: `src/ui_labels.py`
- Create: `src/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `engine.ensure_data`, `engine.solve_frontier`, `engine.InfeasibleProfileError`, `engine.annualized_risk`, `engine.constraint_usage`, `engine.data_window`; `frontier_builder.frontier_to_weight_table`.
- Produces: `config.LIQUIDITY_LEVELS` and `config.CURRENCY_LEVELS` (lists of fractions), and session-state keys and widget keys that tests and Task 6 rely on: `risk_level` (`select_slider`, options are the `config.RISK_LEVEL_CHOICES` keys), `equity_cap` (`slider`, 0-100 int), `benchmark` (`selectbox`), `risk_measures` (`multiselect`), `liquidity_cap` (`select_slider`, whole-percent ints from `config.LIQUIDITY_LEVELS`), `currency_cap` (`select_slider`, whole-percent ints from `config.CURRENCY_LEVELS`), `gamma`, `lambda_decay`, `K`, button key `reset`, text input `customer`. In `app.py`, module-level names used by Task 6: `ordered` (dict risk_measure -> frontier sorted by `achieved_return`), `focus` (chosen risk-measure key), `point` (1-based position), `rounded` (ndarray of weights, fractions), `benchmark`, `equity_cap`/`liquidity_cap`/`currency_cap` (fractions), `tab_history`/`tab_compare` are added in Task 6.

- [ ] **Step 1: Install Streamlit and confirm the testing API exists**

Run: `pip install streamlit`
Run: `python -c "import streamlit, altair; from streamlit.testing.v1 import AppTest; print(streamlit.__version__, altair.__version__)"`
Expected: prints two versions (Altair must be 5.x for `xOffset` in Task 6).

- [ ] **Step 1b: Add the discrete level lists to `src/config.py`**

Insert directly after the `TURNOVER_CAP_DEFAULT = None ...` line:

```python

# Discrete customer answers, as in the paper's finite menu of categories. The
# paper says "a few discrete levels" without giving numbers, so these stops
# are our documented assumption; edit them here to change what the dashboard
# offers. Each list must contain the matching default above.
LIQUIDITY_LEVELS = [0.0, 0.20, 0.40, 0.60, 1.00]   # max share in illiquid assets
CURRENCY_LEVELS = [0.0, 0.25, 0.50, 0.75, 1.00]    # max share in foreign-currency assets
assert LIQUIDITY_CAP_DEFAULT in LIQUIDITY_LEVELS, "LIQUIDITY_LEVELS must include the default"
assert CURRENCY_CAP_DEFAULT in CURRENCY_LEVELS, "CURRENCY_LEVELS must include the default"
```

- [ ] **Step 2: Write `src/ui_labels.py`**

```python
"""Friendly display names for the CRM dashboard. UI text only: the model
itself uses the identifiers in config.py."""

ASSETS = {
    "IL_Equity":        "Israeli equities (TA-125)",
    "US_Equity":        "US equities (S&P 500)",
    "EU_Equity":        "Euro-area equities (Euro Stoxx 50)",
    "Foreign_Bond":     "Foreign bonds (US Treasury 7-10y)",
    "IL_Bond_Unlinked": "Israeli government bonds (unlinked)",
    "IL_Bond_Linked":   "Israeli government bonds (CPI-linked)",
    "Cash":             "Cash / short-term deposits",
}

BENCHMARKS = {
    "CPI":      "Israeli CPI (inflation)",
    "USD":      "USD/ILS exchange rate",
    "ILS_RATE": "Bank of Israel rate (3M interbank proxy)",
    "EUR":      "EUR/ILS exchange rate",
}

RISK_LEVELS = {
    "low":           "Low",
    "low_medium":    "Low-medium",
    "medium":        "Medium",
    "risk_oriented": "Risk-oriented",
    "high":          "High",
}

RISK_MEASURES = {
    "symmetric":  "Benchmark-relative (symmetric)",
    "asymmetric": "Downside vs benchmark (asymmetric)",
    "markowitz":  "Classical volatility (Markowitz)",
}
```

- [ ] **Step 3: Write the failing tests**

Create `tests/test_app.py`:

```python
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
```

- [ ] **Step 4: Run to verify failure**

Run: `python -m pytest tests/test_app.py -v`
Expected: `test_labels_cover_every_config_key` and `test_discrete_level_lists_contain_the_defaults` PASS (labels and config lists exist); the rest FAIL (app file missing).

- [ ] **Step 5: Write `src/app.py`**

```python
"""Opti-Money CRM dashboard.

Run with:  streamlit run src/app.py

A relationship manager enters a customer's profile in the sidebar, sees the
efficient frontier for it, picks a point, and explains the recommended
portfolio. All optimization happens in engine.py; this file is UI only.
Every control starts at its config.py default; only controls the user
changes deviate from it.
"""

import os
import sys

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import engine
import frontier_builder
import ui_labels as L

st.set_page_config(page_title="Opti-Money CRM", layout="wide")

DEFAULT_RISK_LEVEL = "medium"
DEFAULT_BENCHMARK = "CPI"

# Allowed stops for the discrete sliders, as whole percentages (see config.py).
LIQUIDITY_STOPS = [round(v * 100) for v in config.LIQUIDITY_LEVELS]
CURRENCY_STOPS = [round(v * 100) for v in config.CURRENCY_LEVELS]

# Slider values are whole percentages; converted to fractions before solving.
DEFAULTS = {
    "risk_level": DEFAULT_RISK_LEVEL,
    "equity_cap": round(config.RISK_CATEGORY_EQUITY_CAP[DEFAULT_RISK_LEVEL] * 100),
    "benchmark": DEFAULT_BENCHMARK,
    "risk_measures": list(config.RISK_MEASURES),
    "liquidity_cap": round(config.LIQUIDITY_CAP_DEFAULT * 100),
    "currency_cap": round(config.CURRENCY_CAP_DEFAULT * 100),
    "gamma": config.GAMMA_TRACKING,
    "lambda_decay": config.LAMBDA_DECAY,
    "K": config.K_FRONTIER_POINTS,
}

for _key, _value in DEFAULTS.items():
    st.session_state.setdefault(_key, list(_value) if isinstance(_value, list) else _value)


def _apply_preset():
    """Selecting a risk level pre-fills the equity slider with that level's default."""
    level = st.session_state["risk_level"]
    st.session_state["equity_cap"] = round(config.RISK_CATEGORY_EQUITY_CAP[level] * 100)


def _reset():
    for key, value in DEFAULTS.items():
        st.session_state[key] = list(value) if isinstance(value, list) else value


def _tag(key):
    """Small marker under a control whose value differs from its default."""
    if st.session_state[key] != DEFAULTS[key]:
        st.caption(":orange[● modified]")


@st.cache_resource(show_spinner="Preparing market data (the first launch can take a minute)...")
def _prepare_data():
    engine.ensure_data()
    return True


@st.cache_data(show_spinner="Optimizing portfolios...")
def _solve(risk_measure, benchmark, equity_cap, liquidity_cap, currency_cap,
           gamma, lambda_decay, K):
    return engine.solve_frontier(
        risk_measure, benchmark, equity_cap, liquidity_cap, currency_cap,
        gamma, lambda_decay, K,
    )


# ---------------------------------------------------------------------------
# Sidebar: customer profile
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Customer profile")
    st.text_input("Customer name / ID", key="customer",
                  placeholder="Session only, never saved")

    st.select_slider("Risk level", options=list(L.RISK_LEVELS), key="risk_level",
                     format_func=L.RISK_LEVELS.get, on_change=_apply_preset,
                     help="One of the paper's five risk categories; the handle "
                          "snaps to the nearest one.")
    _tag("risk_level")

    st.slider("Maximum equity share (%)", 0, 100, key="equity_cap",
              help="Preset by the risk level; drag to fine-tune to any whole percentage.")
    _tag("equity_cap")

    st.selectbox("Benchmark", list(config.BENCHMARK_CHOICES), key="benchmark",
                 format_func=L.BENCHMARKS.get)
    _tag("benchmark")

    st.multiselect("Risk measures to compare", list(config.RISK_MEASURES),
                   key="risk_measures", format_func=L.RISK_MEASURES.get)
    _tag("risk_measures")

    st.select_slider("Maximum illiquid assets", options=LIQUIDITY_STOPS,
                     key="liquidity_cap", format_func=lambda v: f"{v}%",
                     help="A few fixed levels, as in the paper's customer questionnaire; "
                          "the handle snaps to the nearest one.")
    _tag("liquidity_cap")

    st.select_slider("Maximum foreign-currency assets", options=CURRENCY_STOPS,
                     key="currency_cap", format_func=lambda v: f"{v}%",
                     help="A few fixed levels, as in the paper's customer questionnaire; "
                          "the handle snaps to the nearest one.")
    _tag("currency_cap")

    with st.expander("Analyst settings"):
        st.number_input("Tracking penalty (gamma)", min_value=0.0, max_value=5.0,
                        step=0.01, format="%.2f", key="gamma")
        _tag("gamma")
        st.slider("Recency decay (lambda)", 0.80, 1.00, step=0.01, key="lambda_decay")
        _tag("lambda_decay")
        st.slider("Frontier points (K)", 2, 30, key="K")
        _tag("K")

    st.button("Reset to defaults", key="reset", on_click=_reset)

# ---------------------------------------------------------------------------
# Inputs -> solve
# ---------------------------------------------------------------------------
try:
    _prepare_data()
except Exception as exc:  # download or build failure: show it instead of a traceback
    st.error(f"Could not prepare the market data: {exc}")
    st.stop()

measures = st.session_state["risk_measures"]
if not measures:
    st.info("Select at least one risk measure in the sidebar.")
    st.stop()

benchmark = st.session_state["benchmark"]
equity_cap = st.session_state["equity_cap"] / 100
liquidity_cap = st.session_state["liquidity_cap"] / 100
currency_cap = st.session_state["currency_cap"] / 100

frontiers = {}
try:
    for _measure in measures:
        frontiers[_measure] = _solve(
            _measure, benchmark, equity_cap, liquidity_cap, currency_cap,
            st.session_state["gamma"], st.session_state["lambda_decay"],
            st.session_state["K"],
        )
except engine.InfeasibleProfileError:
    st.error(
        "These limits leave room for only one portfolio (100% cash), so there is "
        "no frontier to show. Raise the equity, illiquid or foreign-currency limit."
    )
    st.stop()

# Frontier order = ascending expected return: min-risk point ... max-return point.
ordered = {m: f.sort_values("achieved_return").reset_index(drop=True)
           for m, f in frontiers.items()}

if not all(f["success"].all() for f in ordered.values()):
    st.warning("Some frontier points did not fully converge; treat those results with care.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
customer = st.session_state["customer"].strip() or "New customer"
st.title(f"Portfolio advice: {customer}")
_start, _end = engine.data_window()
st.caption(f"Market data window: {_start:%b %Y} to {_end:%b %Y} "
           f"(last {config.T_MONTHS} months of common data)")
st.markdown(
    f"**Risk level:** {L.RISK_LEVELS[st.session_state['risk_level']]} · "
    f"**Benchmark:** {L.BENCHMARKS[benchmark]} · "
    f"**Limits:** equity {equity_cap:.0%}, illiquid {liquidity_cap:.0%}, "
    f"foreign currency {currency_cap:.0%}"
)

# ---------------------------------------------------------------------------
# Customer choice: which risk measure, and where on the frontier
# ---------------------------------------------------------------------------
n_points = len(next(iter(ordered.values())))
choice_left, choice_right = st.columns([1, 2])
with choice_left:
    focus = st.radio("Risk measure for the recommendation", measures,
                     format_func=L.RISK_MEASURES.get)
with choice_right:
    point = st.slider("Risk appetite (1 = most conservative, highest number = most growth)",
                      1, n_points, value=(n_points + 1) // 2)

frontier = ordered[focus]
row = frontier.iloc[point - 1]
rounded = np.array(row["rounded_x"], dtype=float)

tab_options, tab_portfolio = st.tabs(["Risk & return options", "Recommended portfolio"])

# ---------------------------------------------------------------------------
# Tab 1: frontier + how the mix changes along it
# ---------------------------------------------------------------------------
with tab_options:
    st.subheader("Risk and return options")

    chart_df = pd.concat([
        pd.DataFrame({
            "measure": L.RISK_MEASURES[m],
            "position": range(1, len(f) + 1),
            "annual_risk": f["risk"].map(engine.annualized_risk) * 100,
            "annual_return": f["achieved_return"] * 100,
        })
        for m, f in ordered.items()
    ], ignore_index=True)
    picked_df = chart_df[(chart_df["measure"] == L.RISK_MEASURES[focus])
                         & (chart_df["position"] == point)]

    x_enc = alt.X("annual_risk:Q", title="Annualized risk (%)")
    y_enc = alt.Y("annual_return:Q", title="Expected annual return (%)")
    lines = alt.Chart(chart_df).mark_line(point=True).encode(
        x=x_enc, y=y_enc,
        color=alt.Color("measure:N", title="Risk measure"),
        tooltip=[
            alt.Tooltip("measure:N", title="Risk measure"),
            alt.Tooltip("position:Q", title="Position"),
            alt.Tooltip("annual_risk:Q", title="Risk (%)", format=".2f"),
            alt.Tooltip("annual_return:Q", title="Return (%)", format=".2f"),
        ],
    )
    marker = alt.Chart(picked_df).mark_point(
        shape="diamond", size=260, filled=True, color="crimson"
    ).encode(x=x_enc, y=y_enc)
    st.altair_chart((lines + marker).interactive())
    st.caption("The red diamond is the selected portfolio. Each risk measure defines "
               "'risk' differently, so compare the shapes rather than exact positions.")

    mix = pd.DataFrame(np.vstack(frontier["x"].values), columns=config.ASSET_NAMES)
    mix["annual_return"] = frontier["achieved_return"].values * 100
    mix_long = mix.melt(id_vars="annual_return", var_name="asset", value_name="weight")
    mix_long["asset"] = mix_long["asset"].map(L.ASSETS)
    mix_long["weight"] = mix_long["weight"] * 100
    st.subheader("How the mix changes as you take more risk")
    st.altair_chart(
        alt.Chart(mix_long).mark_area().encode(
            x=alt.X("annual_return:Q", title="Expected annual return (%)"),
            y=alt.Y("weight:Q", stack="zero", title="Weight (%)"),
            color=alt.Color("asset:N", title="Asset class"),
            tooltip=[alt.Tooltip("asset:N", title="Asset class"),
                     alt.Tooltip("weight:Q", title="Weight (%)", format=".1f")],
        )
    )

# ---------------------------------------------------------------------------
# Tab 2: the recommended portfolio
# ---------------------------------------------------------------------------
with tab_portfolio:
    st.subheader("Recommended portfolio")
    left, right = st.columns(2)

    weights_df = pd.DataFrame({
        "asset": [L.ASSETS[a] for a in config.ASSET_NAMES],
        "weight": rounded * 100,
    })
    held = weights_df[weights_df["weight"] > 0].sort_values("weight", ascending=False)

    with left:
        st.altair_chart(
            alt.Chart(held).mark_arc(innerRadius=70).encode(
                theta=alt.Theta("weight:Q"),
                color=alt.Color("asset:N", title="Asset class"),
                tooltip=[alt.Tooltip("asset:N", title="Asset class"),
                         alt.Tooltip("weight:Q", title="Weight (%)", format=".0f")],
            )
        )

    with right:
        m_return, m_risk = st.columns(2)
        m_return.metric("Expected annual return", f"{row['achieved_return']:.2%}")
        m_risk.metric("Annualized risk", f"{engine.annualized_risk(row['risk']):.2%}")
        st.dataframe(
            held.assign(weight=held["weight"].map(lambda w: f"{w:.0f}%"))
                .rename(columns={"asset": "Asset class", "weight": "Weight"}),
            hide_index=True,
        )
        st.caption("Weights are rounded to whole percentages.")

    st.subheader("Limits check")
    usage = engine.constraint_usage(rounded)
    usage_df = pd.DataFrame({
        "limit": ["Equity", "Foreign currency", "Illiquid assets"],
        "used": [usage["equity"] * 100, usage["foreign"] * 100, usage["illiquid"] * 100],
        "cap": [equity_cap * 100, currency_cap * 100, liquidity_cap * 100],
    })
    limit_axis = alt.Y("limit:N", title=None, sort=None)
    bars = alt.Chart(usage_df).mark_bar().encode(
        y=limit_axis,
        x=alt.X("used:Q", title="% of portfolio", scale=alt.Scale(domain=[0, 100])),
    )
    ticks = alt.Chart(usage_df).mark_tick(color="crimson", thickness=3, size=30).encode(
        y=limit_axis,
        x=alt.X("cap:Q", title="% of portfolio", scale=alt.Scale(domain=[0, 100])),
    )
    st.altair_chart(bars + ticks)
    st.caption("Red marker = the customer's limit.")

    download_left, download_right = st.columns(2)
    download_left.download_button(
        "Download recommended portfolio (CSV)",
        data=held.rename(columns={"asset": "Asset class", "weight": "Weight (%)"})
                 .to_csv(index=False),
        file_name="recommended_portfolio.csv", mime="text/csv",
    )
    download_right.download_button(
        "Download full frontier (CSV)",
        data=frontier_builder.frontier_to_weight_table(frontier).to_csv(index=False),
        file_name="efficient_frontier.csv", mime="text/csv",
    )

st.divider()
st.caption("Illustrative reproduction built on public proxy data (Yahoo Finance, FRED); "
           "not investment advice.")
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tests/test_app.py -v`
Expected: 9 PASS.

Common failures and what to check first:
- A `StreamlitAPIException` about a widget "created with a default value but also had its value set via the Session State API": remove the offending explicit default (`value=`/`index=`) from that widget; the `setdefault` loop already supplies it.
- `AttributeError` on `at.metric`/`at.multiselect`: upgrade streamlit (`pip install -U streamlit`).
- A `TypeError` from an Altair call: print `alt.__version__`; the code assumes Altair 5.x.

- [ ] **Step 7: Commit**

```bash
git add src/config.py src/ui_labels.py src/app.py tests/test_app.py
git commit -m "feat: add Streamlit CRM dashboard core (profile sidebar, frontier, recommendation)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: History and current-portfolio comparison tabs

**Files:**
- Modify: `src/app.py` (the `st.tabs` line, and a block inserted before the footer)
- Test: `tests/test_app.py` (append)

**Interfaces:**
- Consumes: names produced by Task 5 (`rounded`, `benchmark`, `focus`) and `engine.portfolio_history`, `engine.compare_portfolios`.
- Produces: number-input keys `cur_<asset name>` (e.g. `cur_IL_Equity`); validation message containing `100%`.

- [ ] **Step 1: Append the failing tests to `tests/test_app.py`**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_app.py -v`
Expected: the 3 new tests FAIL (`IndexError`/`KeyError`: widgets and metrics do not exist yet); the earlier 9 still PASS.

- [ ] **Step 3: Change the tabs line in `src/app.py`**

Replace:

```python
tab_options, tab_portfolio = st.tabs(["Risk & return options", "Recommended portfolio"])
```

with:

```python
tab_options, tab_portfolio, tab_history, tab_compare = st.tabs([
    "Risk & return options", "Recommended portfolio",
    "History vs benchmark", "Compare with current portfolio",
])
```

- [ ] **Step 4: Insert the two tab blocks immediately before the footer**

Insert this block directly above the line `st.divider()` (the footer, at the end of the file):

```python
# ---------------------------------------------------------------------------
# Tab 3: what this portfolio would have done, historically
# ---------------------------------------------------------------------------
with tab_history:
    st.subheader("History vs benchmark")
    history = engine.portfolio_history(rounded, benchmark)
    benchmark_label = L.BENCHMARKS[benchmark]

    total_portfolio = history["Portfolio"].iloc[-1] / 100 - 1
    total_benchmark = history["Benchmark"].iloc[-1] / 100 - 1
    h_left, h_right = st.columns(2)
    h_left.metric("Portfolio, total over window", f"{total_portfolio:+.1%}")
    h_right.metric("Benchmark, total over window", f"{total_benchmark:+.1%}")

    st.line_chart(history.rename(columns={"Benchmark": benchmark_label}))
    st.caption(f"Growth of 100 invested in {_start:%b %Y}. Historical and in-sample "
               "(the portfolio was chosen using this same period): not a forecast.")

# ---------------------------------------------------------------------------
# Tab 4: current vs proposed
# ---------------------------------------------------------------------------
with tab_compare:
    st.subheader("Compare with the customer's current portfolio")
    st.caption("Enter the current allocation as % of the portfolio; it must total 100%.")

    current = {}
    input_columns = st.columns(3)
    for i, asset in enumerate(config.ASSET_NAMES):
        current[asset] = input_columns[i % 3].number_input(
            L.ASSETS[asset], min_value=0.0, max_value=100.0, value=0.0, step=1.0,
            key=f"cur_{asset}",
        )
    current_total = sum(current.values())

    if current_total == 0:
        st.info("Enter the current holdings to compare them with the recommendation.")
    elif abs(current_total - 100.0) > 0.01:
        st.error(f"Current weights add up to {current_total:.1f}%; they must total 100%.")
    else:
        table = engine.compare_portfolios(
            [current[a] / 100 for a in config.ASSET_NAMES], rounded
        )
        table["asset"] = table["asset"].map(L.ASSETS)
        long = pd.concat([
            pd.DataFrame({"asset": table["asset"], "series": "Current",
                          "weight": table["current"] * 100}),
            pd.DataFrame({"asset": table["asset"], "series": "Proposed",
                          "weight": table["proposed"] * 100}),
        ])
        st.altair_chart(
            alt.Chart(long).mark_bar().encode(
                x=alt.X("asset:N", title=None, axis=alt.Axis(labelAngle=-35)),
                xOffset="series:N",
                y=alt.Y("weight:Q", title="Weight (%)"),
                color=alt.Color("series:N", title=None),
                tooltip=["asset", "series", alt.Tooltip("weight:Q", format=".0f")],
            )
        )
        st.metric("Total change (sum of absolute weight changes)",
                  f"{table['trade'].abs().sum() * 100:.0f}%")
        st.dataframe(
            pd.DataFrame({
                "Asset class": table["asset"],
                "Current": (table["current"] * 100).map(lambda w: f"{w:.0f}%"),
                "Proposed": (table["proposed"] * 100).map(lambda w: f"{w:.0f}%"),
                "Change": (table["trade"] * 100).map(lambda w: f"{w:+.0f} pts"),
            }),
            hide_index=True,
        )

```

- [ ] **Step 5: Run the full UI tests**

Run: `python -m pytest tests/test_app.py -v`
Expected: 12 PASS.

- [ ] **Step 6: Commit**

```bash
git add src/app.py tests/test_app.py
git commit -m "feat: add history-vs-benchmark and current-portfolio comparison tabs" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Docs, spec amendments, final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-09-20-crm-streamlit-ui-design.md`

- [ ] **Step 1: Update `README.md`**

Make these edits:

1. In "1. One-time setup", change the install command to:

```
pip install numpy pandas scipy yfinance pandas_datareader matplotlib streamlit
```

and add below it: `To run the tests you also need pytest (\`pip install pytest\`).`

2. In "2. Run everything with one command", change item 4 to `Builds the 20 customer profiles (5 risk levels x 4 benchmarks: CPI, USD, Bank of Israel rate, Euro).` and item 5 to `Solves all 60 efficient frontiers (20 profiles x 3 risk measures), 720 individual optimizations total.`

3. Insert a new section before "## 3. Where to find the results":

```markdown
## 2b. Interactive CRM dashboard

For a relationship-manager view with live controls and graphs:

    streamlit run src/app.py

It opens in your browser (usually http://localhost:8501). Pick a risk level (this pre-fills the equity-cap slider, which you can then drag to any whole percentage), a benchmark, and the liquidity/currency limits. The risk level and the liquidity/currency limits are discrete, as in the paper's questionnaire: their sliders snap to the nearest allowed level (edit `LIQUIDITY_LEVELS` / `CURRENCY_LEVELS` in `src/config.py` to change the levels). The efficient frontier and recommended portfolio update immediately. Every control starts at its `src/config.py` default and only changes when you change it; "Reset to defaults" restores them. Tabs: risk/return options, recommended portfolio, history vs benchmark, and a comparison with the customer's current portfolio. Nothing you type is saved.
```

4. In "4. Run just the tests", replace the body with:

```
python tests/test_toy_example.py
python -m pytest tests -v
```

- [ ] **Step 2: Amend the spec to match what was built**

In `docs/superpowers/specs/2026-09-20-crm-streamlit-ui-design.md`:

- In the Architecture table row for `src/app.py`, and in the sentence "Display labels ... live in `app.py`", change the label location to `src/ui_labels.py` (new small module, importable by tests).
- In "Main area — tabs", tab 1: change "A 'Conservative <-> Growth' selector picks a frontier point" to say the risk-measure radio and the "Risk appetite" slider sit **above the tabs** (tabs 2-4 depend on them), and add: "Risk is shown as annualized risk = sqrt(12 x monthly risk score), a monotonic display transform so the three measures share one axis."
- In "Error handling", "Missing data files" bullet: change "shows an error with the failing series name" to "shows an error containing the download error text" (the loader's message reports how many series failed, and its log names them).
- In "Dependencies": add "`pytest` (dev only, for tests)".

- [ ] **Step 3: Full test run**

Run: `python -m pytest tests -v && python tests/test_toy_example.py`
Expected: all PASS (about 35 tests) and "All toy-example tests passed."

- [ ] **Step 4: Launch the real app and check it serves**

Run in the background: `streamlit run src/app.py --server.headless true --server.port 8599`
Then: `curl -s http://localhost:8599/_stcore/health`
Expected: `ok`. Stop the background server afterwards.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/specs/2026-09-20-crm-streamlit-ui-design.md
git commit -m "docs: document CRM dashboard, 4 benchmarks, and spec amendments" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Hand over**

Tell the user: run `streamlit run src/app.py` and open http://localhost:8501. Mention that headless tests cover behavior but the visual layout has not been checked in a browser by the agent, and ask them to look at the four tabs and report anything that looks off.
