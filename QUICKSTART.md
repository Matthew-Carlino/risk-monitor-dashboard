# Quick Start Guide

## Installation

```bash
# Clone or navigate to the project
cd risk-monitor-dashboard

# Install dependencies
pip install -r requirements.txt
```

## Running the Dashboard

```bash
# Launch the Streamlit app
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## First Run

The dashboard loads with sample data by default:
- 15-asset crypto portfolio (BTC, ETH, SOL, AVAX, LINK, etc.)
- 90 days of realistic correlated price history
- Perpetual futures funding rates
- Simulated P&L with realistic drawdown periods

**No configuration needed** — just run and explore.

## Features Overview

### Dashboard Tabs

1. **📈 Exposure Tab**
   - Total portfolio allocation by asset
   - Long/short breakdown
   - Exchange distribution
   - Gross exposure calculation

2. **💰 P&L Attribution Tab**
   - Waterfall chart: Price P&L + Funding P&L + Fee P&L
   - Position-level attribution details
   - Component contribution percentages

3. **📉 Drawdown Tab**
   - Equity curve with running drawdown overlay
   - Max drawdown and time underwater metrics
   - Recovery period analysis

4. **⚠️ VaR Analysis Tab**
   - 95% and 99% Value-at-Risk
   - Conditional VaR (Expected Shortfall)
   - Return distribution histogram
   - Per-asset component VaR

5. **🔗 Correlations Tab**
   - Full correlation matrix heatmap
   - Average/min/max correlation metrics
   - Highest correlation pairs

6. **📊 Concentration Tab**
   - HHI (Herfindahl-Hirschman Index)
   - Top-N asset exposure
   - Exchange breakdown
   - Margin utilization & liquidation distance

### Top-Level Metrics

- **Total NAV**: Current portfolio value
- **Daily P&L**: Today's profit/loss
- **Total Return**: Cumulative return %
- **Max Drawdown**: Worst peak-to-trough loss
- **Sharpe Ratio**: Risk-adjusted return metric

## Using Your Own Data

1. Prepare a CSV with columns:
   ```
   asset,position,entry_price,current_price,notional,exchange
   ```

2. In the sidebar, select "Upload CSV"

3. Upload your file

4. Dashboard auto-generates 90 days of price history and funding data

## Configuration Options (Sidebar)

- **Risk-Free Rate**: Adjust for Sharpe ratio calculation (default 0%)
- **VaR Confidence Levels**: Toggle 95% and/or 99% VaR
- **Margin Cushion**: Set warning threshold for margin usage

## Testing

Run the unit test suite:

```bash
pytest tests/ -v
```

This runs 18 tests covering all core risk metrics with known inputs and expected outputs.

## Extending the Dashboard

### Add a New Risk Metric

1. Implement calculation in `src/risk_metrics.py`
2. Add visualization in `src/visualization.py`
3. Integrate in appropriate tab in `app.py`

Example:
```python
# In src/risk_metrics.py
def compute_cvar(returns, confidence=0.95):
    """Compute Conditional Value-at-Risk."""
    var = np.percentile(returns, (1 - confidence) * 100)
    return returns[returns <= var].mean()

# In app.py
cvar = compute_cvar(daily_returns)
st.metric("CVaR", f"${cvar * equity_curve[-1]:,.0f}")
```

### Add a New Chart Type

1. Implement in `src/visualization.py` using Plotly
2. Call from appropriate tab in `app.py`
3. Use consistent color scheme

## Troubleshooting

**Streamlit not found?**
```bash
pip install streamlit
```

**Module import errors?**
```bash
# Make sure you're in the project root directory
cd /path/to/risk-monitor-dashboard
python -c "from src import risk_metrics; print('OK')"
```

**Tests failing?**
```bash
pytest tests/ -v --tb=short
```

## Performance Notes

- Dashboard recalculates all metrics on each interaction
- For large portfolios (1000+ positions), consider caching
- VaR calculations use 90-day history (adjust in `generate_price_history()`)
- Correlation matrices recompute on every run (could be optimized with @st.cache_data)

## Architecture

```
risk-monitor-dashboard/
├── app.py                    # Main Streamlit dashboard (594 lines)
├── src/
│   ├── risk_metrics.py       # Core calculations (296 lines)
│   ├── pnl_attribution.py    # P&L decomposition (239 lines)
│   ├── data_generator.py     # Sample data (289 lines)
│   └── visualization.py      # Plotly charts (378 lines)
├── tests/
│   └── test_risk_metrics.py  # Unit tests (310 lines)
└── sample_data/
    └── sample_positions.csv  # Example positions
```

All modules use:
- Full type hints
- Google-style docstrings
- PEP 8 style
- Comprehensive error handling

## Interview Ready

This project demonstrates:
- **Risk Management**: VaR, component VaR, concentration metrics
- **Data Science**: Statistical calculations, correlation analysis
- **Software Engineering**: Modular design, type hints, testing
- **UI/UX**: Professional Streamlit dashboard
- **Python Excellence**: ~2,100 lines of production code

Perfect for discussing at quant trading interviews (Two Sigma, Renaissance, Citadel, etc.)
