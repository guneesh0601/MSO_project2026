"""Opti-Money CRM dashboard.

Run with:  streamlit run src/app.py

A relationship manager enters a customer's profile in the sidebar, sees the
frontier portfolios for it, and explains the recommended portfolio. All optimization happens in engine.py; this file is UI only.
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

# Streamlit re-runs this script on every interaction but keeps imported modules in
# memory, so an edit to engine.py, ui_labels.py, config.py ... was not picked up until
# the server was restarted (typically an AttributeError on a new name). Drop this
# project's own modules so every run imports them fresh; third-party modules stay.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
for _name, _module in list(sys.modules.items()):
    _path = getattr(_module, "__file__", None)
    if (_path and _name != "__main__" and os.path.abspath(_path) != os.path.abspath(__file__)
            and os.path.dirname(os.path.abspath(_path)) == _SRC_DIR):
        del sys.modules[_name]

import config
import engine
import frontier_builder
import ui_labels as L

st.set_page_config(page_title="Opti-Money CRM", layout="wide")

DEFAULT_RISK_LEVEL = "medium"
DEFAULT_BENCHMARK = "CPI"

# Altair cuts legend/axis labels at ~160-180 px by default, which truncates the
# longer asset-class and risk-measure names; give them room.
LABEL_LIMIT_PX = 320

# Allowed stops for the discrete sliders, as whole percentages (see config.py).
LIQUIDITY_STOPS = [round(v * 100) for v in config.LIQUIDITY_LEVELS]
CURRENCY_STOPS = [round(v * 100) for v in config.CURRENCY_LEVELS]

# Slider values are whole percentages; converted to fractions before solving.
DEFAULTS = {
    "risk_level": DEFAULT_RISK_LEVEL,
    "benchmarks": [DEFAULT_BENCHMARK],
    "risk_measures": list(config.RISK_MEASURES),
    "liquidity_cap": round(config.LIQUIDITY_CAP_DEFAULT * 100),
    "currency_cap": round(config.CURRENCY_CAP_DEFAULT * 100),
    "gamma": config.GAMMA_TRACKING,
    "lambda_decay": config.LAMBDA_DECAY,
    "K": config.K_FRONTIER_POINTS,
}

# One weight (% of the benchmark blend) per benchmark; only used when 2+ are selected.
DEFAULTS.update({f"bw_{name}": (100 if name == DEFAULT_BENCHMARK else 0)
                 for name in config.BENCHMARK_CHOICES})

for _key, _value in DEFAULTS.items():
    st.session_state.setdefault(_key, list(_value) if isinstance(_value, list) else _value)


def _equalize_benchmark_weights():
    """Changing the benchmark selection resets the weights to an even split
    (50/50, 34/33/33, ...), which the CRM can then edit."""
    chosen = st.session_state["benchmarks"]
    for name in config.BENCHMARK_CHOICES:
        st.session_state[f"bw_{name}"] = 0
    if chosen:
        base, extra = divmod(100, len(chosen))
        for i, name in enumerate(chosen):
            st.session_state[f"bw_{name}"] = base + (1 if i < extra else 0)


def _benchmark_label(benchmark) -> str:
    """'Israeli CPI (inflation)' for one benchmark, '60% CPI + 40% USD/ILS' for a blend."""
    if isinstance(benchmark, str):
        return L.BENCHMARKS[benchmark]
    return " + ".join(f"{round(w * 100)}% {L.BENCHMARKS_SHORT[n]}" for n, w in benchmark.items())


def _benchmark_short(benchmark) -> str:
    """'CPI' for one benchmark, '60% CPI + 40% USD/ILS' for a blend (for chart legends)."""
    if isinstance(benchmark, str):
        return L.BENCHMARKS_SHORT[benchmark]
    return _benchmark_label(benchmark)


def _point_label(point: str) -> str:
    """Frontier point names in the paper's terms: Step 1, k = 1 ... K, Step 2."""
    if point == "min_risk":
        return "Step 1: minimum risk"
    if point == "max_return":
        return "Step 2: maximum return"
    return point.replace("k=", "k = ")


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
def _solve(risk_measure, benchmark_key, liquidity_cap, currency_cap,
           gamma, lambda_decay, K):
    # benchmark_key is a name, or a hashable tuple of (name, weight) pairs for a blend.
    benchmark = benchmark_key if isinstance(benchmark_key, str) else dict(benchmark_key)
    return engine.solve_frontier(
        risk_measure, benchmark, None, liquidity_cap, currency_cap,
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
                     format_func=L.RISK_LEVELS.get,
                     help="One of the paper's five risk categories; the handle snaps to the "
                          "nearest one. It does not restrict the portfolio: it picks which "
                          "point on the customer's frontier is recommended (Low = minimum "
                          "risk ... High = maximum return).")
    _tag("risk_level")

    st.multiselect("Benchmark(s)", list(config.BENCHMARK_CHOICES), key="benchmarks",
                   format_func=L.BENCHMARKS.get, on_change=_equalize_benchmark_weights,
                   help="Pick one, or several to track a weighted blend, as in the paper.")
    _tag("benchmarks")
    _chosen = st.session_state["benchmarks"]
    if len(_chosen) > 1:
        for _name in _chosen:
            st.slider(f"Weight: {L.BENCHMARKS_SHORT[_name]} (%)", 0, 100, key=f"bw_{_name}")
        _weights_total = sum(st.session_state[f"bw_{n}"] for n in _chosen)
        st.caption(f"Weights total {_weights_total}%"
                   + ("" if _weights_total == 100 else " (must be 100%)"))

    st.multiselect("Risk measures to compare", list(config.RISK_MEASURES),
                   key="risk_measures", format_func=L.RISK_MEASURES.get,
                   help="Classical volatility (Markowitz) does not use the benchmark.")
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

