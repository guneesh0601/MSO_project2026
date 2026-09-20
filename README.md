# MSO_project2026

## How to Run This Project

This is the working reproduction of the Opti-Money model from the Avriel et al. (2004) paper. Everything is already built and tested — this file just tells you how to actually run it yourself.

## 1. One-time setup (only needed once, ever)

Open a terminal in the `MSO project` folder and install the required libraries:

```
pip install numpy pandas scipy yfinance pandas_datareader matplotlib streamlit
```

To run the tests you also need pytest (`pip install pytest`).

You need an internet connection the first time you run the pipeline (it downloads real market data from Yahoo Finance and FRED). After that first run, the data is saved locally and it won't need the internet again unless you delete the `data/` folder.

## 2. Run everything with one command

```
cd src
python main.py
```

That single command does all of this automatically, in order:
1. Downloads the raw price/rate data (skipped if already downloaded).
2. Builds the historical returns table and benchmark series.
3. Builds the return forecasts.
4. Builds the 20 customer profiles (5 risk levels x 4 benchmarks: CPI, USD, Bank of Israel rate, Euro).
5. Solves all 60 efficient frontiers (20 profiles x 3 risk measures), 720 individual optimizations total.
6. Rounds every portfolio to clean percentages.
7. Saves all results as CSV files and PNG charts.

It takes about 4 seconds to run once the data is downloaded. You'll see a progress line print after each customer profile finishes.

## 2b. Interactive CRM dashboard

For a relationship-manager view with live controls and graphs:

```
streamlit run src/app.py
```

It opens in your browser (usually http://localhost:8501). Pick a risk level (this pre-fills the equity-cap slider, which you can then drag to any whole percentage), a benchmark, and the liquidity/currency limits. The risk level and the liquidity/currency limits are discrete, as in the paper's questionnaire: their sliders snap to the nearest allowed level (edit `LIQUIDITY_LEVELS` / `CURRENCY_LEVELS` in `src/config.py` to change the levels). The efficient frontier and recommended portfolio update immediately. Every control starts at its `src/config.py` default and only changes when you change it; "Reset to defaults" restores them. Tabs: risk/return options, recommended portfolio, history vs benchmark, and a comparison with the customer's current portfolio. Nothing you type is saved.

## 3. Where to find the results

- `outputs/frontiers/*.csv` — one file per (customer profile, risk measure) combination, e.g. `medium__CPI__symmetric.csv`. Each row is one point on that efficient frontier: the portfolio weights, the risk achieved, and the expected return achieved.
- `outputs/plots/*.png` — one chart per customer profile, showing all three risk measures' frontiers plotted together (risk on the x-axis, expected return on the y-axis). Open these image files directly to look at them.

## 4. Run just the tests (to double-check nothing is broken)

```
python tests/test_toy_example.py
python -m pytest tests -v
```

The first re-runs the small hand-checkable sanity tests and should print "All toy-example tests passed." The second runs the full suite, including the engine and dashboard tests.

## 5. Re-running with fresh data or different settings

- To force a fresh data download instead of reusing the saved files, delete everything inside `data/raw/` and `data/processed/`, then run `python main.py` again.
- To change any setting (which assets, gamma, lambda, K, risk category bounds, etc.), edit `src/config.py` and rerun `python main.py`.

## 6. Looking at one specific result quickly

If you just want to peek at one frontier without opening a spreadsheet program:

```
cd src
python -c "import pandas as pd; print(pd.read_csv('../outputs/frontiers/medium__CPI__symmetric.csv').round(3))"
```

Swap `medium__CPI__symmetric` for any of the other 44 file names in `outputs/frontiers/` to look at a different profile/risk-measure combination.

## Project files, if you want to understand or modify the code

See `docs/Master_Implementation_Plan.md` for what each file in `src/` does and why, and the other files in `docs/` for the underlying math explained in plain English:

- `docs/Reproduction_Plan.md` — the overall plan and what we substituted for the bank's proprietary data
- `docs/Data_Sources_Plan.md` — exactly where every dataset comes from
- `docs/loop.md` — the three nested optimization loops explained
- `docs/ExpRet_Constraint_Explained.md` — a deep dive on the expected-return constraint
- `docs/Master_Implementation_Plan.md` — the file-by-file build plan for `src/`

**Note:** the original paper PDF is intentionally not included in this repository — it's a copyrighted INFORMS/Interfaces article whose terms restrict use to research, teaching, and private study, so it isn't redistributed here.
