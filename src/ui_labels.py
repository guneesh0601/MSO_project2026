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

# Short forms, used as column headers in the frontier table.
ASSETS_SHORT = {
    "IL_Equity":        "Israeli equities",
    "US_Equity":        "US equities",
    "EU_Equity":        "Euro equities",
    "Foreign_Bond":     "Foreign bonds",
    "IL_Bond_Unlinked": "IL bonds (unlinked)",
    "IL_Bond_Linked":   "IL bonds (CPI-linked)",
    "Cash":             "Cash",
}

BENCHMARKS = {
    "CPI":      "Israeli CPI (inflation)",
    "USD":      "USD/ILS exchange rate",
    "ILS_RATE": "Bank of Israel rate (3M interbank proxy)",
    "EUR":      "EUR/ILS exchange rate",
}

# Short forms, used to label a blend such as "60% CPI + 40% USD/ILS".
BENCHMARKS_SHORT = {
    "CPI":      "CPI",
    "USD":      "USD/ILS",
    "ILS_RATE": "BoI rate",
    "EUR":      "EUR/ILS",
}

RISK_LEVELS = {
    "low":           "Low",
    "low_medium":    "Low-medium",
    "medium":        "Medium",
    "risk_oriented": "Risk-oriented",
    "high":          "High",
}

# Named after the risk measures in the paper (p. 47): (1) Symmetric Risk,
# (2) Asymmetric Risk, (4) classical Markowitz risk V.
RISK_MEASURES = {
    "symmetric":  "Symmetric Risk (benchmark-relative)",
    "asymmetric": "Asymmetric Risk (downside vs benchmark)",
    "markowitz":  "Markowitz Risk V (portfolio variance)",
}
