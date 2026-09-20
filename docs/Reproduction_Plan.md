# Reproducing "Opti-Money at Bank Hapoalim" — Plan and Math Explained Simply

Source paper: Avriel, Pri-Zan, Meiri, Peretz (2004), *"Opti-Money at Bank Hapoalim: A Model-Based Investment Decision-Support System for Individual Customers"*, Interfaces 34(1), pp. 39–50.

This document explains, in plain English:
1. What the paper's model actually is
2. Every variable and constraint, defined simply
3. A concrete, honest plan for reproducing it (including what we have to fill in ourselves, since the paper doesn't give real data)

---

## 1. What problem is the paper solving?

A bank customer walks in with money to invest. The bank must recommend **what fraction of the money to put into each asset class** (Israeli stocks, government bonds, foreign bonds, foreign stocks, deposits, etc.) so that the portfolio:

- gives a good expected return,
- has controlled risk,
- tracks (doesn't stray too far from) a **benchmark** the customer cares about (e.g. inflation, USD, or the shekel interest rate),
- respects the customer's personal constraints (risk appetite, liquidity needs, currency preference, restrictions on illiquid assets, portfolio turnover limits).

This is a **modified version of the classical Markowitz mean-variance portfolio model**. The paper's core contribution is *how* they modified Markowitz to (a) avoid ugly "corner solutions" (portfolios that dump everything into 1–2 assets) and (b) let customers define risk relative to a benchmark instead of just raw variance.

There is no single "the answer" portfolio — the system builds a whole **efficient frontier** (many optimal portfolios at different risk/return levels) for every combination of customer inputs, in a big overnight batch job, and the CRM (bank advisor) just looks up the right one during a live meeting.

---

## 2. Basic setup and notation (defined simply)

| Symbol | Meaning in plain English |
|---|---|
| $n$ | Number of asset classes we can invest in (paper uses ~60 real ones; we'll use a smaller representative set, see Section 5) |
| $x_i$ | **Decision variable.** Fraction of the portfolio invested in asset class $i$. This is what the optimizer solves for. |
| $T$ | Number of past months used to measure historical risk (paper uses $T=36$, i.e. 3 years of monthly data) |
| $r_{t,i}$ | The actual historical return of asset $i$ in month $t$ (this is data, not a decision variable) |
| $\rho_i$ | The **expected future return** the bank forecasts for asset $i$ (e.g., next 12 months). This is a forecast input, not historical data. |
| $\text{PortfRet}_t$ | The portfolio's historical return in month $t$, computed from the $x_i$ and the historical $r_{t,i}$ |
| $\text{ExpRet}$ | The portfolio's **expected future** return, computed from the $x_i$ and the forecasts $\rho_i$ |
| $\text{BchRet}_t$ | The benchmark's historical return in month $t$ (e.g. CPI inflation that month) |
| $m_j$ | The weight of asset class $j$ in a reference "market portfolio" (a sensible, typical, diversified portfolio used only to keep the optimizer from producing extreme/unbalanced results) |
| $\gamma$ | A small positive constant that controls how strongly the optimizer is pulled toward the market portfolio $m_j$ (a "leash," not a hard rule) |
| $\omega_t$ | A weight given to month $t$ when measuring risk — more recent months can count more (see decay factor below) |
| $\lambda$ | The decay factor controlling how much more recent months are weighted vs older months |

### 2.1 The two basic building-block equations

**Budget constraint** — the fractions must add to 1, and you cannot hold a negative amount of an asset (no short-selling):
$$\sum_{i=1}^{n} x_i = 1, \qquad x_i \geq 0 \quad \text{for all } i$$

**Historical portfolio return in month $t$** — just a weighted average of what each asset actually returned that month:
$$\text{PortfRet}_t = \sum_{i=1}^{n} r_{t,i}\, x_i, \qquad t = 1, 2, \dots, T$$

**Expected future portfolio return** — same idea but using the forecast instead of history:
$$\text{ExpRet} = \sum_{i=1}^{n} \rho_i\, x_i$$

Note the important subtlety the paper makes explicit: **$\rho_i$ (forecast) is *not* derived from the average of $r_{t,i}$ (history).** Historical data is used only to measure *risk* (how bumpy/uncertain returns have been); the forecast $\rho_i$ is a separate, independently-supplied number (e.g., from the bank's economists). This is a deliberate design choice, and we must replicate it — i.e., don't just plug in historical mean return as your "expected return."

---

## 3. The four risk measures (this is the heart of the modification)

Classical Markowitz uses only risk measure (4) below. Opti-Money offers **four choices**, and mixes the chosen one with a "stay close to a sensible market portfolio" term (Section 4). Here they are, explained one at a time.

### (1) Symmetric Risk — "how much does my portfolio wobble around the benchmark, in both directions?"

$$\text{Symmetric Risk} = \sum_{t=1}^{T} \omega_t \Big[(\text{PortfRet}_t - \text{BchRet}_t) - \text{Av}(\text{PortfRet}_t - \text{BchRet}_t)\Big]^2$$

Plain English: look at the *gap* between the portfolio's return and the benchmark's return each month. Compute the average gap over all $T$ months. Then measure, month by month, how far the gap wanders from that average gap, square it (so ups and downs both count as "bad"), and take a weighted sum. This is just Markowitz-style variance, except computed on **(portfolio − benchmark)** instead of on the raw portfolio return. $\text{Av}(\cdot)$ just means the weighted average over $t=1,\dots,T$.

### (2) Asymmetric Downside Risk — "only punish underperforming the benchmark, not outperforming it"

$$\text{Asymmetric Risk} = \sum_{t=1}^{T} \omega_t\Big[(\text{PortfRet}_t - \text{BchRet}_t)_- - \text{Av}\big((\text{PortfRet}_t-\text{BchRet}_t)_-\big)\Big]^2$$

where the subscript minus means:
$$(\text{PortfRet}_t - \text{BchRet}_t)_- = \min\big[0,\ \text{PortfRet}_t - \text{BchRet}_t\big]$$

Plain English: this is the same idea as (1), but before doing anything else, any month where the portfolio *beat* the benchmark gets **clipped to zero** (it "doesn't count as risk" — only shortfalls do). This matches how real investors think: beating your benchmark is not "risk," only falling behind it is. This is the paper's realistic argument for downside risk over symmetric variance.

### (3) Multi-benchmark variability
Same as (1) or (2), but instead of one benchmark, you take a **weighted average of several benchmarks** (e.g., partly CPI, partly USD) and measure variability around that blend. No new formula needed — just replace $\text{BchRet}_t$ with a weighted mix of multiple benchmark series.

### (4) Classical Markowitz Variance — "risk = the portfolio's own volatility, no benchmark at all"

$$V = \sum_{i=1}^n \sum_{j=1}^n \sigma_{ij}\, x_i x_j$$

where $\sigma_{ij}$ is the covariance between historical returns of assets $i$ and $j$:
$$\sigma_{ij} = \frac{1}{T-1}\sum_{t=1}^{T} R_{t,i} R_{t,j}, \qquad R_{t,i} = r_{t,i} - \frac{1}{T}\sum_{t=1}^{T} r_{t,i}$$

**Important implementation trick the paper highlights:** Opti-Money never actually builds an $n\times n$ covariance matrix (with $n\approx 60$ that's ~1,800 numbers to maintain, and it gets stale/expensive). Instead they substitute the covariance formula directly into $V$ and simplify:

$$V = \frac{1}{T-1}\sum_{i=1}^n\sum_{j=1}^n\left(\sum_{t=1}^T R_{t,i}R_{t,j}\right) x_i x_j$$

This is mathematically identical, but computationally it means: at solve-time, you compute $\text{PortfRet}_t$ (as above) from the *de-meaned* returns, and the variance of *that one time series* over $T$ months **is** $V$. In other words:
$$V = \text{Var}_t(\text{PortfRet}_t) = \frac{1}{T-1}\sum_{t=1}^T \left(\text{PortfRet}_t - \overline{\text{PortfRet}}\right)^2$$
You only ever need one running number series (the portfolio's own historical monthly return), never the full covariance matrix. This is exactly the same trick as risk measures (1)–(2): compute a portfolio-level time series first, then take its variance. This is why the paper says "we do not explicitly compute covariance-type matrices."

---

## 4. The market-tracking term (this is what fixes the "corner solution" problem)

**The problem:** In plain Markowitz, the optimizer often produces "corner solutions" — 80% in one bond, 0% in everything else, because that literally minimizes the math, even though no sane advisor would recommend it.

**The paper's fix:** Add a second penalty term that punishes the optimizer for straying too far, asset-by-asset, from a sensible **reference market portfolio** $m_j$ (a realistic, diversified benchmark portfolio, e.g., value-weighted across all asset classes). This is just a Euclidean-distance penalty:

$$\text{Tracking Term} = \gamma \sum_{j=1}^{n} (x_j - m_j)^2$$

**The full modified objective function** (example shown using the symmetric risk measure; any of the 4 could be substituted in the first term):

$$\text{Minimize} \quad \underbrace{\sum_{t=1}^{T} \omega_t\Big[(\text{PortfRet}_t - \text{BchRet}_t) - \text{Av}(\text{PortfRet}_t - \text{BchRet}_t)\Big]^2}_{\text{risk term (pick one of the 4)}} \;+\; \underbrace{\gamma \sum_{j=1}^n (x_j - m_j)^2}_{\text{stay close to a normal portfolio}}$$

$\gamma$ is chosen small, so it acts like a gentle leash rather than a hard rule — it nudges the optimizer away from extreme corner solutions without materially hurting the risk/return tradeoff. The paper doesn't give a specific numeric value for $\gamma$; we will need to calibrate it ourselves (Section 6).

---

## 5. Exponentially decaying weights $\omega_t$ (recency weighting)

Instead of treating all $T=36$ months equally (weight $1/T$ each), Opti-Money lets recent months matter more:

$$\omega_t = \lambda^{\,t-1} \Big/ \sum_{j=1}^{T}\lambda^{\,j-1}, \qquad t = 1,2,\dots,T$$

- $t=1$ is defined as **the most recent month** (1 month ago), $t=T$ is the oldest (36 months ago).
- If $\lambda = 1$: all weights collapse to $1/T$ (equal weighting, the traditional method).
- Paper's example: $\lambda = 0.95$ gives $\omega_1 = 0.0594$ (recent month) down to $\omega_{36}=0.0099$ (oldest month), vs. flat $1/36 = 0.0278$ for equal weighting.

**Why it matters:** a shock (e.g. a market crash) immediately raises perceived risk, and that effect fades gradually as the shock ages out of the window — rather than suddenly dropping out of the model the instant it's more than 36 months old (which is what happens with equal weights).

---

## 6. Building the efficient frontier (the actual algorithm to implement)

For **one fixed combination** of customer inputs (benchmark, risk-measure choice, λ, γ, constraints), Opti-Money doesn't solve one optimization — it solves a whole **sequence of $K$ optimizations** to trace out a frontier:

1. **Step 1 — Min-risk portfolio:** Solve "minimize (risk term + tracking term)" with *no* constraint on expected return at all. This gives the lowest-risk point on the frontier.
2. **Step 2 — Max-return portfolio:** Solve "maximize $\text{ExpRet}$" subject only to the basic constraints (budget, bounds, etc. — ignore risk). This gives the highest-return, highest-risk point on the frontier.
3. **Step 3 — Pick $K$ target returns:** Take the expected returns from steps 1 and 2, and pick $K$ evenly spaced values in between (e.g. $K=10$ intermediate targets).
4. **Step 4 — Solve $K$ constrained problems:** For each target return level $\text{ExpRet}^{(k)}$, solve:
$$\text{Minimize (risk term + tracking term)} \quad \text{s.t.} \quad \text{ExpRet} = \text{ExpRet}^{(k)}, \ \ \sum x_i = 1,\ \ x_i \ge 0 \ (\text{+ any other constraints})$$

The $K+2$ portfolios (steps 1, 2, and the $K$ from step 4) together form a **discrete approximation of the balanced efficient frontier**. This whole procedure must be repeated for every combination of customer-facing parameters (risk level, benchmark, horizon, liquidity constraint, currency preference) — this is why the real system produces "thousands" of frontiers in a batch run. For our reproduction, we'll do this for a handful of representative customer profiles rather than the full combinatorial explosion (see Section 8).

---

## 7. Constraints beyond the basics

The paper mentions these but does not give exact formulas — we implement them as standard linear constraints:

- **Budget & no short-selling:** $\sum_i x_i = 1,\ x_i \ge 0$ (always present).
- **Risk-level bounds:** each of the 5 customer risk categories (low, low-medium, medium, risk-oriented, high) maps to bounds on total equity-like allocation (e.g. "low risk → equities ≤ 20%"). Paper doesn't give exact numbers; we define reasonable bounds ourselves and document the assumption.
- **Liquidity constraint:** an upper bound on the combined weight of illiquid asset classes (e.g. CDs): $\sum_{i \in \text{Illiquid}} x_i \le L$.
- **Currency constraint:** bound on domestic vs. foreign-currency asset weight: $\sum_{i\in\text{Foreign}} x_i \le F$ (or a fixed split if the customer explicitly restricts to one currency).
- **Turnover constraint:** limits how much the *new* portfolio can differ from the customer's *existing* portfolio $x_i^{\text{old}}$, e.g. $\sum_i |x_i - x_i^{\text{old}}| \le \text{Turnover}_{\max}$ (paper only says "no more than a certain percentage of new assets"; exact formula not given — we'll use this standard L1-turnover form, or a simpler "new-asset fraction" cap).

---

## 8. Postoptimal rounding (mentioned, not detailed)

The paper notes that after solving, fractions must be rounded to "predetermined discrete values" (e.g., round each $x_i$ to the nearest 1% or 5%) for practical execution, using a method from a separate working paper (Avriel 2003, not public) — similar in spirit to the Balinski–Young (1977) apportionment method. We will **not** try to reverse-engineer that exact undisclosed method; instead we'll implement a standard, well-documented largest-remainder rounding procedure (same family as Balinski–Young apportionment) that:
- rounds all $x_i$ to a chosen grid (e.g., nearest 1%),
- guarantees the rounded values still sum exactly to 100%,
- minimizes total rounding distortion.
This is a reasonable, honestly-labeled substitute, not a claim of reproducing their exact proprietary algorithm.

---

## 9. What we can't reproduce exactly, and how we'll honestly fill the gap

The paper is a business case study, not a reproducible research paper — it deliberately omits:

| Missing piece | What we'll do instead |
|---|---|
| The real ~60 asset classes and their exact definitions | Define a smaller (~10–15) representative set of asset classes: Israeli TASE stock index, Israeli CPI-linked govt bonds (short/medium/long), Israeli unlinked govt bonds, a foreign bond proxy, S&P 500, a Euro-area equity index, USD cash/money market, ILS savings deposit. Document every substitution. |
| Real historical return data ($r_{t,i}$) held internally by the bank | Pull public monthly data for public proxies (e.g., TA-125 index, US Treasury/US aggregate bond index, S&P 500, EUR/USD, ILS/USD, Israeli CPI, Bank of Israel rate) over the most recent 36 months available, via public sources (Yahoo Finance, FRED, Bank of Israel public statistics). |
| The bank's proprietary forward-looking forecasts $\rho_i$ | Use a documented, simple forecasting rule (e.g., a blend of historical mean return and a risk-free-rate-plus-premium assumption) — clearly labeled as *our* assumption standing in for the bank's forecasting committee. |
| Exact value of $\gamma$, $\lambda$, $K$, and the market portfolio $m_j$ | Choose reasonable values ($\lambda=0.95$ as given in the paper; $\gamma$ calibrated by trying a few values and picking one that removes corner solutions without much frontier distortion — we'll show this sensitivity explicitly; $m_j$ defined as an equal- or value-weighted mix across our asset classes; $K=10$). |
| Exact solver (GAMS/MINOS) | Use an open equivalent: Python with `scipy.optimize` (SLSQP, handles nonlinear objective + linear constraints) or `Pyomo` + `IPOPT` for a closer match to a professional NLP solver. This preserves the "nonlinear program with continuous variables" nature of the original. |
| Exact discrete rounding grid/method | Use a documented largest-remainder rounding to a stated grid (Section 8), not the undisclosed Avriel (2003) method. |

We will state these substitutions explicitly in any write-up/report — this is standard and expected practice when reproducing a practitioner paper that used confidential production data.

---

## 10. Concrete implementation roadmap

1. **Data collection module** — fetch/clean 36 months of monthly returns for the ~10–15 proxy asset classes + the 3 benchmark series (CPI, risk-free/BoI rate proxy, USD FX rate). Store as a $T \times n$ returns matrix and $T$-length benchmark vectors.
2. **Forecast module** — produce the $\rho_i$ vector using the documented simple rule from Section 9.
3. **Risk-measure module** — implement all 4 risk measures as functions of $x$ (symmetric, asymmetric downside, multi-benchmark, classical variance), each built by first computing $\text{PortfRet}_t(x)$ and then aggregating — matching the paper's "never build the covariance matrix explicitly" approach.
4. **Objective module** — combine chosen risk measure + $\gamma \sum (x_j-m_j)^2$ tracking term.
5. **Constraint module** — budget, bounds by risk category, liquidity cap, currency cap, turnover cap.
6. **Optimizer** — implement the 4-step efficient-frontier algorithm (Section 6) using SLSQP/IPOPT for each of the $K+2$ subproblems.
7. **Rounding module** — largest-remainder rounding to a grid (Section 8).
8. **Validation / comparison to paper's qualitative claims**:
   - Confirm the frontier is smooth/balanced (no corner solutions) when $\gamma>0$, and compare to the degenerate/corner-heavy frontier when $\gamma=0$ — this directly reproduces the paper's central qualitative claim.
   - Confirm medium-risk portfolios show higher cumulative return than low-risk portfolios over the backtest window, echoing Figures 2–4 / Table 2 (we can't reproduce their exact percentages since it's different data, but the *ordering* and *shape* of results should match).
   - Sanity-check that using asymmetric downside risk gives different (typically more conservative on the downside) weights than symmetric risk, for the same benchmark.
9. **Write-up** — a short report presenting the reproduced frontier, comparison plots (analogous to the paper's Figures 2–4), and an explicit "what we approximated vs. the original" section (from Section 9's table).

---

## 11. Suggested tech stack

- **Language:** Python (widely available, easy to inspect/debug, good optimization libraries — a fair open substitute for GAMS/MINOS/Delphi used in the original).
- **Data handling:** `pandas`, `numpy`.
- **Optimization:** `scipy.optimize.minimize` (method `SLSQP`) for a first pass; optionally `Pyomo` + `IPOPT` if we want a solver closer in spirit to MINOS (handles nonlinear objective with linear/nonlinear constraints well).
- **Data sources:** `yfinance` for equity/FX/index data; Bank of Israel and Israel CBS public data portals for CPI and the BoI interest rate (may need manual CSV download if no API); FRED for any US-side series if used as a proxy.
- **Plotting:** `matplotlib` for frontier and cumulative-performance charts.

---

## Next step

This document is the plan only — no code has been written yet, as requested. Once you confirm this plan (or want changes to the asset universe, data sources, or parameter choices), the next step is to implement Sections 10's modules one at a time, starting with data collection, and to validate the optimizer against a very small toy case (e.g., 3 assets, hand-checkable) before scaling to the full asset set.
