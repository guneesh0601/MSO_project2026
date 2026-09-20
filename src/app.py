"""Opti-Money CRM dashboard.

Run with:  streamlit run src/app.py

A relationship manager enters a customer's profile in the sidebar, sees the
efficient frontier for it, picks a point, and explains the recommended
portfolio. All optimization happens in engine.py; this file is UI only.
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
import config
import engine
import frontier_builder
import ui_labels as L

st.set_page_config(page_title="Opti-Money CRM", layout="wide")

DEFAULT_RISK_LEVEL = "medium"
DEFAULT_BENCHMARK = "CPI"

# Allowed stops for the discrete sliders, as whole percentages (see config.py).
LIQUIDITY_STOPS = [round(v * 100) for v in config.LIQUIDITY_LEVELS]
CURRENCY_STOPS = [round(v * 100) for v in config.CURRENCY_LEVELS]

# Slider values are whole percentages; converted to fractions before solving.
DEFAULTS = {
    "risk_level": DEFAULT_RISK_LEVEL,
    "equity_cap": round(config.RISK_CATEGORY_EQUITY_CAP[DEFAULT_RISK_LEVEL] * 100),
    "benchmark": DEFAULT_BENCHMARK,
    "risk_measures": list(config.RISK_MEASURES),
    "liquidity_cap": round(config.LIQUIDITY_CAP_DEFAULT * 100),
    "currency_cap": round(config.CURRENCY_CAP_DEFAULT * 100),
    "gamma": config.GAMMA_TRACKING,
    "lambda_decay": config.LAMBDA_DECAY,
    "K": config.K_FRONTIER_POINTS,
}

for _key, _value in DEFAULTS.items():
    st.session_state.setdefault(_key, list(_value) if isinstance(_value, list) else _value)


def _apply_preset():
    """Selecting a risk level pre-fills the equity slider with that level's default."""
    level = st.session_state["risk_level"]
    st.session_state["equity_cap"] = round(config.RISK_CATEGORY_EQUITY_CAP[level] * 100)


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
def _solve(risk_measure, benchmark, equity_cap, liquidity_cap, currency_cap,
           gamma, lambda_decay, K):
    return engine.solve_frontier(
        risk_measure, benchmark, equity_cap, liquidity_cap, currency_cap,
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
                     format_func=L.RISK_LEVELS.get, on_change=_apply_preset,
                     help="One of the paper's five risk categories; the handle "
                          "snaps to the nearest one.")
    _tag("risk_level")

    st.slider("Maximum equity share (%)", 0, 100, key="equity_cap",
              help="Preset by the risk level; drag to fine-tune to any whole percentage.")
    _tag("equity_cap")

    st.selectbox("Benchmark", list(config.BENCHMARK_CHOICES), key="benchmark",
                 format_func=L.BENCHMARKS.get)
    _tag("benchmark")

    st.multiselect("Risk measures to compare", list(config.RISK_MEASURES),
                   key="risk_measures", format_func=L.RISK_MEASURES.get)
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

benchmark = st.session_state["benchmark"]
equity_cap = st.session_state["equity_cap"] / 100
liquidity_cap = st.session_state["liquidity_cap"] / 100
currency_cap = st.session_state["currency_cap"] / 100

frontiers = {}
try:
    for _measure in measures:
        frontiers[_measure] = _solve(
            _measure, benchmark, equity_cap, liquidity_cap, currency_cap,
            st.session_state["gamma"], st.session_state["lambda_decay"],
            st.session_state["K"],
        )
except engine.InfeasibleProfileError:
    st.error(
        "These limits leave room for only one portfolio (100% cash), so there is "
        "no frontier to show. Raise the equity, illiquid or foreign-currency limit."
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
    f"**Benchmark:** {L.BENCHMARKS[benchmark]} · "
    f"**Limits:** equity {equity_cap:.0%}, illiquid {liquidity_cap:.0%}, "
    f"foreign currency {currency_cap:.0%}"
)

# ---------------------------------------------------------------------------
# Customer choice: which risk measure, and where on the frontier
# ---------------------------------------------------------------------------
n_points = len(next(iter(ordered.values())))
choice_left, choice_right = st.columns([1, 2])
with choice_left:
    focus = st.radio("Risk measure for the recommendation", measures,
                     format_func=L.RISK_MEASURES.get)
