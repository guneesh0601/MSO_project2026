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
1. **Risk & return options.** Efficient frontier chart (risk vs expected annual return, one line per risk
   measure, hover tooltips). A "Conservative <-> Growth" selector picks a frontier point; the point is
   highlighted on the chart. Also a stacked-area chart of asset weights across the frontier
   ("how the mix changes as you take more risk").
2. **Recommended portfolio.** For the selected point and risk measure: allocation donut, weights table
   (rounded to 1%), expected return and risk figures, and constraint-usage bars (equity / foreign-currency /
   illiquid share vs the customer's caps). Download buttons for the portfolio and the full frontier as CSV.
3. **History vs benchmark.** Cumulative growth of the recommended portfolio vs the chosen benchmark over the
   36-month window, captioned as historical/in-sample, not a forecast.
4. **Compare with current portfolio (optional).** CRM enters current weights (must sum to 100%; validated).
   Shows current vs proposed bars and buy/sell % per asset and total turnover. Hidden until weights are entered.

**Footer:** "Illustrative reproduction built on public proxy data (Yahoo Finance, FRED); not investment advice."

Display labels (friendly asset/benchmark/risk-level names) live in `app.py`; `config.py` keeps model identifiers only.

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
  failure shows an error with the failing series name.

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

Adds `streamlit` (Altair ships with it; no separate charting dependency). Not currently installed.
