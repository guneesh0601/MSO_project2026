# Handover Report — Opti-Money CRM Dashboard

**Who this is for:** a teammate picking up this project with no other context. Written in plain
English on purpose. If something here doesn't match the code, trust the code — this is a summary,
written on 2026-10-16, covering the work done by Claude (an AI assistant) in conversation with
Guneesh.

---

## 1. What this project is, in one paragraph

This repo reproduces a 2004 academic paper, *"Opti-Money at Bank Hapoalim"* (Avriel et al.,
*Interfaces* 34(1), pp. 39–50), using public data instead of the bank's private data. The paper
describes a system that builds investment portfolios for bank customers: given a customer's risk
level, which benchmark they want to track (inflation, a currency, etc.), and some limits on their
portfolio, the system finds the mix of asset classes (stocks, bonds, cash) that gives the best
trade-off between expected return and risk. This repo rebuilds that model in Python, using Yahoo
Finance and FRED for market data, and adds an interactive web dashboard (built with Streamlit) so
a bank relationship manager (a "CRM" in the paper's language) can use it live in a meeting instead
of just reading CSV files.

The original paper PDF is **not** in this repo (copyright — see `.gitignore`). If you need it,
ask Guneesh; he has a copy locally.

---

## 2. How to run it (quick start)

```bash
pip install numpy pandas scipy yfinance pandas_datareader matplotlib streamlit pytest
```

To run the batch pipeline (downloads data, solves all the frontiers, saves CSVs and PNGs):

```bash
cd src
python main.py
```

To run the interactive dashboard:

```bash
streamlit run src/app.py
```

This opens a browser tab (usually `http://localhost:8501`). **If you edit any file in `src/`
while the server is running and the page doesn't pick up the change, press Ctrl+C in the terminal
and restart `streamlit run src/app.py`.** The app has a self-fix for this (see §6.9) that handles
most cases, but a hard restart always works.

To run the tests:

```bash
python -m pytest tests -v
python tests/test_toy_example.py
```

All 73 tests should pass. `test_toy_example.py` is older, hand-checked-by-hand sanity tests for
the core formulas (kept from before this session).

The full README has more detail: see `README.md` in the repo root.

---

## 3. What already existed before this session

Before this round of work, the repo already had a working, non-interactive reproduction of the
paper's math:

- **Data pipeline** (`data_loader.py`, `returns_calculator.py`): downloads monthly prices/rates
  from Yahoo Finance and FRED for 7 asset classes and 3 benchmarks, and turns them into a table of
  monthly returns.
- **Forecasts** (`forecasts.py`): builds the "expected future return" number the model needs for
  each asset (see §6.11 below — this is one of the weaker parts of the project).
- **Risk math** (`risk_measures.py`): implements the paper's three risk measures — see §5.
- **Optimizer** (`optimizer.py`, `objective.py`, `constraints.py`): uses `scipy.optimize.minimize`
  (the SLSQP method) to solve the nonlinear optimization problem — find the portfolio weights that
  minimize risk for a given expected return, subject to constraints (weights sum to 1, no
  short-selling, liquidity/currency limits, etc).
- **Frontier builder** (`frontier_builder.py`): the paper's 4-step method for building an
  "efficient frontier" — a sequence of K+2 portfolios from lowest-risk to highest-return (see §5).
- **Batch runner** (`main.py`): runs the whole pipeline end to end and saves CSVs/PNGs, imitating
  the paper's "overnight batch" approach (though as discussed in §6.12, that's no longer really
  necessary with today's hardware).
- **Tests** (`tests/test_toy_example.py`): hand-worked numeric examples that check the formulas
  are implemented correctly.
- **Docs** (`docs/`): a set of planning documents written before any code existed, explaining the
  math in plain English and recording which assumptions stand in for things the paper doesn't
  specify. Worth reading if you want the "why" behind a formula:
  - `docs/Reproduction_Plan.md` — overall plan and what was substituted for the bank's private data.
  - `docs/Data_Sources_Plan.md` — exactly where each dataset comes from.
  - `docs/loop.md` — explains the three nested loops in the system (customer profiles → one
    frontier → one optimization), which is useful for understanding why this isn't actually an
    "infinite" search problem despite having continuous variables.
  - `docs/ExpRet_Constraint_Explained.md` — deep dive on the expected-return constraint.
  - `docs/Master_Implementation_Plan.md` — file-by-file build plan.

This session did **not** touch the core math files (`risk_measures.py`, `optimizer.py`,
`objective.py`, `frontier_builder.py`, `rounding.py`, `returns_calculator.py`) except for one
one-line change (adding the EUR benchmark, §6.1) and one change to `constraints.py` (making the
equity cap optional, §6.13). The core optimization logic is unchanged from before.

---

## 4. What this session added, in order

This was a long back-and-forth conversation. Here's the order things happened, each explained
simply. All of it is already committed and pushed to `main` on GitHub
(`https://github.com/guneesh0601/MSO_project2026`) as of this report, except as noted.

### 4.1 Added the 4th benchmark (EUR)

The paper says customers can track one of **four** benchmarks: inflation (CPI), the Bank of
Israel's interest rate, the US dollar exchange rate, and the Euro exchange rate. The code only had
three (no Euro). Added `EUR` to `config.py` (ticker `EURILS=X` on Yahoo Finance) and wired it into
`returns_calculator.py`. Confirmed the data actually downloads with 60 months of history.

### 4.2 Built the Streamlit dashboard (the main piece of work)

Before this, the only way to see results was to run the batch script and open CSV/PNG files by
hand. Built an interactive web app instead:

- **`src/engine.py`** (new file): a thin layer between the UI and the existing math code. Has two
  jobs: (1) make sure the data is downloaded/processed (`ensure_data`), and (2) solve one
  efficient frontier for one set of customer inputs (`solve_frontier`). `main.py` (the batch
  script) was rewritten to call this same code, so the dashboard and the batch script can never
  drift apart — they use exactly the same solver path.
- **`src/app.py`** (new file): the actual Streamlit page. All UI, no math.
- **`src/ui_labels.py`** (new file): human-friendly names for assets/benchmarks/risk measures
  (e.g. "Israeli equities (TA-125)" instead of the internal code `IL_Equity`). Kept separate from
  `config.py` so the model code never needs to care about display text.

The dashboard has a sidebar where you enter a (fictional) customer's profile, and four tabs:
1. **Frontier portfolios** — a table of all the portfolios on the frontier (see §5).
2. **Recommended portfolio** — the one portfolio picked out for this customer, shown as a pie
   chart + table, plus how much of each limit (illiquid assets, foreign currency) it's using.
3. **History vs benchmark** — how the recommended portfolio's monthly returns compare to the
   benchmark's monthly returns, over the same 36 months the model was built on.
4. **Compare with current portfolio** — optional: type in what the customer currently holds and
   see a bar chart of current vs. recommended, plus total % that would need to change.

### 4.3 Made the liquidity/currency sliders snap to fixed values

The paper's customer questionnaire only offers **a few discrete levels** for things like "how much
of your portfolio can be illiquid" — not a free-form 0–100% slider. Added
`LIQUIDITY_LEVELS = [0, 20, 40, 60, 100]%` and `CURRENCY_LEVELS = [0, 25, 50, 75, 100]%` to
`config.py` (our own assumption — the paper doesn't give exact numbers) and used Streamlit's
`select_slider` so the handle always snaps to one of these values instead of landing on an
arbitrary number in between.

### 4.4 Added the "multiple benchmarks" feature

Found this line in the paper: *"Customers can choose multiple investment objectives and
benchmarks, and the system's results will be weighted accordingly."* The code only supported one
benchmark at a time. Added support for a **weighted blend** of benchmarks — e.g. "60% CPI + 40%
USD". This lives in `engine.benchmark_series()`, which takes either a single benchmark name or a
`{name: weight}` dictionary and returns the (possibly blended) monthly return series. The sidebar
now lets you pick more than one benchmark and set a weight slider for each (must add up to 100%).

### 4.5 Several rounds of chart fixes

A number of small, concrete UI bugs got reported via screenshots and fixed:
- Legend/axis labels were getting cut off (Altair, the charting library, truncates long text by
  default) — fixed with an explicit `labelLimit`.
- The frontier chart had pan/zoom enabled (`.interactive()`), which let the chart get dragged off
  to one side with the y-axis title clipped off-screen — removed `.interactive()`.
- The "History vs benchmark" chart originally showed **cumulative growth of 100** (like a stock
  chart) instead of the actual monthly return numbers (`PortfRet_t` and `BchRet_t`) that the risk
  formulas use. User asked for the simpler, more direct version — changed it to plot the raw
  monthly returns instead, with proper axis/series labels ("Portfolio return", "Benchmark return
  (CPI)", axis "Month" / "Monthly return (%)", with years shown on the month axis).

### 4.6 Replaced the frontier/mix charts with a table, and used the paper's own terminology

Originally the first tab had two graphs (a frontier scatter plot and a stacked-area "mix" chart).
User found the frontier chart confusing — specifically, some points on it had **less risk and
more return** than other points, which shouldn't happen on a true efficient frontier (see §6.10,
this surfaced a real bug). User asked to replace both graphs with a straightforward table instead:
one row per frontier point (Step 1 = minimum risk, k=1...K, Step 2 = maximum return), with each
row showing its expected return, risk, and asset weights. Also renamed the risk measures to match
the paper's own names: **"Symmetric Risk"**, **"Asymmetric Risk"**, **"Markowitz Risk V"** (from
page 47 of the paper), instead of generic labels.

### 4.7 Removed the "risk appetite" slider

There used to be a slider letting the CRM manually pick which point on the frontier (1 to 12) to
recommend. User asked to remove it. This led to §4.8 below, which is the biggest conceptual
change made this session.

### 4.8 Fixed a real conceptual bug: how "risk level" should work

**This is the most important thing in this report. Read it carefully.**

**What was wrong:** Originally, the customer's risk level (Low / Low-medium / Medium /
Risk-oriented / High) was implemented as an **equity cap** — e.g. "Low risk" meant "no more than
20% of the portfolio in stocks," defined in a table called `RISK_CATEGORY_EQUITY_CAP`. This meant
every risk level got its own, different frontier (different allowed portfolios), because the cap
is a hard constraint on the optimization.