chosen_benchmarks = st.session_state["benchmarks"]
if not chosen_benchmarks:
    st.info("Select at least one benchmark in the sidebar.")
    st.stop()

if len(chosen_benchmarks) == 1:
    benchmark = benchmark_key = chosen_benchmarks[0]
else:
    weights_pct = {n: st.session_state[f"bw_{n}"] for n in chosen_benchmarks}
    weights_total = sum(weights_pct.values())
    if weights_total != 100:
        st.error(f"Benchmark weights add up to {weights_total}%; they must total 100%.")
        st.stop()
    benchmark = {n: w / 100 for n, w in weights_pct.items() if w > 0}
    benchmark_key = tuple(sorted(benchmark.items()))

liquidity_cap = st.session_state["liquidity_cap"] / 100
currency_cap = st.session_state["currency_cap"] / 100

frontiers = {}
try:
    for _measure in measures:
        frontiers[_measure] = _solve(
            _measure, benchmark_key, liquidity_cap, currency_cap,
            st.session_state["gamma"], st.session_state["lambda_decay"],
            st.session_state["K"],
        )
except engine.InfeasibleProfileError:
    st.error(
        "These limits leave room for only one portfolio (100% cash), so there is "
        "no frontier to show. Raise the illiquid or foreign-currency limit."
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
    f"**Benchmark:** {_benchmark_label(benchmark)} · "
    f"**Limits:** illiquid {liquidity_cap:.0%}, foreign currency {currency_cap:.0%}"
)

# ---------------------------------------------------------------------------
# Recommendation: which risk measure, and the point the risk level picks on its frontier
# ---------------------------------------------------------------------------
n_points = len(next(iter(ordered.values())))
focus = st.radio("Risk measure for the recommendation", measures,
                 format_func=L.RISK_MEASURES.get, horizontal=True)
# 1-based position on the frontier: Low = Step 1 ... High = Step 2, evenly spaced between.
point = engine.frontier_position(st.session_state["risk_level"], n_points)

frontier = ordered[focus]
row = frontier.iloc[point - 1]
rounded = np.array(row["rounded_x"], dtype=float)

tab_options, tab_portfolio, tab_history, tab_compare = st.tabs([
    "Frontier portfolios", "Recommended portfolio",
    "History vs benchmark", "Compare with current portfolio",
])

