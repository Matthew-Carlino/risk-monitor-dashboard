"""Main Streamlit dashboard for portfolio risk monitoring."""

import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf

from src.portfolio import Portfolio, SECTOR_MAP
from src.risk_metrics import (
    parametric_var,
    historical_var,
    cornish_fisher_var,
    expected_shortfall,
    max_drawdown,
    herfindahl_index,
    correlation_regime_detector,
    component_var,
)
from src.pnl_attribution import (
    rolling_sharpe,
    rolling_volatility,
    cumulative_returns,
    calmar_ratio,
)
from src.alerts import AlertEngine, Severity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Risk Monitor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS customization
st.markdown(
    """
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .critical {
        color: #d73d3d;
        font-weight: bold;
    }
    .warning {
        color: #ff9500;
        font-weight: bold;
    }
    .info {
        color: #0068c9;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_historical_data(tickers: list, lookback: int = 252) -> pd.DataFrame:
    """Load historical data for given tickers."""
    end = datetime.now()
    start = end - timedelta(days=lookback)

    try:
        data = yf.download(tickers, start=start, end=end, progress=False)["Adj Close"]
        if isinstance(data, pd.Series):
            data = data.to_frame()
        return data.dropna()
    except Exception as e:
        logger.error(f"Error downloading data: {e}")
        return pd.DataFrame()


def calculate_returns(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily returns from price data."""
    return data.pct_change().dropna()


def render_overview_tab(portfolio: Portfolio, returns_df: pd.DataFrame):
    """Render overview tab with P&L and key metrics."""
    st.subheader("Portfolio Overview")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Net Value",
            f"${portfolio.net_value:,.0f}",
            delta=f"Gross: ${portfolio.gross_value:,.0f}",
        )

    with col2:
        st.metric(
            "Gross Leverage",
            f"{portfolio.gross_leverage:.2f}x",
            delta=f"Net: {portfolio.net_value/portfolio.net_value if portfolio.net_value else 0:.2f}x",
        )

    with col3:
        n_positions = len(portfolio.positions)
        st.metric("Positions", n_positions)

    with col4:
        hhi = herfindahl_index(np.array(list(portfolio.weights.values())))
        st.metric("HHI", f"{hhi:.4f}", delta="Concentration")

    st.divider()

    # Equity curve
    if len(returns_df) > 0:
        port_returns = returns_df.mean(axis=1)
        equity_curve = (1 + port_returns).cumprod() * 100

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=equity_curve.index, y=equity_curve.values, mode="lines", name="Equity Curve")
        )
        fig.update_layout(
            title="Equity Curve (Last Year)",
            xaxis_title="Date",
            yaxis_title="Value ($)",
            hovermode="x unified",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Drawdown chart
        dd, duration = max_drawdown(equity_curve.values)
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Max Drawdown", f"{dd:.2%}", delta=f"Duration: {duration} days")

        with col2:
            port_sharpe = rolling_sharpe(port_returns).iloc[-1]
            st.metric("Rolling Sharpe (1Q)", f"{port_sharpe:.2f}")


def render_risk_tab(portfolio: Portfolio, returns_df: pd.DataFrame, alert_engine: AlertEngine):
    """Render risk analysis tab."""
    st.subheader("Risk Analysis")

    if len(returns_df) == 0:
        st.warning("Insufficient data for risk analysis")
        return

    # VaR calculations
    col1, col2, col3 = st.columns(3)

    # Estimate portfolio returns for VaR
    portfolio_returns = returns_df.mean(axis=1)

    with col1:
        var_param = parametric_var(portfolio_returns, confidence=0.99)
        st.metric("Parametric VaR (99%)", f"{var_param:.2%}")

    with col2:
        var_hist = historical_var(portfolio_returns, confidence=0.99)
        st.metric("Historical VaR (99%)", f"{var_hist:.2%}")

    with col3:
        var_cf = cornish_fisher_var(portfolio_returns, confidence=0.99)
        st.metric("Cornish-Fisher VaR", f"{var_cf:.2%}")

    st.divider()

    # CVaR and regime detection
    col1, col2 = st.columns(2)

    with col1:
        cvar = expected_shortfall(portfolio_returns, confidence=0.99)
        st.metric("Conditional VaR (CVaR)", f"{cvar:.2%}", delta="Tail Risk")

    with col2:
        regime_info = correlation_regime_detector(returns_df, lookback=60)
        regime = regime_info["regime"].upper()
        corr = regime_info["current_avg_corr"]
        color = "🔴" if regime == "RISK-OFF" else "🟢"
        st.metric(f"Market Regime {color}", regime, delta=f"Corr: {corr:.3f}")

    st.divider()

    # Correlation heatmap
    st.write("**Correlation Matrix (Last 60 days)**")
    corr_matrix = returns_df.iloc[-60:].corr()
    fig = go.Figure(
        data=go.Heatmap(z=corr_matrix.values, x=corr_matrix.columns, y=corr_matrix.index, colorscale="RdBu")
    )
    fig.update_layout(height=500, width=700)
    st.plotly_chart(fig, use_container_width=True)

    # Component VaR
    st.write("**Component VaR Contribution**")
    try:
        weights = np.array(list(portfolio.weights.values()))
        comp_var = component_var(weights, returns_df)
        fig = px.bar(
            x=comp_var.values,
            y=comp_var.index,
            orientation="h",
            labels={"x": "VaR Contribution", "y": "Asset"},
            title="Per-Asset VaR Contribution",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error calculating component VaR: {e}")


def render_pnl_tab(returns_df: pd.DataFrame):
    """Render P&L attribution tab."""
    st.subheader("P&L Attribution")

    if len(returns_df) == 0:
        st.warning("Insufficient data")
        return

    # Rolling Sharpe
    col1, col2, col3 = st.columns(3)

    portfolio_returns = returns_df.mean(axis=1)

    with col1:
        sharpe = rolling_sharpe(portfolio_returns).iloc[-1]
        st.metric("Rolling Sharpe (1Q)", f"{sharpe:.2f}")

    with col2:
        vol = rolling_volatility(portfolio_returns).iloc[-1]
        st.metric("Rolling Volatility", f"{vol:.2%}")

    with col3:
        calmar = calmar_ratio(portfolio_returns)
        st.metric("Calmar Ratio", f"{calmar:.2f}")

    st.divider()

    # Rolling metrics
    col1, col2 = st.columns(2)

    with col1:
        sharpe_rolling = rolling_sharpe(portfolio_returns)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=sharpe_rolling.index, y=sharpe_rolling.values, mode="lines", name="Sharpe Ratio")
        )
        fig.update_layout(title="Rolling Sharpe Ratio (1Q)", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        vol_rolling = rolling_volatility(portfolio_returns)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=vol_rolling.index, y=vol_rolling.values, mode="lines", name="Volatility", line=dict(color="red"))
        )
        fig.update_layout(title="Rolling Volatility (1Q)", height=400, yaxis_title="Annualized Volatility")
        st.plotly_chart(fig, use_container_width=True)