**Why that's wrong:** The user pointed out that the paper builds **one frontier per customer**
(for a given benchmark, liquidity limit, etc.) with K+2 points, specifically so that the risk
level can be used to **pick which point of that frontier to recommend** — not to redefine the
whole problem. We went and checked page 49 of the paper: it lists the parameters that define a
frontier (investment horizon, benchmark, liquidity level, tax status, forecast overrides) — **risk
level is not on that list**. Page 44 says each recommended portfolio has a "risk-scale of 1 to 5."
So risk level is much more likely to be a way of selecting a point on an already-built frontier,
not a constraint that produces a different frontier for each level.

**Important honesty note:** the paper doesn't actually *say* how risk level is used — this reading
is strongly suggested by the structure of the paper (the five risk-scale levels, the K+2-point
frontier construction, the list of frontier-defining parameters not including risk level), but it
is still our interpretation, not something stated outright. Flag this to anyone reviewing the
project against the original paper.

**What changed:**
- Removed `RISK_CATEGORY_EQUITY_CAP` from `config.py` entirely. There is no longer an equity-cap
  slider in the UI at all.
- Added `engine.frontier_position(risk_level, n_points)`: given a risk level and how many points
  are on the frontier, it returns which 1-based position to use. The five levels are spread evenly
  from position 1 (Low = the minimum-risk portfolio) to the last position (High = the
  maximum-return portfolio). With the default K=10 (12 points total), the five levels land on
  positions **1, 4, 7, 9, 12**.