with choice_right:
    point = st.slider("Risk appetite (1 = most conservative, highest number = most growth)",
                      1, n_points, value=(n_points + 1) // 2)

frontier = ordered[focus]
row = frontier.iloc[point - 1]
rounded = np.array(row["rounded_x"], dtype=float)

tab_options, tab_portfolio = st.tabs(["Risk & return options", "Recommended portfolio"])

# ---------------------------------------------------------------------------
# Tab 1: frontier + how the mix changes along it
# ---------------------------------------------------------------------------
with tab_options:
    st.subheader("Risk and return options")

    chart_df = pd.concat([
        pd.DataFrame({
            "measure": L.RISK_MEASURES[m],
            "position": range(1, len(f) + 1),
            "annual_risk": f["risk"].map(engine.annualized_risk) * 100,
            "annual_return": f["achieved_return"] * 100,
        })
        for m, f in ordered.items()
    ], ignore_index=True)
    picked_df = chart_df[(chart_df["measure"] == L.RISK_MEASURES[focus])
                         & (chart_df["position"] == point)]

    x_enc = alt.X("annual_risk:Q", title="Annualized risk (%)")
    y_enc = alt.Y("annual_return:Q", title="Expected annual return (%)")
    lines = alt.Chart(chart_df).mark_line(point=True).encode(
        x=x_enc, y=y_enc,
        color=alt.Color("measure:N", title="Risk measure"),
        tooltip=[
            alt.Tooltip("measure:N", title="Risk measure"),
            alt.Tooltip("position:Q", title="Position"),
            alt.Tooltip("annual_risk:Q", title="Risk (%)", format=".2f"),
            alt.Tooltip("annual_return:Q", title="Return (%)", format=".2f"),
        ],
    )
    marker = alt.Chart(picked_df).mark_point(
        shape="diamond", size=260, filled=True, color="crimson"
    ).encode(x=x_enc, y=y_enc)
    st.altair_chart((lines + marker).interactive())
    st.caption("The red diamond is the selected portfolio. Each risk measure defines "
               "'risk' differently, so compare the shapes rather than exact positions.")

    mix = pd.DataFrame(np.vstack(frontier["x"].values), columns=config.ASSET_NAMES)
    mix["annual_return"] = frontier["achieved_return"].values * 100
    mix_long = mix.melt(id_vars="annual_return", var_name="asset", value_name="weight")
    mix_long["asset"] = mix_long["asset"].map(L.ASSETS)
    mix_long["weight"] = mix_long["weight"] * 100
    st.subheader("How the mix changes as you take more risk")
    st.altair_chart(
        alt.Chart(mix_long).mark_area().encode(
            x=alt.X("annual_return:Q", title="Expected annual return (%)"),
            y=alt.Y("weight:Q", stack="zero", title="Weight (%)"),
            color=alt.Color("asset:N", title="Asset class"),
            tooltip=[alt.Tooltip("asset:N", title="Asset class"),
                     alt.Tooltip("weight:Q", title="Weight (%)", format=".1f")],
        )
    )

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
                color=alt.Color("asset:N", title="Asset class"),
                tooltip=[alt.Tooltip("asset:N", title="Asset class"),
                         alt.Tooltip("weight:Q", title="Weight (%)", format=".0f")],
            )
        )

    with right:
        m_return, m_risk = st.columns(2)
        m_return.metric("Expected annual return", f"{row['achieved_return']:.2%}")
        m_risk.metric("Annualized risk", f"{engine.annualized_risk(row['risk']):.2%}")
        st.dataframe(
            held.assign(weight=held["weight"].map(lambda w: f"{w:.0f}%"))
                .rename(columns={"asset": "Asset class", "weight": "Weight"}),
            hide_index=True,
        )
        st.caption("Weights are rounded to whole percentages.")

    st.subheader("Limits check")
    usage = engine.constraint_usage(rounded)
    usage_df = pd.DataFrame({
        "limit": ["Equity", "Foreign currency", "Illiquid assets"],
        "used": [usage["equity"] * 100, usage["foreign"] * 100, usage["illiquid"] * 100],
        "cap": [equity_cap * 100, currency_cap * 100, liquidity_cap * 100],
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

st.divider()
st.caption("Illustrative reproduction built on public proxy data (Yahoo Finance, FRED); "
           "not investment advice.")
