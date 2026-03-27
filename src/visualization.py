"""
Plotly visualization builders for the dashboard.

Creates publication-quality charts for displaying risk metrics, P&L attribution,
drawdowns, correlations, and concentration analysis.
"""

import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Optional

logger = logging.getLogger(__name__)

COLORS = {
    "positive": "#00d084",
    "negative": "#ff4757",
    "neutral": "#6c757d",
    "accent": "#0066cc",
}


def waterfall_chart(
    attribution_df: pd.DataFrame,
    title: str = "P&L Attribution Waterfall",
) -> go.Figure:
    """
    Create a waterfall chart showing P&L components (price, funding, fees).

    Args:
        attribution_df: DataFrame with columns [price_pnl, funding_pnl, fee_pnl, total_pnl].
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    # Aggregate by component
    price_total = attribution_df["price_pnl"].sum()
    funding_total = attribution_df["funding_pnl"].sum()
    fee_total = attribution_df["fee_pnl"].sum()
    total_pnl = price_total + funding_total + fee_total

    # Create waterfall data
    categories = ["Price P&L", "Funding P&L", "Fee P&L", "Total P&L"]
    values = [price_total, funding_total, fee_total, 0]
    measures = ["relative", "relative", "relative", "total"]

    fig = go.Figure(
        go.Waterfall(
            x=categories,
            y=values,
            measure=measures,
            connector={"line": {"color": COLORS["neutral"]}},
            increasing={"marker": {"color": COLORS["positive"]}},
            decreasing={"marker": {"color": COLORS["negative"]}},
            totals={"marker": {"color": COLORS["accent"]}},
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=450,
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="closest",
    )

    return fig


def drawdown_chart(
    equity_curve: np.ndarray,
    drawdown_series: np.ndarray,
    dates: Optional[pd.DatetimeIndex] = None,
) -> go.Figure:
    """
    Create a dual-axis chart showing equity curve and running drawdown.

    Args:
        equity_curve: Array of portfolio values over time.
        drawdown_series: Array of running drawdown (as decimals, e.g., -0.15 for -15%).
        dates: Optional DatetimeIndex for x-axis.

    Returns:
        Plotly Figure object.
    """
    if dates is None:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=len(equity_curve), freq="D")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=("Equity Curve", "Running Drawdown"),
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]],
    )

    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=equity_curve,
            mode="lines",
            name="Equity",
            line=dict(color=COLORS["accent"], width=2),
            fill="tozeroy",
            fillcolor="rgba(0, 102, 204, 0.1)",
        ),
        row=1, col=1,
    )

    # Drawdown
    drawdown_pct = drawdown_series * 100
    colors = [COLORS["negative"] if dd < -0.05 else COLORS["neutral"] for dd in drawdown_series]

    fig.add_trace(
        go.Bar(
            x=dates,
            y=drawdown_pct,
            marker=dict(color=colors),
            name="Drawdown %",
            showlegend=False,
        ),
        row=2, col=1,
    )

    fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    fig.update_layout(
        title="Equity Curve & Drawdown Analysis",
        template="plotly_white",
        height=600,
        hovermode="x unified",
        margin=dict(l=60, r=50, t=50, b=50),
    )

    return fig


def correlation_heatmap(
    corr_matrix: pd.DataFrame,
    title: str = "Asset Correlation Matrix",
) -> go.Figure:
    """
    Create a clustered correlation heatmap.

    Args:
        corr_matrix: Correlation matrix as DataFrame.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlation"),
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=600,
        width=700,
        margin=dict(l=100, r=50, t=50, b=100),
    )

    return fig


def exposure_treemap(
    positions_df: pd.DataFrame,
    title: str = "Portfolio Exposure Breakdown",
) -> go.Figure:
    """
    Create a treemap showing notional exposure by asset.

    Args:
        positions_df: DataFrame with columns [asset, notional].
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    # Separate long and short positions for visual distinction
    long_pos = positions_df[positions_df["notional"] > 0].copy()
    short_pos = positions_df[positions_df["notional"] < 0].copy()

    all_data = []

    if len(long_pos) > 0:
        all_data.append({
            "asset": "LONG",
            "notional": long_pos["notional"].sum(),
            "parent": "Portfolio",
            "type": "long",
        })
        for _, row in long_pos.iterrows():
            all_data.append({
                "asset": row["asset"],
                "notional": row["notional"],
                "parent": "LONG",
                "type": "long",
            })

    if len(short_pos) > 0:
        all_data.append({
            "asset": "SHORT",
            "notional": abs(short_pos["notional"].sum()),
            "parent": "Portfolio",
            "type": "short",
        })
        for _, row in short_pos.iterrows():
            all_data.append({
                "asset": row["asset"],
                "notional": abs(row["notional"]),
                "parent": "SHORT",
                "type": "short",
            })

    # Root
    all_data.insert(0, {
        "asset": "Portfolio",
        "notional": positions_df["notional"].abs().sum(),
        "parent": "",
        "type": "root",
    })

    data_df = pd.DataFrame(all_data)

    # Color by type
    colors = []
    for idx, row in data_df.iterrows():
        if row["type"] == "root":
            colors.append("rgba(200,200,200,0)")
        elif row["type"] == "long":
            colors.append(COLORS["positive"])
        else:  # short
            colors.append(COLORS["negative"])

    fig = go.Figure(
        go.Treemap(
            labels=data_df["asset"],
            parents=data_df["parent"],
            values=data_df["notional"].abs(),
            marker=dict(
                colors=colors,
                line=dict(color="white", width=2),
            ),
            textposition="middle center",
            hovertemplate="<b>%{label}</b><br>Notional: $%{value:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    return fig


def var_distribution(
    returns: np.ndarray,
    var_95: float,
    var_99: float,
    title: str = "Returns Distribution & VaR",
) -> go.Figure:
    """
    Create histogram of returns with VaR thresholds marked.

    Args:
        returns: Array of portfolio returns.
        var_95: 95% VaR value (as negative, e.g., -0.02).
        var_99: 99% VaR value (as negative, e.g., -0.04).
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    # Histogram
    fig.add_trace(
        go.Histogram(
            x=returns * 100,  # Convert to percentage
            nbinsx=50,
            name="Returns",
            marker=dict(color=COLORS["accent"], opacity=0.7),
        )
    )

    # VaR lines
    fig.add_vline(
        x=var_95 * 100,
        line_dash="dash",
        line_color=COLORS["negative"],
        annotation_text="95% VaR",
        annotation_position="top left",
    )

    fig.add_vline(
        x=var_99 * 100,
        line_dash="dash",
        line_color="darkred",
        annotation_text="99% VaR",
        annotation_position="top left",
    )

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=450,
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        hovermode="x",
        margin=dict(l=50, r=50, t=50, b=50),
    )

    return fig


def pnl_chart(
    pnl_series: pd.Series,
    title: str = "Cumulative P&L",
) -> go.Figure:
    """
    Create a cumulative P&L chart.

    Args:
        pnl_series: Series of daily P&L indexed by date.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    cumulative_pnl = pnl_series.cumsum()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=cumulative_pnl.index,
            y=cumulative_pnl.values,
            mode="lines",
            name="Cumulative P&L",
            line=dict(color=COLORS["accent"], width=2),
            fill="tozeroy",
            fillcolor="rgba(0, 102, 204, 0.1)",
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=450,
        xaxis_title="Date",
        yaxis_title="Cumulative P&L ($)",
        hovermode="x unified",
        margin=dict(l=50, r=50, t=50, b=50),
    )

    return fig