# ---------------------------------------------------------------------------
# Tab 1: frontier + how the mix changes along it
# ---------------------------------------------------------------------------
with tab_options:
    st.subheader("Balanced efficient frontier: the K + 2 portfolios")

    table = pd.DataFrame({
        "Point": [_point_label(p) for p in frontier["point"]],
        "Recommended": ["✔" if i + 1 == point else "" for i in range(len(frontier))],
        "ExpRet (% per year)": (frontier["achieved_return"] * 100).round(2),
        "Risk, annualised (%)": (frontier["risk"].map(engine.annualized_risk) * 100).round(2),
    })
    weights = pd.DataFrame(
        np.vstack(frontier["rounded_x"].values) * 100,
        columns=[L.ASSETS_SHORT[a] for a in config.ASSET_NAMES],
    ).round(0).astype(int).astype(str) + "%"
    st.dataframe(pd.concat([table, weights], axis=1), hide_index=True)
    st.caption("Each row is one portfolio on the frontier of the selected risk measure, as in "
               "the paper (p. 49): Step 1 is the minimum-risk portfolio, k = 1 ... K are "
               "evenly spaced expected returns, and Step 2 is the maximum-return portfolio. "
               "Weights are rounded to whole percentages. ExpRet = sum(rho_i * x_i); risk is "
               "the measure's risk score annualised as sqrt(12 * score). The recommended "
               "portfolio is the point picked by the customer's risk level: Low = Step 1, "
               "High = Step 2, the other levels evenly spaced between.")

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
                color=alt.Color("asset:N", title="Asset class",
                            legend=alt.Legend(labelLimit=LABEL_LIMIT_PX)),
                tooltip=[alt.Tooltip("asset:N", title="Asset class"),
                         alt.Tooltip("weight:Q", title="Weight (%)", format=".0f")],
            )
        )

    with right:
        m_return, m_risk, m_equity = st.columns(3)
        m_return.metric("Expected annual return", f"{row['achieved_return']:.2%}")
        m_risk.metric("Annualized risk", f"{engine.annualized_risk(row['risk']):.2%}")
        m_equity.metric("Equity share", f"{engine.constraint_usage(rounded)['equity']:.0%}")
        st.dataframe(
            held.assign(weight=held["weight"].map(lambda w: f"{w:.0f}%"))
                .rename(columns={"asset": "Asset class", "weight": "Weight"}),
            hide_index=True,
        )
        st.caption("Weights are rounded to whole percentages.")

    st.subheader("Limits check")
    usage = engine.constraint_usage(rounded)
    usage_df = pd.DataFrame({
        "limit": ["Foreign currency", "Illiquid assets"],
        "used": [usage["foreign"] * 100, usage["illiquid"] * 100],
        "cap": [currency_cap * 100, liquidity_cap * 100],
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

# ---------------------------------------------------------------------------
# Tab 3: what this portfolio would have done, historically
# ---------------------------------------------------------------------------
with tab_history:
    st.subheader("History vs benchmark")
    history = engine.portfolio_history(rounded, benchmark)

    total_portfolio = history["Portfolio"].iloc[-1] / 100 - 1
    total_benchmark = history["Benchmark"].iloc[-1] / 100 - 1
    h_left, h_right = st.columns(2)
    h_left.metric("Portfolio return, total over window", f"{total_portfolio:+.1%}")
    h_right.metric("Benchmark return, total over window", f"{total_benchmark:+.1%}")

    portfolio_series = "Portfolio return"
    benchmark_series_name = f"Benchmark return ({_benchmark_short(benchmark)})"
    monthly = (engine.monthly_returns(rounded, benchmark) * 100).rename_axis("month")
    monthly = monthly.rename(columns={"Portfolio": portfolio_series,
                                      "Benchmark": benchmark_series_name})
    monthly_long = monthly.reset_index().melt(
        id_vars="month", var_name="series", value_name="return_pct")
    st.altair_chart(
        alt.Chart(monthly_long).mark_line(point=True).encode(
            x=alt.X("month:T", title="Month",
                    axis=alt.Axis(format="%b %Y", labelAngle=-45)),
            y=alt.Y("return_pct:Q", title="Monthly return (%)"),
            color=alt.Color("series:N", title=None,
                            legend=alt.Legend(orient="bottom", labelLimit=LABEL_LIMIT_PX)),
            tooltip=[alt.Tooltip("month:T", title="Month", format="%b %Y"),
                     alt.Tooltip("series:N", title="Series"),
                     alt.Tooltip("return_pct:Q", title="Return (%)", format=".2f")],
        )
    )
    st.caption("Month-by-month return of the recommended portfolio (PortfRet) and of the "
               "benchmark (BchRet): the two series the risk measures compare. The totals "
               "above compound them over the window. Historical and in-sample (the portfolio "
               "was chosen using this same period): not a forecast.")

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
                x=alt.X("asset:N", title=None, axis=alt.Axis(labelAngle=-35, labelLimit=LABEL_LIMIT_PX)),
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

st.divider()
st.caption("Illustrative reproduction built on public proxy data (Yahoo Finance, FRED); "
           "not investment advice.")
