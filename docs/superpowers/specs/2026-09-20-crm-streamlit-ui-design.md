# Opti-Money CRM Dashboard (Streamlit) — Design

Date: 2026-09-20

## Goal

Replace "run `main.py`, then open PNGs/CSVs" with an interactive Streamlit app that a
**bank relationship manager (CRM)** can use in a customer meeting: enter the customer's
profile, see the efficient frontier, pick a point, and explain the recommended portfolio
with graphs. This mirrors the paper's flow (customer answers screens -> CRM/customer sees
the frontier -> picks a portfolio).

Also: the hardcoded `RISK_CATEGORY_EQUITY_CAP` becomes an interactive slider, and the paper's
4th benchmark (Euro) is added.

## Non-goals

- Horizon and objective screens from the paper (this reproduction holds them fixed; see `customer_profiles.py`).
- Applying a turnover constraint against the customer's current portfolio (the current-vs-proposed
  view is display only).
- Saving customers, logins, or any persistence. Nothing the CRM types leaves the session.
- A terminal-menu interface (user chose Streamlit only).

## Architecture

| Unit | Purpose | Depends on |
|---|---|---|
| `src/engine.py` (new) | `ensure_data()` (moved from `main.py`, plus the benchmark-completeness check) and `solve_frontier(risk_measure, benchmark, equity_cap, liquidity_cap, currency_cap, gamma, lambda_decay, K)`. Builds one profile dict, calls the existing `build_frontier`, adds `rounded_x`. Also `portfolio_history(x, benchmark)` (cumulative growth series). | existing modules |
| `src/app.py` (new) | Streamlit UI only; no optimization logic. Run with `streamlit run src/app.py`. | `engine`, `config`, streamlit, altair |
| `src/main.py` | Batch run now calls `engine`, so batch and UI share one code path. | `engine` |
| `src/config.py` | Add `"EUR": {"source": "yfinance", "id": "EURILS=X"}` to `BENCHMARKS`; add `"EUR"` to `BENCHMARK_CHOICES`; add `LIQUIDITY_LEVELS` and `CURRENCY_LEVELS` (allowed stops for the discrete sliders). Every UI default is still an existing config constant. | — |
| `src/returns_calculator.py` | `build_benchmark_returns`: treat `EUR` like `CPI`/`USD` (price series -> `simple_return`). | — |

The UI never mutates `config` globals. `gamma`, `K` and `lambda_decay` are passed as arguments
(`build_frontier` already accepts `gamma` and `K`; decay weights come from `rm.decaying_weights`).

## CRM workflow and layout

**Header card:** customer name/ID (free text, session only) and chips summarizing the profile
(risk level, benchmark, equity/foreign/illiquid caps).

**Sidebar — "Customer profile":**
- Risk level: a 5-stop snapping slider (low ... high). Selecting one sets the equity-cap slider to that
  category's preset from `RISK_CATEGORY_EQUITY_CAP`; the CRM may then drag the equity slider to any whole
  percentage (0-100%) as a fine-tuning override.
- Benchmark dropdown: Israeli CPI, USD/ILS, Bank of Israel rate (3M interbank proxy), EUR/ILS.
- Risk measure(s): multiselect, all three by default (symmetric, asymmetric downside, classical Markowitz).
- Liquidity cap and currency cap: snapping sliders over a few discrete levels, as in the paper's customer
  questionnaire ("a few discrete levels"; the paper gives no numbers). The stops are new config lists,
  `LIQUIDITY_LEVELS = [0, 20, 40, 60, 100]%` and `CURRENCY_LEVELS = [0, 25, 50, 75, 100]%`, a documented
  assumption like the category equity caps; each contains its existing default (40% and 100%).
- Discrete controls use `st.select_slider`, so releasing the handle between stops lands on the nearest stop.
  Continuous-by-nature controls (equity override, lambda, K, frontier position) use stepped sliders.
- Every control starts at its config default. A control that differs from its default shows a
  "modified" tag; the solver uses current values (defaults where untouched). "Reset to defaults" button.
- Collapsed "Analyst settings": gamma (tracking penalty), lambda (recency decay), K (frontier points).