def render_concentration_tab(portfolio: Portfolio):
    """Render concentration analysis tab."""
    st.subheader("Position Concentration")

    # HHI and top positions
    col1, col2 = st.columns(2)

    conc = portfolio.concentration
    with col1:
        st.metric("Herfindahl Index", f"{conc['herfindahl_index']:.4f}")
        st.write("*0 = equal weight, 1 = single asset*")

    with col2:
        st.metric("Top 3 Concentration", f"{conc['top_3_concentration']:.2%}")

    st.divider()

    # Position treemap
    weights = portfolio.weights
    notional = portfolio.notional_values

    df_tree = pd.DataFrame(
        [
            {
                "Ticker": ticker,
                "Weight": abs(w),
                "Value": abs(notional.get(ticker, 0)),
                "Sector": SECTOR_MAP.get(ticker, "Other"),
            }
            for ticker, w in weights.items()
        ]
    )

    fig = px.treemap(
        df_tree,
        labels=df_tree["Ticker"],
        parents=[None] * len(df_tree),
        values="Value",
        color="Weight",
        color_continuous_scale="RdYlGn_r",
        title="Position Treemap",
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Sector breakdown
    st.write("**Sector Exposure**")
    sector_exp = portfolio.sector_exposure
    df_sector = pd.DataFrame(
        [{"Sector": s, "Exposure": v} for s, v in sector_exp.items()]
    ).sort_values("Exposure", ascending=False)

    fig = px.bar(
        df_sector,
        x="Sector",
        y="Exposure",
        title="Sector Exposure Breakdown",
        color="Exposure",
        color_continuous_scale="Blues",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Position table
    st.write("**Position Details**")
    pos_df = pd.DataFrame(
        [
            {
                "Ticker": ticker,
                "Quantity": pos,
                "Price": portfolio.prices.get(ticker, 0),
                "Value": notional.get(ticker, 0),
                "Weight": f"{weights.get(ticker, 0):.2%}",
                "Sector": SECTOR_MAP.get(ticker, "Other"),
            }
            for ticker, pos in portfolio.positions.items()
        ]
    ).sort_values("Value", ascending=False, key=abs)

    st.dataframe(pos_df, use_container_width=True)


def render_alerts_tab(alert_engine: AlertEngine):
    """Render alerts monitoring tab."""
    st.subheader("Risk Alerts")

    # Alert summary
    col1, col2, col3, col4 = st.columns(4)

    severity_counts = alert_engine.severity_count()

    with col1:
        st.metric("Active Alerts", len(alert_engine.get_active_alerts()))

    with col2:
        st.metric(
            "🔴 Critical",
            severity_counts.get("CRITICAL", 0),
        )

    with col3:
        st.metric(
            "🟠 Warning",
            severity_counts.get("WARNING", 0),
        )

    with col4:
        st.metric(
            "ℹ️ Info",
            severity_counts.get("INFO", 0),
        )

    st.divider()

    # Active alerts
    active = alert_engine.get_active_alerts()
    if active:
        st.write("**Active Alerts**")
        for alert in sorted(active, key=lambda a: a.severity.value):
            emoji = (
                "🔴"
                if alert.severity == Severity.CRITICAL
                else "🟠"
                if alert.severity == Severity.WARNING
                else "ℹ️"
            )
            st.warning(f"{emoji} [{alert.metric}] {alert.message}")
    else:
        st.success("✅ No active alerts")

    st.divider()

    # Alert history
    st.write("**Alert History (Last 50)**")
    history = alert_engine.get_alert_history(limit=50)
    if history:
        df_history = pd.DataFrame(
            [
                {
                    "Time": a.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Metric": a.metric,
                    "Value": f"{a.current_value:.4f}",
                    "Threshold": f"{a.threshold:.4f}",
                    "Severity": a.severity.value,
                    "Message": a.message,
                }
                for a in history
            ]
        )
        st.dataframe(df_history, use_container_width=True)


def main():
    """Main app."""
    st.title("📊 Risk Monitor Dashboard")
    st.markdown(
        "Real-time portfolio risk monitoring for institutional trading desks"
    )

    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")

        # Portfolio selection
        use_demo = st.checkbox("Use Demo Portfolio", value=True)

        if use_demo:
            portfolio = Portfolio.from_demo()
        else:
            st.info("Custom portfolio loading not yet implemented")
            portfolio = Portfolio.from_demo()

        st.divider()

        # Alert thresholds
        st.subheader("Alert Thresholds")

        alert_engine = AlertEngine()

        var_limit = st.slider(
            "VaR 99% Limit",
            min_value=0.01,
            max_value=0.20,
            value=0.05,
            step=0.01,
            format="%.2%",
        )
        alert_engine.set_threshold("var_99", var_limit)

        dd_limit = st.slider(
            "Max Drawdown Limit",
            min_value=0.05,
            max_value=0.50,
            value=0.10,
            step=0.05,
            format="%.2%",
        )
        alert_engine.set_threshold("max_drawdown", dd_limit)

        hhi_limit = st.slider(
            "HHI Concentration Limit",
            min_value=0.10,
            max_value=0.50,
            value=0.20,
            step=0.05,
            format="%.3f",
        )
        alert_engine.set_threshold("herfindahl_index", hhi_limit)

        corr_limit = st.slider(
            "Correlation Spike Threshold",
            min_value=0.50,
            max_value=0.95,
            value=0.75,
            step=0.05,
            format="%.2f",
        )
        alert_engine.set_threshold("correlation_threshold", corr_limit)

        st.divider()
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    # Load data
    tickers = list(portfolio.positions.keys())
    returns_df = calculate_returns(load_historical_data(tickers))

    # Check alerts
    if len(returns_df) > 0:
        portfolio_returns = returns_df.mean(axis=1)
        var_val = parametric_var(portfolio_returns, confidence=0.99)
        equity_curve = (1 + portfolio_returns).cumprod() * 100
        dd_val, _ = max_drawdown(equity_curve.values)

        var_alert = alert_engine.check_var_breach(var_val, var_limit)
        if var_alert:
            alert_engine.add_alert(var_alert)

        dd_alert = alert_engine.check_drawdown_breach(dd_val, dd_limit)
        if dd_alert:
            alert_engine.add_alert(dd_alert)

        conc = portfolio.concentration
        hhi_alert = alert_engine.check_concentration(conc["herfindahl_index"], hhi_limit)
        if hhi_alert:
            alert_engine.add_alert(hhi_alert)

        regime = correlation_regime_detector(returns_df, lookback=60)
        corr_alert = alert_engine.check_correlation_spike(
            regime["current_avg_corr"], corr_limit
        )
        if corr_alert:
            alert_engine.add_alert(corr_alert)

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Overview", "Risk Analysis", "P&L Attribution", "Concentration", "Alerts"]
    )

    with tab1:
        render_overview_tab(portfolio, returns_df)

    with tab2:
        render_risk_tab(portfolio, returns_df, alert_engine)

    with tab3:
        render_pnl_tab(returns_df)

    with tab4:
        render_concentration_tab(portfolio)

    with tab5:
        render_alerts_tab(alert_engine)


if __name__ == "__main__":
    main()
