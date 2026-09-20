# Master Plan: How We Will Actually Build This in Python

This file is the bridge between "I understand the math now" (covered in Reproduction_Plan.md, loop.md, and ExpRet_Constraint_Explained.md) and "here is the actual software I need to write." It lists every file we'll create, what goes inside each one in plain language, what equations live where, and the exact order to build and test things so nothing breaks silently.

---

## 1. The overall shape of the project (folders and files)

```
MSO project/
│
├── Reproduction_Plan.md              (already written — the big picture plan)
├── loop.md                            (already written — explains the 3 nested loops)
├── ExpRet_Constraint_Explained.md     (already written — deep dive on one constraint)
├── Master_Implementation_Plan.md      (this file)
│
├── data/
│   ├── raw/                           (downloaded price data, untouched, as CSV files)
│   └── processed/                     (cleaned-up return tables, ready to use)
│
├── src/                               (all our actual Python code lives here)
│   ├── config.py
│   ├── data_loader.py
│   ├── returns_calculator.py
│   ├── forecasts.py
│   ├── risk_measures.py
│   ├── objective.py
│   ├── constraints.py
│   ├── optimizer.py
│   ├── frontier_builder.py
│   ├── customer_profiles.py
│   ├── rounding.py
│   └── main.py
│
├── tests/
│   └── test_toy_example.py            (small hand-checkable sanity tests)
│
└── outputs/
    ├── frontiers/                     (saved results per customer profile)
    └── plots/                         (charts we generate, like the paper's Figures 2-4)
```

Each `.py` file has ONE clear job. Below, file by file, in the order we will actually write and test them.

---

## 2. `config.py` — the settings file (write this first)

**Purpose:** one single place where every fixed number/setting lives, so nothing is hidden or duplicated across files.

**What goes in it (plain values, no equations yet):**
- The list of asset classes we're using (our smaller proxy set — e.g. Israeli stock index, CPI-linked bonds, unlinked bonds, foreign bonds, S&P 500, cash/deposits)
- T = 36 (number of historical months to use)
- Lambda = 0.95 (the decay factor from the paper)
- Gamma (the tracking-term weight — we'll start with a small test value like 0.01 and tune it)
- K = 10 (number of intermediate frontier points)
- The risk-category bounds we're assuming (since the paper doesn't give exact numbers, we define our own here and document it as an assumption)
- File paths (where raw data is stored, where outputs go)

**Why first:** every other file will need to read these values, so it must exist before anything else.

---

## 3. `data_loader.py` — getting real price data

**Purpose:** download monthly price data for every asset class in our list, and save it as CSV files in `data/raw/`.

**What it does, step by step:**
1. For each asset in `config.py`'s list, fetch monthly closing prices for the past several years (e.g. using the `yfinance` Python library for anything with a stock ticker, and manual CSV downloads for things like Israeli CPI or Bank of Israel rates, which may not be available through a simple API).
2. Save each asset's raw price series as its own CSV file (one column: date, one column: price).

**No equations here at all** — this file is pure data-fetching, nothing mathematical happens yet.

---

## 4. `returns_calculator.py` — turning prices into the "r" table

**Purpose:** this is where the r-sub-t-comma-i table (from your last question) actually gets built, plus the benchmark return series.

**The equation that lives here** (in plain words, as we worked out by hand earlier):

    return for asset i in month t  =  (price at end of month t  minus  price at end of month t-1)  divided by  (price at end of month t-1)

**What the code does:**
1. Load each asset's raw price CSV.
2. Apply the formula above, column by column (asset by asset), to turn each price series into a return series.
3. Stack all these return series side by side into one big table: rows = months (t = 1 to 36), columns = assets (i = 1 to n). This table is exactly the r data we've been discussing.
4. Do the same calculation for each benchmark (CPI, USD rate, Bank of Israel rate) to build the BchRet series for each one.
5. Save the finished return table and benchmark series into `data/processed/` as clean CSV files, so we never need to redo this step unless the raw data changes.

**Sanity check to build alongside this file:** manually verify 2-3 rows of the computer-generated table against a hand calculation (like the tiny stock-price example from earlier), to make sure the formula was coded correctly before trusting the rest of the pipeline.

---

## 5. `forecasts.py` — building the rho vector

**Purpose:** produce the expected future return forecast for each asset, called rho, that we discussed is separate from historical data.

**What goes in it:** since we don't have the bank's real forecasting committee, we define a simple, clearly-labeled substitute rule here — for example, a blend of the asset's own recent historical average return and a small risk premium above the risk-free rate. This file should have a clear comment/note that this is OUR assumption standing in for the bank's real process (as documented in Reproduction_Plan.md, Section 9).

**Output:** one single number per asset (a vector of length n), saved for reuse.

---

## 6. `risk_measures.py` — the heart of the math

**Purpose:** this file contains the actual formulas for PortfRet, and all the risk measures, exactly as derived in our earlier conversations.

**Functions to write, and the equation each one implements:**

