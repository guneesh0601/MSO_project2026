"""Central configuration for the Opti-Money reproduction.

Every fixed number/setting used anywhere in the pipeline lives here, so
nothing is duplicated or hidden inside individual modules.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
OUTPUTS_FRONTIERS_DIR = os.path.join(PROJECT_ROOT, "outputs", "frontiers")
OUTPUTS_PLOTS_DIR = os.path.join(PROJECT_ROOT, "outputs", "plots")

for _dir in (DATA_RAW_DIR, DATA_PROCESSED_DIR, OUTPUTS_FRONTIERS_DIR, OUTPUTS_PLOTS_DIR):
    os.makedirs(_dir, exist_ok=True)

# ---------------------------------------------------------------------------
# Historical window
# ---------------------------------------------------------------------------
T_MONTHS = 36          # number of historical months used to measure risk
LAMBDA_DECAY = 0.95    # exponential decay factor for recency weighting (paper's example value)

# ---------------------------------------------------------------------------
# Asset universe (our public-data proxy set, documented in Data_Sources_Plan.md)
# Each entry: internal_name -> (source, identifier, kind)
#   source: "yfinance" or "fred" or "derived"
#   kind:   "equity", "bond", "cash" (affects how returns are computed)
# ---------------------------------------------------------------------------
ASSETS = {
    "IL_Equity":        {"source": "yfinance", "id": "^TA125.TA",  "kind": "equity"},
    "US_Equity":        {"source": "yfinance", "id": "^GSPC",      "kind": "equity"},
    "EU_Equity":        {"source": "yfinance", "id": "^STOXX50E",  "kind": "equity"},
    "Foreign_Bond":     {"source": "yfinance", "id": "IEF",        "kind": "bond"},
    "IL_Bond_Unlinked": {"source": "derived",  "id": "IL_10Y_YIELD_DURATION", "kind": "bond"},
    "IL_Bond_Linked":   {"source": "derived",  "id": "IL_10Y_YIELD_DURATION_CPI", "kind": "bond"},
    "Cash":             {"source": "fred",     "id": "IR3TIB01ILM156N", "kind": "cash"},
}

ASSET_NAMES = list(ASSETS.keys())   # fixed order used everywhere (this defines "i" indexing)
N_ASSETS = len(ASSET_NAMES)

# Which assets are considered "illiquid" for the liquidity constraint
ILLIQUID_ASSETS = ["IL_Bond_Unlinked", "IL_Bond_Linked"]

# Which assets are denominated in foreign currency, for the currency constraint
FOREIGN_ASSETS = ["US_Equity", "EU_Equity", "Foreign_Bond"]

# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------
BENCHMARKS = {
    "CPI":       {"source": "fred",     "id": "ISRCPIALLMINMEI"},
    "USD":       {"source": "yfinance", "id": "USDILS=X"},
    "ILS_RATE":  {"source": "fred",     "id": "IR3TIB01ILM156N"},
}

# FRED series used to approximate Israeli government bond returns via duration
FRED_IL_10Y_YIELD = "IRLTLT01ILM156N"
FRED_IL_CPI = "ISRCPIALLMINMEI"
ASSUMED_BOND_DURATION_YEARS = 7.0   # approximate modified duration used for the yield->price conversion

# ---------------------------------------------------------------------------
# Risk model parameters
# ---------------------------------------------------------------------------
GAMMA_TRACKING = 0.05   # weight of the market-tracking penalty term (to be tuned/sensitivity-tested)
K_FRONTIER_POINTS = 10  # number of intermediate points between min-risk and max-return portfolios

# Reference "market portfolio" weights m_j used by the tracking term.
# Documented assumption: a simple, diversified, roughly value-weighted mix
# across our 7 proxy asset classes (must sum to 1).
MARKET_PORTFOLIO = {
    "IL_Equity":        0.15,
    "US_Equity":        0.15,
    "EU_Equity":        0.10,
    "Foreign_Bond":     0.15,
    "IL_Bond_Unlinked": 0.20,
    "IL_Bond_Linked":   0.15,
    "Cash":             0.10,
}
assert abs(sum(MARKET_PORTFOLIO.values()) - 1.0) < 1e-9, "MARKET_PORTFOLIO must sum to 1"

# ---------------------------------------------------------------------------
# Customer-profile parameters (documented assumptions -- paper gives no exact numbers)
# ---------------------------------------------------------------------------
# Risk category -> maximum allowed combined weight in equity-like assets (IL/US/EU equity)
RISK_CATEGORY_EQUITY_CAP = {
    "low":            0.20,
    "low_medium":     0.35,
    "medium":         0.55,
    "risk_oriented":  0.75,
    "high":           1.00,
}

LIQUIDITY_CAP_DEFAULT = 0.40   # max combined weight allowed in illiquid assets, by default
CURRENCY_CAP_DEFAULT = 1.00    # max combined weight allowed in foreign-currency assets, by default (no cap)
TURNOVER_CAP_DEFAULT = None    # None = no turnover constraint applied by default

RISK_MEASURES = ["symmetric", "asymmetric", "markowitz"]
BENCHMARK_CHOICES = ["CPI", "USD", "ILS_RATE"]
RISK_LEVEL_CHOICES = list(RISK_CATEGORY_EQUITY_CAP.keys())

# ---------------------------------------------------------------------------
# Data download window
# ---------------------------------------------------------------------------
HISTORY_YEARS_BUFFER = 4   # download a little more than T_MONTHS/12 years to allow for gaps