**Main area — tabs:**
1. **Frontier portfolios.** A table of the K + 2 portfolios on the selected risk measure's frontier, one row per
   point (Step 1: minimum risk, k = 1 ... K, Step 2: maximum return) with its ExpRet (% per year), annualised risk
   (sqrt(12 x monthly risk score), a display transform) and asset-class weights (whole percentages). The recommended
   row is marked. This replaced an earlier frontier chart and a stacked-area mix chart, at the user's request.

   The risk-measure radio sits **above the tabs**, because tabs 2-4 all depend on which measure's frontier
   is recommended. The recommended portfolio is the **middle point** of that frontier. (A "Risk appetite"
   slider that chose the point was built first and then removed at the user's request.)
2. **Recommended portfolio.** For the selected point and risk measure: allocation donut, weights table
   (rounded to 1%), expected return and risk figures, and constraint-usage bars (equity / foreign-currency /
   illiquid share vs the customer's caps). Download buttons for the portfolio and the full frontier as CSV.
3. **History vs benchmark.** Cumulative growth of the recommended portfolio vs the chosen benchmark over the
   36-month window, captioned as historical/in-sample, not a forecast.
4. **Compare with current portfolio (optional).** CRM enters current weights (must sum to 100%; validated).
   Shows current vs proposed bars and buy/sell % per asset and total turnover. Hidden until weights are entered.

**Footer:** "Illustrative reproduction built on public proxy data (Yahoo Finance, FRED); not investment advice."

Display labels (friendly asset/benchmark/risk-level/risk-measure names) live in `src/ui_labels.py`, a small
module importable by tests; `config.py` keeps model identifiers only.

## Data flow

Sidebar values -> `engine.solve_frontier` (one call per selected risk measure, about 0.1 s each) -> DataFrame
(`x`, `rounded_x`, `risk`, `achieved_return`, `success`) -> tabs. Solves are cached by parameter values
(`st.cache_data`), so returning to earlier settings is instant. Data loading is cached per session.

## Error handling

- Infeasible settings (e.g. all caps 0%): `build_frontier` raises `ValueError`; the UI catches it and shows a
  plain-language message naming the constraints to relax. No traceback.
- Points with `success == False`: warning banner, as the batch run does today.
- Current-portfolio weights not summing to 100%: inline validation, comparison not drawn.
- Missing data files: `ensure_data()` downloads them on first launch with a visible spinner; a download
  failure shows an error containing the download error text (the loader's message reports how many series
  failed, and its log names them).

## Euro benchmark and data check

`EURILS=X` was verified on 2026-09-20: 60 monthly rows (Oct 2021 - Sep 2026), no gaps, same as `USDILS=X`.
`ensure_data()` currently checks only `asset_returns.csv`; it will also require every `BCH_<name>.csv` in
`BENCHMARKS` and every benchmark column in `benchmark_returns.csv`, rebuilding when any is missing.

## Batch outputs

Re-run `main.py` after the Euro change: 4 benchmarks x 5 risk levels x 3 risk measures = 60 frontiers
(was 45). Outputs are tracked in git, so this is reversible. README updated (run instructions, new
dependency, 4 benchmarks).

## Testing

- **Regression:** `solve_frontier` with all defaults reproduces `outputs/frontiers/medium__CPI__symmetric.csv`
  (risk, return, weights), so the UI cannot drift from the batch results.
- **EUR:** benchmark return series builds, has >= 36 months, no NaNs.
- **Engine:** infeasible caps raise `ValueError`; higher equity cap never lowers max achievable return.
- **UI (`streamlit.testing.v1.AppTest`, headless):** app loads without exception; changing the equity cap
  changes the output; category preset sets the slider; reset restores defaults; invalid current-portfolio
  weights show the validation message.
- Existing `tests/test_toy_example.py` stays as is.

## Dependencies

Adds `streamlit` (Altair ships with it; no separate charting dependency). Installed versions when built:
Streamlit 1.64.0, Altair 6.3.0. Also `pytest` (dev only, for tests).

## Addendum: multiple benchmarks (paper p. 41, p. 47 measure (3))

The paper says "Customers can choose multiple investment objectives and benchmarks, and the system's results
will be weighted accordingly" (p. 41) and lists "return variability around more than one benchmark ... a
weighted average of several benchmarks" as risk measure (3) (p. 47). It does not say how the weights are set;
we let the CRM enter them. Multiple *objectives* are out of scope (objectives are not modeled).

- **Engine:** `solve_frontier(..., benchmark, ...)` and `portfolio_history(x, benchmark)` accept either a
  benchmark name (unchanged) or a weight map `{name: fraction}`. New `engine.benchmark_series(benchmark)`
  returns the monthly benchmark return series: the column for a name, or the fixed-weight sum of the chosen
  columns. It raises `ValueError` for an empty map, unknown names, negative weights, or weights that do not
  total 1 (tolerance 1e-6). Assumption: the blend is a fixed-weight average of monthly benchmark returns.
- **UI:** the benchmark dropdown becomes a multiselect (default CPI). With one benchmark selected the weight
  is implicitly 100%. With two or more, each gets a 0-100 slider; changing the selection resets the weights to
  an equal split (50/50, 34/33/33, ...) which the CRM can then edit. Weights not totalling 100% show a message
  and no charts. Header and history chart label the blend (e.g. "60% CPI + 40% USD/ILS"). Reset and the
  "modified" tag cover the new controls. The classical Markowitz measure ignores the benchmark entirely
  (existing behaviour); the sidebar says so.
- **Unchanged:** batch pipeline and the 20 saved single-benchmark profiles; no outputs regenerate.
- **Tests:** `{CPI: 1.0}` reproduces the plain CPI frontier; the blend equals a hand-computed weighted sum;
  invalid weights raise; a blend changes the symmetric frontier; Markowitz is benchmark-independent; UI tests
  for equal-split reset, the not-100% message, a valid two-benchmark blend, and reset.