1. **portfolio_return_series(x, returns_table)** — computes PortfRet for every month t, given a candidate portfolio x:

       PortfRet for month t  =  sum over all assets i of (return of asset i in month t  times  x_i)

   This produces a list of 36 numbers (one per month) — this single function is reused by every risk measure below, since they all start from this same series.

2. **symmetric_risk(x, returns_table, benchmark_series, decay_weights)** — computes the symmetric risk measure:
   - First compute the gap each month: PortfRet(t) minus BchRet(t).
   - Compute the (decay-weighted) average of that gap across all 36 months.
   - Square the difference between each month's gap and that average.
   - Take the decay-weighted sum of those squared differences.

3. **asymmetric_risk(x, returns_table, benchmark_series, decay_weights)** — same as above, but BEFORE doing anything else, replace any month where PortfRet beat BchRet (i.e., the gap is positive) with zero, using the "clip to zero" rule: take the smaller of (0, the gap). Then proceed exactly like symmetric_risk on this clipped series.

4. **markowitz_variance(x, returns_table)** — computes the classical risk measure, using the "no explicit covariance matrix" trick we discussed:
   - Compute the PortfRet series (same as function 1).
   - Compute the plain variance of that one series across the 36 months (subtract the mean, square, average, using T-1 in the denominator).

5. **decaying_weights(lambda_value, T)** — a small helper function that builds the omega-sub-t weights described earlier:

       weight for month t  =  (lambda to the power of (t-1))  divided by  (the sum of lambda to the power of (j-1), for j = 1 to T)

**Testing approach for this file:** build a tiny toy return table (like our earlier 3-month, 3-asset example) and manually compute what each risk measure SHOULD give by hand, then check the function's output matches.

---

## 7. `objective.py` — combining risk + the tracking term

**Purpose:** implements the full objective function that gets minimized, combining whichever risk measure is chosen with the market-tracking penalty.

**The equation:**

    objective(x)  =  (chosen risk measure, computed from x)  +  gamma  times  (sum over all assets j of (x_j minus market_weight_j) squared)

**What the code does:** takes a candidate x, a choice of which risk measure to use (symmetric / asymmetric / Markowitz), and the market portfolio weights (m_j, which we define in `config.py` as a simple even or value-weighted mix), and returns one single number: how "bad" this candidate x currently is.

---

## 8. `constraints.py` — every rule x must obey

**Purpose:** encode every constraint we discussed, as separate, clearly labeled functions.