- `constraints.py` and `engine.solve_frontier()` still *support* an equity cap as an optional
  argument (it's just not used by the dashboard by default), so the option is there if someone
  wants to reintroduce a limit later.
- `customer_profiles.py` was simplified: instead of building 20 profiles (5 risk levels × 4
  benchmarks), it now builds just 4 profiles (one per benchmark) — because risk level no longer
  defines a separate profile.
- The batch script (`main.py`) now also writes `outputs/recommended_portfolios.csv`: one row per
  (benchmark, risk measure, risk level) showing exactly which frontier point and weights that
  combination resolves to.
- Deleted the old batch outputs (60 per-risk-level CSV files, 20 PNGs) and regenerated fresh ones
  (12 CSVs, 4 PNGs, 1 new recommended-portfolios file).

**A known consequence of this change (flagged, not yet fixed):** without an equity cap, the
"High" risk level now recommends the pure maximum-return portfolio, which the solver currently
puts **100% into a single asset class** (Euro equities, because that's the asset with the highest
forecasted return in our model — see §6.11). This matches what the paper's "Step 2" literally
does (ignore risk, maximize return), but a real bank would almost certainly not hand a customer a
one-asset portfolio — page 47 of the paper explicitly mentions imposing constraints on certain
assets for different customer classes. This is worth discussing with Guneesh: maybe reintroduce a
softer, non-level-specific limit (e.g. "no single asset above 60%") as a sensible, separately
documented assumption.

### 4.9 Fixed a crash bug (module-reload race condition)

Earlier in the session, a guard was added to `app.py` so that if the running Streamlit server had
an old copy of an edited file in memory (e.g. you edit `engine.py` while the server is running),
it force-reloads the project's own modules on every run, instead of making the user restart the
server by hand. The first version of this guard used `del sys.modules[name]`, which crashed with
a `KeyError` if two things tried to clean up the same module at once (e.g. two browser tabs open,
or Streamlit's own file-watcher triggering a second run mid-flight). Fixed by using
`sys.modules.pop(name, None)` instead, which does nothing instead of crashing if the module is
already gone. Added a test that deliberately simulates this race to make sure it can't regress.

### 4.10 Removed the "Equity share" metric

A small metric showing "% of portfolio in equities" was added to the Recommended Portfolio tab
right after §4.8's change (since the equity cap bars were removed, an equity-share number seemed
like a useful replacement). User asked to remove it — removed, along with its test.

---

## 5. The core math, explained simply (for context, not new this session)

This section is **unchanged from before this session** — it's here so you don't have to go dig
through `docs/` to get oriented.

- **Three risk measures** (page 47 of the paper), each turns a portfolio's weights `x` into one
  risk number:
  1. **Symmetric Risk** — variance of (portfolio return − benchmark return) each month, weighted
     so recent months count more. Penalizes both over- and under-performing the benchmark.
  2. **Asymmetric Risk** — same idea, but months where the portfolio *beat* the benchmark count as
     zero (only underperformance is "risk").
  3. **Markowitz Risk (V)** — classic portfolio variance, ignoring the benchmark entirely.
- **Expected return (`ExpRet`)** = weighted sum of each asset's forecasted return (`rho_i`) times
  its weight in the portfolio. See §6.11 — this is where the biggest unresolved weakness is.
- **Efficient frontier**: for one customer (one benchmark, one risk measure, one set of limits),
  the code solves K+2 separate optimization problems:
  1. Minimize risk, ignore return (gives the lowest-risk portfolio — "Step 1").
  2. Maximize return, ignore risk (gives the highest-return portfolio — "Step 2").
  3. Pick K evenly-spaced return targets between those two.
  4. For each target, minimize risk subject to hitting that exact return (gives points
     `k=1...k=K`).
  This produces 12 portfolios (with the default K=10), sorted from lowest-return to
  highest-return. Each one is individually optimal for its own risk/return trade-off.
- **The solver**: `scipy.optimize.minimize` with the SLSQP method (a gradient-based method — it
  doesn't check every possible portfolio, it follows the slope downhill, the same way the paper's
  original GAMS/MINOS software did). Typically converges in under 10 iterations per portfolio.
- **The "no corner solutions" trick**: plain portfolio optimization tends to dump everything into
  1-2 assets. The paper fixes this by adding a small penalty term (`gamma`) that discourages the
  portfolio from straying too far from a reference "market portfolio" — see §6.10 for why this
  matters and is partly still an open problem.

---

## 6. Known issues / things to look at next

This is the most useful section for picking up the work. In rough priority order:

### 6.1 The gamma (tracking penalty) problem — **not fully fixed, needs attention**

Early in the session, a real bug was found: with the equity cap still in place (before §4.8), the
tracking-penalty weight `gamma = 0.05` (in `config.py`) was **way too large** — at the high-return
end of a frontier, the tracking penalty was about **29 times bigger** than the actual risk score.
This meant the solver was mostly minimizing "distance from a generic market portfolio" instead of
minimizing risk, and the result was **dominated points**: frontier points where another point on
the same frontier had *both* less risk *and* more return. Across the 60 then-existing frontiers,
**47 of 60 contained dominated points, and about half of all points (357/720) were dominated.**

Lowering gamma to around 0.001 was found to cut this down to about a sixth of the original
dominated-point count, without fully eliminating it. At gamma=0, the problem goes away but then
the "no corner solutions" protection is gone entirely (you get 100%-in-one-asset portfolios).

**After §4.8 removed the equity cap**, one spot-check (the CPI benchmark, Symmetric Risk measure,
no cap) showed the frontier was **clean** — risk rose steadily with return, no dominated points.
This *suggests* the equity cap interacting with gamma was the main cause, but **this was only
checked for one of the 12 frontiers**. The user asked for a full re-check across all 12 and this
was never actually done — got sidetracked onto other questions. **This is the single most
important thing to do next**: write a script that loops over all 12 current frontiers (4
benchmarks × 3 risk measures) and checks for dominated points (a point is dominated if another
point on the same frontier has risk ≤ its risk AND return ≥ its return, with at least one strictly
better). If dominated points still show up anywhere, gamma probably still needs tuning down, or
dominated points should be filtered out of the frontier table before showing it to the user.

### 6.2 The expected-return forecast (`rho_i`) is a rough, undocumented-source guess

`forecasts.py` computes each asset's expected annual return as:

```
rho_i = 0.5 × (historical annualized average return over the 36-month window)
      + 0.5 × (risk-free rate + a premium: +5% for equities, +1.5% for bonds, 0% for cash)
```

The 50/50 blend weight and the three premium numbers (5%, 1.5%, 0%) were picked when this file was
originally written, with **no documented source or calibration** — they're just plausible-looking
numbers. The paper is explicit that real forecasts should come from an independent forecasting
process (the bank's own committee), not be derived from historical averages, so this blend-with-
history approach is already a known simplification; the premiums on top of it make it weaker
still.

During this session, some research was done (via web search) into what real, dated 1-year-ahead
forecast numbers might be used instead — e.g. the Bank of Israel's own published rate/inflation
path for cash, current bond yields for bonds, and an implied equity risk premium (Damodaran's free
dataset) for equities. This research was **not turned into code** — it's a good next step if
someone wants to make `rho_i` defensible instead of arbitrary. Also worth doing: Vanguard and
J.P. Morgan publish free long-term (10-15 year) capital market return assumptions by asset class,
which could be a secondary cross-check.

### 6.3 The historical data window is stale (ends March 2025, not "now")

The 36-month window used for all risk calculations is **April 2022 to March 2025** — even though
the system is being run well after that. The cause: the Israeli CPI series (from FRED) stops
updating around March 2025, and since every return series has to overlap on the same 36 months,
the stale CPI series drags the whole window backward. This was flagged as a known issue but not
fixed. Fixing it would mean finding and plugging in a fresher CPI source (e.g. directly from
Israel's Central Bureau of Statistics instead of FRED's mirror of it).

### 6.4 No currency conversion for foreign assets

US equities, Euro equities, and the foreign-bond proxy use their own-currency monthly returns —
they are **not converted into shekels** before being combined with Israeli assets. For an Israeli
customer this is a real simplification (currency moves would add to or subtract from their actual
return). Not fixed this session; flagged as a simplification worth revisiting.

### 6.5 The "High" risk level can recommend a one-asset portfolio

Covered in §4.8 above — worth a product decision (not just a code fix) about whether to add some
kind of sensible diversification floor back in, separate from the old per-level equity cap.

### 6.6 Multiple investment *objectives* are not modeled

The paper also lets customers pick multiple **objectives** (e.g. "saving for a house," "no
specific goal") in addition to multiple benchmarks — only the benchmark side was implemented this
session (§4.4). Objectives are out of scope; this reproduction doesn't model them at all.

### 6.7 Horizon (1/2/5/10 years) is not modeled

The paper's first screen also asks for an investment horizon. This reproduction treats everything
as effectively a 1-year view (the forecasts `rho_i` are explicitly annual) and does not vary
anything by horizon. Out of scope so far.

### 6.8 No turnover constraint actually applied

There's a "Compare with current portfolio" tab that shows how much the recommended portfolio
differs from what the customer currently holds — but this is **display only**. The underlying
optimizer does support a turnover constraint (limiting how much the new portfolio can differ from
an existing one — `constraints.py` has `turnover_constraint()`), it's just never wired up to the
dashboard's "current portfolio" input. Would be a reasonably contained feature to add.

### 6.9 The "server keeps stale code in memory" workaround is a patch, not a real fix

`app.py` force-drops its own project's modules from `sys.modules` at the top of every run so a
long-running Streamlit server picks up edits to `engine.py`/`ui_labels.py`/etc. without needing a
manual restart. This works (and is tested — see §4.9) but it's a workaround for how Streamlit
caches Python modules, not a standard pattern. If this ever causes weird behavior, the safe fallback
is always: Ctrl+C the server, run `streamlit run src/app.py` again.

### 6.10 Overnight-batch vs. live-solve (background, no action needed)

Also researched this session: whether the paper's "we need an overnight batch because live solving
is too slow" reasoning (page 40 of the paper) still holds up today. Timed our actual solver: one
full frontier (12 optimizations) at our project's size (7 assets) takes about **0.1 seconds**;
at the paper's size (60 asset classes) it'd be roughly 2.3 seconds. Extrapolated to the paper's
~36,000 customer-profile combinations, that's under 3 hours on a modern 8-core laptop (vs. their
original need for an overnight run on 2004-era hardware with a licensed solver). This confirms
live solving is now entirely practical — which is exactly why the dashboard solves on the fly
instead of reading from pre-computed files. No code changes came from this, just background
reasoning for why the architecture makes sense. Purely informational, not an action item.

### 6.11 Terminology quick-reference

If you're new to the paper's notation:
- `PortfRet_t` — the portfolio's own return in month t.
- `BchRet_t` — the benchmark's return in month t.
- `ExpRet` — the portfolio's forecasted future return (uses `rho_i`, not history).
- `rho_i` — forecasted future return for asset i (see §6.2 — currently a rough estimate).
- `x_i` — the portfolio weight (0 to 1) of asset class i.
- `T` — number of historical months used (36, i.e. 3 years).
- `K` — number of intermediate frontier points (default 10, so K+2 = 12 total points per
  frontier).
- `gamma` — the market-tracking penalty weight (see §6.1).

---

## 7. File map

```
src/
  config.py              — every fixed setting (assets, benchmarks, gamma, K, discrete-level lists)
  data_loader.py          — downloads raw price/rate data from Yahoo Finance / FRED
  returns_calculator.py   — turns raw prices/rates into monthly return tables
  forecasts.py            — builds rho_i (expected return forecast) — see §6.2
  risk_measures.py        — the 3 risk-measure formulas + the tracking-penalty term
  objective.py            — combines a risk measure + tracking penalty into one objective function
  constraints.py          — budget/bounds/liquidity/currency/(optional equity)/turnover constraints
  optimizer.py            — wraps scipy.optimize.minimize for the 3 problem types (min-risk,
                             max-return, target-return)
  frontier_builder.py     — the paper's 4-step frontier construction (K+2 points)
  rounding.py             — rounds weights to clean percentages while keeping them summing to 100%
  customer_profiles.py    — builds the list of batch profiles (now: one per benchmark)
  engine.py               — NEW this session: shared solving/data layer used by both main.py and app.py
  ui_labels.py             — NEW this session: human-friendly display names, kept separate from config.py
  app.py                  — NEW this session: the Streamlit dashboard (UI only, no math)
  main.py                 — batch script: builds all frontiers + recommended_portfolios.csv, saves plots

tests/
  test_toy_example.py     — hand-checked formula sanity tests (pre-existing)
  test_eur_benchmark.py   — checks the EUR benchmark is wired through correctly
  test_engine_data.py     — checks engine.py's data-readiness checks
  test_engine_solve.py    — checks engine.solve_frontier, benchmark blending, frontier_position, etc.
  test_app.py             — headless Streamlit UI tests (streamlit.testing.v1.AppTest)

docs/
  (pre-existing planning docs, see §3)
  superpowers/specs/2026-09-20-crm-streamlit-ui-design.md
                           — the design spec for the dashboard, with several "Addendum" sections
                             added as the design evolved during the session — worth reading for
                             the reasoning behind each UI decision
  superpowers/plans/2026-09-20-crm-streamlit-ui.md
                           — the step-by-step implementation plan that was followed to build it

outputs/
  frontiers/*.csv          — one file per (benchmark, risk measure): all 12 points, all weights
  recommended_portfolios.csv — one row per (benchmark, risk measure, risk level): which point got
                             picked and its weights
  plots/*.png               — one chart per benchmark, all 3 risk measures overlaid

data/
  raw/                     — downloaded price/rate series, one CSV per series
  processed/               — the cleaned monthly return tables used by the model
```

---

## 8. Testing approach

- `tests/test_toy_example.py` — pure hand-arithmetic checks of the core formulas, no dependencies
  beyond numpy. Run directly with `python tests/test_toy_example.py`.
- `tests/test_eur_benchmark.py`, `test_engine_data.py`, `test_engine_solve.py` — plain pytest
  tests of `engine.py` (and related config/constraints changes). Several of these are *regression*
  tests that check the live solver reproduces numbers saved in `outputs/frontiers/*.csv` — if you
  change the math and these fail, check whether the saved CSVs need regenerating (`python
  src/main.py`) or whether something actually broke.
- `tests/test_app.py` — uses Streamlit's own `streamlit.testing.v1.AppTest` to run the dashboard
  headlessly (no real browser) and check things like: does it load without error, does changing a
  slider change the output, is a given label/metric present, etc. This is how every UI bug fixed
  this session was first turned into a failing test before being fixed (test-driven).
- Run everything with `python -m pytest tests -v` from the repo root — currently 73 tests, all
  passing.

If you add a new feature, the pattern used throughout this session was: write a test that
describes the desired behavior, watch it fail, implement the minimal change to make it pass, then
run the *whole* suite before committing (not just the new test) — a few UI changes this session
had knock-on effects on earlier tests' assumptions (e.g. renamed metrics, removed sliders) and the
full suite catches that.

---

## 9. Dependencies

```
numpy, pandas, scipy, yfinance, pandas_datareader, matplotlib   — core (pre-existing)
streamlit, altair                                                — dashboard (added this session;
                                                                     altair ships inside streamlit)
pytest                                                            — dev-only, for running tests
```

Versions actually installed and tested against in this session: streamlit 1.64.0, altair 6.3.0,
scipy 1.17.1, pandas 3.0.5, numpy 2.4.3, pytest 9.1.1.

---

## 10. Git / GitHub state

- Everything described above is committed and pushed to the `main` branch of
  `https://github.com/guneesh0601/MSO_project2026.git`. There is no separate feature branch in
  active use — all work this session went directly onto `main`, pushed as a normal (non-force)
  push each time, so the full commit history is intact and nothing was overwritten.
- `git log --oneline` on `main` will show each change as its own commit with a descriptive
  message — worth skimming if you want the blow-by-blow instead of this summary.
- The paper PDF, if you have a copy, should **not** be added to git (see `.gitignore` — it's
  excluded on purpose for copyright reasons).

---

## 11. Suggested next steps, if you want a starting todo list

1. **Finish §6.1** — check all 12 current frontiers (not just CPI/Symmetric) for dominated points
   now that the equity cap is gone, and decide whether `gamma` still needs adjusting.
2. **Decide on §6.5** — should "High" risk level really be allowed to recommend a 100%-one-asset
   portfolio, or should some sensible diversification limit come back (as a documented assumption,
   separate from the old per-risk-level equity cap)?
3. **Improve §6.2** — replace the ad-hoc `rho_i` forecast rule with something sourced from real
   published numbers (policy rate for cash, current yields for bonds, implied equity premium for
   equities), with a clear note on where each number came from and when it was pulled.
4. Everything else in §6 is lower priority but worth knowing about.

If anything in this report doesn't match what you find in the code, the code is the source of
truth — this is a best-effort summary of a long conversation, not a spec.
