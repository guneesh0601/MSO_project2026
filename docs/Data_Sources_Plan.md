# Where Every Dataset Actually Comes From

This file nails down, concretely, exactly which real-world data source we'll use for each asset class and benchmark in our reproduction — this is the specific detail that `data_loader.py` (from Master_Implementation_Plan.md) will implement. I checked each of these against real, currently-working sources before writing them here, rather than guessing.

---

## The honest starting point

Bank Hapoalim's real system used ~60 internal, proprietary asset classes and internal forecasts that were never published. We cannot get those. What we CAN get is public data for reasonable stand-ins covering the same broad categories the paper describes: Israeli stocks, Israeli government bonds (CPI-linked and unlinked), foreign bonds, foreign stocks, and the four benchmarks (CPI, Bank of Israel rate, USD, Euro). Below is exactly where each one comes from.

---

## 1. Israeli stock market (equity asset class)

- **What we need:** a broad Israeli stock index, monthly closing values.
- **Source:** Yahoo Finance, ticker `^TA125.TA` (the TA-125 index, the 125 largest companies on the Tel Aviv Stock Exchange — this is a very close real-world match to what the paper describes).
- **How to fetch it:** the Python library `yfinance`, e.g. `yfinance.download("^TA125.TA", start=..., end=..., interval="1mo")`.
- **Confidence:** confirmed working ticker as of today.

## 2. Foreign stock market (US equity asset class)

- **What we need:** the paper explicitly mentions the S&P 500 as one of the foreign stock indices used.
- **Source:** Yahoo Finance, ticker `^GSPC`.
- **How to fetch it:** same `yfinance.download(...)` call.
- **Confidence:** very high — this is one of the most standard tickers in existence.

## 3. Foreign stock market (Euro-area equity, optional extra)

- **What we need:** if we want a second foreign-equity class (the paper mentions Euro-related benchmarks/assets).
- **Source:** Yahoo Finance, ticker `^STOXX50E` (Euro Stoxx 50 index).
- **Confidence:** moderate-high, standard well-known ticker, but we should double check it downloads cleanly when we actually write the code, since regional indices occasionally have data gaps.

## 4. USD/ILS exchange rate (both a benchmark AND used for currency conversion)

- **What we need:** the shekel-to-dollar exchange rate, monthly.
- **Source:** Yahoo Finance, ticker `USDILS=X` (this is the standard Yahoo Finance format for currency pairs: BASE-then-QUOTE, followed by `=X`).
- **How to fetch it:** `yfinance.download("USDILS=X", ...)`.
- **Confidence:** confirmed working ticker.

## 5. EUR/ILS exchange rate (optional, paper calls it "new" with limited track record)

- **Source:** Yahoo Finance, ticker `EURILS=X` (same naming convention as above).
- **Confidence:** moderate — follows the same standard convention as USDILS=X, but we should verify it actually returns data when we write the fetch code, since some cross-currency pairs have thinner history.

## 6. Israeli CPI (inflation) — used both as a benchmark and to build CPI-linked bond returns

- **What we need:** monthly Israeli Consumer Price Index level.
- **Source:** FRED (Federal Reserve Economic Data, run by the St. Louis Fed) — this is a free, reliable, well-maintained government-data aggregator, not a paid service. Series ID: `ISRCPIALLMINMEI` ("Consumer Price Index: Total for Israel").
- **How to fetch it:** either the `pandas_datareader` library (`pandas_datareader.data.DataReader("ISRCPIALLMINMEI", "fred", start, end)`), or the `fredapi` Python package with a free FRED API key, or by directly downloading the CSV FRED provides for any series.
- **Confidence:** confirmed — this exact series exists and is free.

## 7. Bank of Israel interest rate (the "riskless rate" benchmark)

This one needed the most digging, so here's the honest picture:

- The Bank of Israel's own official policy-rate database exists, but a clean, free, directly-downloadable time series wasn't confirmed during our search — some third-party services offer it, but only on paid plans.
- **What IS confirmed and free:** FRED hosts related Israeli interest-rate series we can use as a very close substitute for "the riskless rate of interest," specifically:
  - `IR3TIB01ILM156N` — 3-month interbank interest rate for Israel, monthly.
  - `IRLTLT01ILM156N` — Israel long-term (10-year) government bond yield, monthly.
- **Our plan:** use `IR3TIB01ILM156N` as our stand-in for the paper's "riskless rate of interest" benchmark. This is a very reasonable substitute since interbank rates track central bank policy rates closely.
- **Confidence:** confirmed series IDs exist on FRED and are free.

## 8. Israeli government bonds — CPI-linked and unlinked (this is the genuine gap)

This is the one place I want to be fully upfront with you: **there is no clean, free, easily-downloadable historical price series for these specific instruments that I could confirm.** The Tel Aviv Stock Exchange does maintain real bond indices (e.g., the "Tel-Bond" family, and a government CPI-linked bond index), and paid data platforms like CEIC do carry this data — but nothing free and directly automatable turned up.