**What goes in it, one function per rule:**
- **budget_constraint(x):** checks that the sum of all x_i equals 1.
- **nonnegativity_constraint(x):** checks every x_i is greater than or equal to 0 (this is usually handled by telling the solver the "bounds" for each variable, rather than writing a separate function — we'll do it the standard way scipy expects).
- **expected_return_constraint(x, forecasts, target_k):** computes ExpRet from x and the forecast vector, and checks it equals the specific target_k we're solving for at this frontier point (this is exactly the constraint from ExpRet_Constraint_Explained.md).
- **liquidity_constraint(x):** checks the combined weight of illiquid assets doesn't exceed our chosen limit.
- **currency_constraint(x):** checks the combined weight of foreign-currency assets doesn't exceed our chosen limit.
- **turnover_constraint(x, existing_portfolio):** checks how much x differs from an existing portfolio, if one is provided, and keeps it under our chosen limit.

Each of these will be written in the exact format scipy's optimizer expects (a function that returns zero when satisfied exactly, for equality constraints, or a non-negative number when satisfied, for inequality constraints).

---

## 9. `optimizer.py` — this is "Loop C," wrapped around scipy

**Purpose:** this file doesn't implement the gradient search itself (recall: that's scipy/MINOS's internal job, not ours) — it just correctly PACKAGES our objective and constraints and hands them to scipy's solver, then returns the answer.

**What it does:**
1. Takes in: which risk measure to use, which target return (if any), which constraint set applies (based on the customer profile), and a starting guess for x (e.g. equal weights across all assets).
2. Calls `scipy.optimize.minimize(...)` with method `SLSQP`, passing in the objective function from `objective.py` and the constraint functions from `constraints.py`.
3. Returns the resulting optimal x, and the achieved risk and return values.

**This one file effectively implements all three of the problem types we discussed:**
- Call it with no return-target constraint and the risk-measure objective → gives the Step 1 (min-risk) portfolio.
- Call it with the objective flipped to maximize ExpRet and no risk term at all → gives the Step 2 (max-return) portfolio.
- Call it with a specific target_k constraint active → gives one of the K middle points.

---

## 10. `frontier_builder.py` — this is "Loop B"

**Purpose:** for ONE fixed customer profile, build the whole efficient frontier (K+2 points), by calling `optimizer.py` repeatedly.

**What it does, step by step (this is literally the 4-step procedure from the paper's Appendix, now as real code):**
1. Call the optimizer once for Step 1 (min risk, ignore return) → save this portfolio.
2. Call the optimizer once for Step 2 (max return, ignore risk) → save this portfolio.
3. Compute K evenly spaced target returns between Step 1's and Step 2's resulting returns.
4. Loop over each of the K targets, calling the optimizer once per target with that target locked in as a constraint → save each resulting portfolio.
5. Collect all K+2 portfolios (their x vectors, their risk scores, their return values) into one table, and return it.

---

## 11. `customer_profiles.py` — this is "Loop A"

**Purpose:** generate the list of customer profile combinations we'll test (a smaller, manageable version of the bank's ~36,000), and translate each profile into the specific settings `frontier_builder.py` needs (which benchmark series, which bounds, which liquidity/currency limits).

**What it does:** builds a simple list, for example: 5 risk levels times 3 benchmarks times 2 horizons = 30 profiles (a number we can realistically compute and inspect, rather than tens of thousands), and for each one, produces a small settings object listing exactly which constraint values and which benchmark apply.

---

## 12. `rounding.py` — the postoptimal adjustment step

**Purpose:** implements the "largest remainder" rounding approach discussed earlier, rounding each x_i to a clean grid (e.g., nearest 1%) while making sure the rounded values still sum to exactly 100%.

**What it does:** takes a raw solved x vector (with messy decimals like 0.0833) and outputs a clean, presentable version (like 0.08 or 0.09, chosen so the total still adds to exactly 1.00).

---

## 13. `main.py` — the file that runs everything, start to finish

**Purpose:** ties every other file together into one runnable script.

**What it does, in order:**
1. Load settings from `config.py`.
2. Run `data_loader.py` (or load already-downloaded data if it exists).
3. Run `returns_calculator.py` to build the r table and benchmark series.
4. Run `forecasts.py` to build the rho vector.
5. Run `customer_profiles.py` to get our list of profiles to test.
6. For each profile, run `frontier_builder.py` to get its efficient frontier.
7. Run `rounding.py` on each resulting portfolio.
8. Save all results into `outputs/frontiers/` as CSV tables.
9. Generate plots (risk vs. return curves, one line per risk measure, per profile) and save them into `outputs/plots/`.

---

## 14. `tests/test_toy_example.py` — write this early, and keep using it

**Purpose:** a small, fully hand-checkable example (2-3 assets, 3-4 months of made-up data) that we can verify by hand — exactly like the tiny examples used throughout our conversation (the stock/bond/cash example, the 2-asset ExpRet example). Every time we write a new function in `risk_measures.py`, `objective.py`, `constraints.py`, or `optimizer.py`, we run it against this toy example first and check the numbers match what we calculated by hand on paper, BEFORE trusting it on the real 36-month, multi-asset data.

**Why this matters:** with real data and many assets, if something is wrong in the code, the mistake is very hard to spot just by looking at the output numbers — they'll just look like "some portfolio." With a tiny toy example we've already solved by hand, any mismatch is immediately obvious.

---

## 15. The exact order we will build things in (do not skip ahead)

1. `config.py` — just settings, nothing to test yet.
2. `data_loader.py` — confirm we can actually download and save real price data for our chosen assets.
3. `returns_calculator.py` — confirm the r table and benchmark series look correct on a few hand-checked rows.
4. `forecasts.py` — confirm we get one sensible rho number per asset.
5. `risk_measures.py` + `tests/test_toy_example.py` together — build both at once, verifying every risk formula against hand calculations on the toy example before moving on.
6. `objective.py` — confirm it correctly adds the tracking term to whichever risk measure is chosen.
7. `constraints.py` — confirm each constraint function correctly flags valid vs invalid x on simple hand-picked examples (like our earlier 2-asset example that solves to x_A = 0.0833).
8. `optimizer.py` — first test on the tiny toy example, confirming it reproduces the exact by-hand answer we already calculated in ExpRet_Constraint_Explained.md for the 2-asset case.
9. `frontier_builder.py` — run it once on the toy example, confirm you get a sensible small frontier (K+2 points, return increasing, risk generally increasing too).
10. `customer_profiles.py` — build the small list of profiles we'll actually test.
11. `rounding.py` — confirm rounded weights still sum to exactly 1.00 on a few test cases.
12. `main.py` — now, and only now, run the FULL real-data pipeline end to end.
13. Generate the comparison plots and check them against the paper's qualitative claims (medium-risk portfolios beating low-risk ones over time; corner solutions disappearing once gamma is turned on; asymmetric risk producing different, typically more conservative, weights than symmetric risk for the same target return).

---

## 16. Libraries we'll need (install these first)

- `pandas` — for handling all the data tables (prices, returns, results)
- `numpy` — for the underlying math/array operations
- `scipy` — specifically `scipy.optimize.minimize` with the SLSQP method, our stand-in for MINOS
- `yfinance` — for pulling public price data for stock/index/FX proxies
- `matplotlib` — for the frontier and performance charts

---

## 17. What "done" looks like

By the end of this plan, we will have: a small set of real historical return data we built ourselves; a working risk-measure engine matching all three formulas from the paper; a solver pipeline that reproduces the paper's exact 4-step efficient-frontier construction; a small set of test customer profiles with their own frontiers; rounded, presentable portfolios; and comparison charts that let us check our reproduction behaves the way the paper describes (even though our specific numbers will differ, since we're using different, smaller, public proxy data instead of the bank's real internal data — this gap is intentional and documented in Reproduction_Plan.md, Section 9).
