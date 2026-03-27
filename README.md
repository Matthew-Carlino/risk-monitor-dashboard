# Risk Monitor Dashboard

A real-time portfolio risk monitoring dashboard for quantitative traders and risk managers. Built with Streamlit and Python, this tool provides institutional-grade risk analytics for multi-asset trading desks.

## Features

### Core Risk Metrics
- **Value at Risk (VaR)**: Parametric, Historical Simulation, and Cornish-Fisher variants
- **Conditional VaR (CVaR/Expected Shortfall)**: Tail risk measurement
- **Component VaR**: Per-asset risk contribution with marginal and incremental VaR
- **Maximum Drawdown**: Peak-to-trough analysis with duration tracking
- **Correlation Regime Detection**: Identify risk-on/off market regimes in real-time

### Portfolio Analytics
- **P&L Attribution**: Daily P&L decomposition by source (price moves, rebalancing, dividends)
- **Sector Attribution**: Understand contribution to P&L by sector exposure
- **Factor Attribution**: Regression-based decomposition against common factors
- **Rolling Performance**: Sharpe ratio, volatility, and correlation evolution

### Position Management
- **Concentration Analysis**: Herfindahl-Hirschman Index (HHI) and exposure treemaps
- **Leverage Tracking**: Real-time gross, net, and notional exposure
- **Sector Exposure**: Aggregate and individual position exposure
- **Correlation Heatmaps**: Intra-portfolio correlation matrices with dynamic thresholds

### Alerts & Monitoring
- **Configurable Thresholds**: Set custom breach points for all risk metrics
- **Real-time Alerts**: VaR breaches, drawdown warnings, concentration limits, correlation spikes
- **Alert History**: Track and review past alerts with timestamps
- **Severity Levels**: Color-coded alerts (INFO, WARNING, CRITICAL)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/risk-monitor-dashboard.git
cd risk-monitor-dashboard

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
# Run the dashboard
streamlit run app.py

# Dashboard will open at http://localhost:8501
```

## Project Structure

```
risk-monitor-dashboard/
├── README.md                      # This file
├── requirements.txt               # Project dependencies
├── Makefile                       # Development commands
├── .gitignore                     # Git exclusions
├── app.py                         # Main Streamlit dashboard
├── src/
│   ├── __init__.py
│   ├── risk_metrics.py            # Core risk calculations
│   ├── pnl_attribution.py         # P&L decomposition
│   ├── portfolio.py               # Portfolio class
│   └── alerts.py                  # Alert system
├── scripts/
│   └── generate_demo_data.py      # Demo data generation
└── tests/
    └── test_risk_metrics.py       # Unit tests
```

## Documentation

### Risk Metrics

#### Value at Risk (VaR)
Measures the maximum potential loss at a given confidence level over a specific horizon.

**References:**
- Jorion, P. (2007). *Value at Risk: The New Benchmark for Managing Financial Risk*
- Hull, J. (2018). *Risk Management and Financial Institutions*

#### Conditional VaR (CVaR) / Expected Shortfall
The expected loss exceeding VaR. Better captures tail risk than VaR alone.

#### Component VaR
Decomposes total portfolio VaR into per-asset contributions using marginal VaR.

#### Correlation Regime Detection
Identifies market regimes by analyzing rolling correlation structure.

### P&L Attribution

Daily P&L decomposition across price impact, sector drift, and factor exposure.

## Testing

```bash
pytest tests/ -v
```

## License

MIT License

## Author

Matthew Carlino
Quantitative Trader & Risk Manager