**Two honest options, and I'd recommend the first:**

**Option A (recommended) — build an approximate bond return series ourselves from the free yield data we already have.** We already have `IRLTLT01ILM156N` (Israel's 10-year government bond yield, monthly, from FRED, free). Bond prices move in a predictable, well-understood way when yields change — there's a standard, simple formula (using something called "duration") that converts a change in yield into an approximate change in bond price. We can build our "Israeli government bond, unlinked" return series this way, clearly documented as an approximation derived from yield data rather than directly observed bond prices. For the CPI-linked version, we'd do the same thing but also add the CPI series (item 6 above) on top, since CPI-linked bonds are designed to move with inflation by construction.

**Option B (more manual, more authentic, more effort) — manually download index data from the TASE website (tase.co.il) itself,** which does publish historical index level data for its bond indices, though not through a simple one-line API call — this would likely mean visiting the site, exporting a CSV by hand, and importing it. This gets you real, not-approximated data, at the cost of it not being a fully automated pipeline step.

**My recommendation:** start with Option A for a first working version, and clearly label it in the code and write-up as "approximated from yield data using duration," which is honest and standard practice. We can upgrade to Option B later if you want more authenticity and are willing to do the manual download step.

## 9. Foreign bonds (a general "foreign fixed income" asset class)

- **What we need:** a proxy for foreign (e.g., US or global) bond exposure.
- **Source:** Yahoo Finance, ticker `AGG` (iShares Core U.S. Aggregate Bond ETF) or `IEF` (iShares 7-10 Year Treasury Bond ETF) — both are real, tradable funds with long, clean daily/monthly price histories, and uses their price directly (already includes reinvested distributions in "adjusted close," which is the correct field to use so that coupon-like payments aren't lost).
- **Confidence:** high — these are extremely standard, heavily-traded ETFs.

## 10. Cash / deposits / money market (the "riskless"/parking asset class)

- **What we need:** a low-risk, steady-return asset representing bank deposits or short-term cash instruments.
- **Source:** we can reuse the same interbank rate series from item 7 (`IR3TIB01ILM156N`), treated as the return earned by holding cash/deposits, rather than needing a separate price series (since deposits don't have a "price" that fluctuates the way a stock or bond does — they simply accrue interest).

---

## Summary table

| # | Asset / benchmark | Source | Identifier | Free & automatable? |
|---|---|---|---|---|
| 1 | Israeli stocks | Yahoo Finance | ^TA125.TA | Yes |
| 2 | US stocks (S&P 500) | Yahoo Finance | ^GSPC | Yes |
| 3 | Euro-area stocks (optional) | Yahoo Finance | ^STOXX50E | Yes (verify on first run) |
| 4 | USD/ILS exchange rate | Yahoo Finance | USDILS=X | Yes |
| 5 | EUR/ILS exchange rate (optional) | Yahoo Finance | EURILS=X | Yes (verify on first run) |
| 6 | Israeli CPI | FRED | ISRCPIALLMINMEI | Yes |
| 7 | Israeli riskless/interbank rate | FRED | IR3TIB01ILM156N | Yes |
| 8a | Israeli govt bonds (unlinked) | FRED (approximated via duration) | IRLTLT01ILM156N | Yes, but approximated — see Option A above |
| 8b | Israeli govt bonds (CPI-linked) | FRED (8a's method + CPI series #6) | IRLTLT01ILM156N + ISRCPIALLMINMEI | Yes, but approximated |
| 9 | Foreign bonds | Yahoo Finance | AGG or IEF | Yes |
| 10 | Cash / deposits | Reuses #7 | IR3TIB01ILM156N | Yes |

---

## Practical notes for when we actually write `data_loader.py`

1. **Two different libraries needed:** `yfinance` for everything from Yahoo Finance (items 1-5, 9), and `pandas_datareader` (or `fredapi`) for everything from FRED (items 6, 7, 8).
2. **Frequency alignment:** Yahoo Finance data can be pulled directly at monthly intervals; FRED series are often already monthly, but we should double check each one's native frequency and resample to month-end if needed, so every series lines up on the same 36 monthly dates before we build the r-table.
3. **Use "adjusted close," not plain "close," for anything from Yahoo Finance.** Adjusted close already factors in dividends/distributions, which is exactly the "total return" idea we discussed when explaining how r is calculated — this saves us from having to manually add dividends back in.
4. **Date range:** since the paper uses T = 36 months, we'll pull at least 36-40 months of history for every series (a little extra buffer helps handle any missing-data edges at the start/end).
5. **Document every approximation directly in the code** (a comment at the top of whichever function builds the bond return series, explicitly saying "this is a duration-based approximation from yield data, not an observed bond price series") — this keeps us honest and makes the substitution easy to explain later.

This file, combined with Reproduction_Plan.md's Section 9 (which already flagged that public proxies would be needed) and Master_Implementation_Plan.md's `data_loader.py` description, is now specific enough to actually start writing the data-fetching code.
