"""
Sample data generation for dashboard demonstrations.

Creates realistic synthetic portfolios, price histories, and funding rates for testing
and demo purposes without requiring external data feeds.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple

logger = logging.getLogger(__name__)


def generate_sample_portfolio(
    n_assets: int = 15,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a realistic multi-asset portfolio with crypto assets.

    Args:
        n_assets: Number of assets in portfolio (default 15).
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns:
            - asset: Asset ticker
            - position: Position size
            - entry_price: Entry price
            - current_price: Current market price
            - notional: Position value (position * current_price)
            - exchange: Trading exchange
    """
    np.random.seed(seed)

    assets = [
        ("BTC", 42500, 43200, "BINANCE"),
        ("ETH", 2200, 2250, "BINANCE"),
        ("SOL", 105, 108, "BINANCE"),
        ("AVAX", 78, 82, "BINANCE"),
        ("LINK", 29, 31, "BINANCE"),
        ("AAVE", 410, 425, "BINANCE"),
        ("ARB", 1.15, 1.22, "BINANCE"),
        ("OP", 2.80, 2.95, "BINANCE"),
        ("DYDX", 6.50, 6.85, "BINANCE"),
        ("FIL", 17.50, 18.30, "FILECOIN"),
        ("NEAR", 8.20, 8.75, "BINANCE"),
        ("APE", 8.50, 9.10, "BINANCE"),
        ("BLUR", 0.85, 0.92, "OPENSEA"),
        ("LDO", 4.20, 4.60, "BINANCE"),
        ("UNI", 14.50, 15.80, "BINANCE"),
    ]

    # Generate positions with realistic weight distribution (Pareto-like)
    pareto_weights = np.random.pareto(1.5, n_assets)
    pareto_weights = pareto_weights / pareto_weights.sum()

    # Make some positions long, some short (hedges)
    position_signs = np.random.choice([-1, 1], n_assets, p=[0.15, 0.85])

    portfolio_data = []
    total_notional = 500_000  # $500K portfolio

    for i in range(n_assets):
        asset, entry_price, current_price, exchange = assets[i % len(assets)]
        notional = total_notional * pareto_weights[i]
        position = (notional / current_price) * position_signs[i]

        portfolio_data.append(
            {
                "asset": asset,
                "position": position,
                "entry_price": entry_price,
                "current_price": current_price,
                "notional": notional,
                "exchange": exchange,
            }
        )

    return pd.DataFrame(portfolio_data)


def generate_price_history(
    n_days: int = 90,
    n_assets: int = 15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Generate correlated price history using Cholesky decomposition.

    Creates realistic asset return correlations based on empirical crypto patterns:
    - BTC is the market driver (high beta)
    - Large alts (ETH) correlated with BTC but less volatile
    - Small alts have higher idiosyncratic volatility

    Args:
        n_days: Number of days of history (default 90).
        n_assets: Number of assets (default 15).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (price_history_df, returns_array).
            - price_history_df: DataFrame indexed by date, columns are assets.
            - returns_array: 2D array of daily returns (n_days, n_assets).
    """
    np.random.seed(seed)

    assets = [
        "BTC", "ETH", "SOL", "AVAX", "LINK",
        "AAVE", "ARB", "OP", "DYDX", "FIL",
        "NEAR", "APE", "BLUR", "LDO", "UNI",
    ][:n_assets]

    # Create correlation matrix with BTC as driver
    corr_matrix = np.eye(n_assets)
    btc_idx = 0

    # BTC correlations
    btc_correlations = [
        1.0,    # BTC-BTC
        0.75,   # ETH
        0.68,   # SOL
        0.65,   # AVAX
        0.60,   # LINK
        0.58,   # AAVE
        0.55,   # ARB
        0.55,   # OP
        0.52,   # DYDX
        0.50,   # FIL
        0.52,   # NEAR
        0.48,   # APE
        0.45,   # BLUR
        0.58,   # LDO
        0.55,   # UNI
    ][:n_assets]

    for i in range(n_assets):
        for j in range(n_assets):
            if i != j:
                # Correlation based on BTC, with some cross-correlations
                corr = btc_correlations[i] * btc_correlations[j] * 0.8 + 0.2 * (1 - abs(i - j) / n_assets)
                corr_matrix[i, j] = min(max(corr, -0.5), 0.95)

    # Make symmetric
    corr_matrix = (corr_matrix + corr_matrix.T) / 2
    np.fill_diagonal(corr_matrix, 1.0)

    # Cholesky decomposition
    try:
        L = np.linalg.cholesky(corr_matrix)
    except np.linalg.LinAlgError:
        # If not positive definite, use eigenvalue adjustment
        eigenvalues, eigenvectors = np.linalg.eigh(corr_matrix)
        eigenvalues[eigenvalues < 1e-6] = 1e-6
        corr_matrix = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
        L = np.linalg.cholesky(corr_matrix)

    # Asset volatilities (annualized)
    volatilities = np.array([0.65, 0.70, 0.85, 0.80, 0.75, 0.72, 0.95, 0.92, 0.88, 0.78, 0.82, 0.88, 0.95, 0.70, 0.75])[:n_assets]

    # Generate correlated returns
    Z = np.random.standard_normal((n_days, n_assets))
    returns = (Z @ L.T) * (volatilities / 252) + 0.0005  # Small drift

    # Generate prices from returns
    start_prices = np.array([43200, 2250, 108, 82, 31, 425, 1.22, 2.95, 6.85, 18.30, 8.75, 9.10, 0.92, 4.60, 15.80])[:n_assets]

    prices = np.zeros((n_days, n_assets))
    prices[0, :] = start_prices

    for t in range(1, n_days):
        prices[t, :] = prices[t - 1, :] * np.exp(returns[t, :])

    # Create DataFrame
    dates = pd.date_range(end=datetime.now().date(), periods=n_days, freq="D")
    price_df = pd.DataFrame(prices, index=dates, columns=assets)

    return price_df, returns


def generate_funding_rates(
    n_days: int = 90,
    n_assets: int = 15,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate simulated perpetual futures funding rates.

    Funding rates follow market conditions: positive when market is bullish (longs pay shorts),
    negative when bearish (shorts pay longs).

    Args:
        n_days: Number of days of funding history.
        n_assets: Number of assets.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame of cumulative funding rates indexed by date, columns by asset.
    """
    np.random.seed(seed)

    assets = [
        "BTC", "ETH", "SOL", "AVAX", "LINK",
        "AAVE", "ARB", "OP", "DYDX", "FIL",
        "NEAR", "APE", "BLUR", "LDO", "UNI",
    ][:n_assets]

    # Base funding rates (typical 0.01% to 0.1% per 8h)
    base_rates = np.random.uniform(0.0001, 0.0008, n_assets)

    # Simulate funding over time with trending component
    funding = np.zeros((n_days, n_assets))

    for i in range(n_assets):
        trend = np.random.uniform(-0.0002, 0.0002)
        noise = np.random.normal(0, 0.00015, n_days)
        funding[:, i] = base_rates[i] + trend * np.arange(n_days) / n_days + np.cumsum(noise)

    # Cumulative funding (total paid over period)
    cumulative_funding = np.cumsum(funding, axis=0)

    dates = pd.date_range(end=datetime.now().date(), periods=n_days, freq="D")
    funding_df = pd.DataFrame(cumulative_funding, index=dates, columns=assets)

    return funding_df


def generate_trade_fees(
    n_assets: int = 15,
    seed: int = 42,
) -> pd.Series:
    """
    Generate realistic trading fees by asset.

    Args:
        n_assets: Number of assets.
        seed: Random seed.

    Returns:
        Series of fees (as % of notional) indexed by asset.
    """
    np.random.seed(seed)

    assets = [
        "BTC", "ETH", "SOL", "AVAX", "LINK",
        "AAVE", "ARB", "OP", "DYDX", "FIL",
        "NEAR", "APE", "BLUR", "LDO", "UNI",
    ][:n_assets]

    # Fees vary by liquidity: BTC/ETH lower, smaller alts higher
    # Typical maker fee 0.01-0.05%, taker fee 0.05-0.10%
    fees = np.array([0.0003, 0.0004, 0.0006, 0.0006, 0.0005, 0.0005, 0.0007, 0.0007, 0.0008, 0.0006, 0.0007, 0.0008, 0.0009, 0.0005, 0.0006])[:n_assets]

    return pd.Series(fees, index=assets)


def generate_equity_curve(
    n_days: int = 90,
    initial_balance: float = 500_000,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate a sample equity curve (portfolio value over time).

    Args:
        n_days: Number of days.
        initial_balance: Starting portfolio value.
        seed: Random seed.

    Returns:
        Array of portfolio values over time.
    """
    np.random.seed(seed)

    # Generate daily returns with trending up but with drawdown periods
    base_return = 0.0008
    volatility = 0.015
    returns = np.random.normal(base_return, volatility, n_days)

    # Add a drawdown period (days 40-50) and recovery
    returns[40:50] -= 0.025
    returns[50:60] += 0.015

    equity = np.cumprod(1 + returns) * initial_balance

    return equity
