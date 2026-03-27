"""P&L attribution and performance analysis.

Decomposes portfolio P&L into components: price impact, sector effects, and factor exposure.
Also calculates rolling Sharpe ratio and volatility metrics.
"""

import logging
from typing import Dict, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)


def daily_pnl(
    positions: Dict[str, float],
    prices_today: Dict[str, float],
    prices_yesterday: Dict[str, float],
) -> Dict[str, float]:
    """Calculate daily P&L by position.

    Args:
        positions: Dict of {ticker: quantity}.
        prices_today: Dict of {ticker: price} at end of today.
        prices_yesterday: Dict of {ticker: price} at end of yesterday.

    Returns:
        Dict of {ticker: pnl} for each position.

    Examples:
        >>> positions = {'AAPL': 100, 'MSFT': 50}
        >>> prices_today = {'AAPL': 150, 'MSFT': 200}
        >>> prices_yesterday = {'AAPL': 148, 'MSFT': 198}
        >>> pnl = daily_pnl(positions, prices_today, prices_yesterday)
        >>> print(pnl)  # AAPL: 200, MSFT: 100
    """
    pnl = {}
    for ticker, qty in positions.items():
        if ticker in prices_today and ticker in prices_yesterday:
            price_change = prices_today[ticker] - prices_yesterday[ticker]
            pnl[ticker] = qty * price_change
    return pnl


def sector_attribution(
    pnl: Dict[str, float],
    sector_map: Dict[str, str],
) -> pd.DataFrame:
    """Decompose P&L by sector.

    Args:
        pnl: Dict of {ticker: pnl}.
        sector_map: Dict of {ticker: sector}.

    Returns:
        DataFrame with sectors and cumulative P&L.

    Examples:
        >>> pnl = {'AAPL': 200, 'MSFT': 150, 'GLD': 50}
        >>> sectors = {'AAPL': 'Tech', 'MSFT': 'Tech', 'GLD': 'Commodities'}
        >>> result = sector_attribution(pnl, sectors)
        >>> print(result)
    """
    sector_pnl = {}
    for ticker, p in pnl.items():
        sector = sector_map.get(ticker, "Other")
        sector_pnl[sector] = sector_pnl.get(sector, 0) + p

    df = pd.DataFrame(
        list(sector_pnl.items()), columns=["Sector", "P&L"]
    ).sort_values("P&L", ascending=False)
    return df


def factor_attribution(
    returns: pd.Series,
    factor_returns: pd.DataFrame,
) -> Dict[str, float]:
    """Decompose returns via factor regression.

    Regresses asset returns against factor returns (e.g., market, size, value, momentum).
    Returns factor loadings (betas).

    Args:
        returns: Series of portfolio or asset returns.
        factor_returns: DataFrame of factor returns (aligned index).

    Returns:
        Dict of {factor_name: beta_loading}.

    Examples:
        >>> import numpy as np
        >>> returns = pd.Series(np.random.randn(252) * 0.01)
        >>> factors = pd.DataFrame({
        ...     'mkt': np.random.randn(252) * 0.01,
        ...     'smb': np.random.randn(252) * 0.005,
        ... })
        >>> factors.index = returns.index
        >>> attr = factor_attribution(returns, factors)
        >>> print(f"Market beta: {attr['mkt']:.3f}")
    """
    # Align indices
    common_idx = returns.index.intersection(factor_returns.index)
    returns_aligned = returns.loc[common_idx]
    factors_aligned = factor_returns.loc[common_idx]

    if len(common_idx) < 10:
        logger.warning(f"Few data points for regression: {len(common_idx)}")
        return {}

    # Fit regression
    model = LinearRegression()
    model.fit(factors_aligned.values, returns_aligned.values)

    attribution = dict(zip(factor_returns.columns, model.coef_))
    attribution["alpha"] = float(model.intercept_)
    return attribution


def rolling_sharpe(
    returns: pd.Series,
    window: int = 63,
    rf_rate: float = 0.0,
) -> pd.Series:
    """Calculate rolling Sharpe ratio.

    Args:
        returns: Series of periodic returns.
        window: Rolling window in periods (default 63 = 1 quarter).
        rf_rate: Risk-free rate (annualized). Default 0.0.

    Returns:
        Series of rolling Sharpe ratios.

    Examples:
        >>> returns = pd.Series(np.random.randn(252) * 0.01)
        >>> sharpe = rolling_sharpe(returns, window=63)
        >>> print(f"Current Sharpe: {sharpe.iloc[-1]:.2f}")
    """
    rolling_mean = returns.rolling(window).mean()
    rolling_std = returns.rolling(window).std()

    # Annualize (assuming daily returns)
    annual_mean = rolling_mean * 252
    annual_std = rolling_std * np.sqrt(252)

    sharpe = (annual_mean - rf_rate) / (annual_std + 1e-6)
    return sharpe


def rolling_volatility(
    returns: pd.Series,
    window: int = 63,
) -> pd.Series:
    """Calculate rolling volatility (annualized).

    Args:
        returns: Series of daily returns.
        window: Rolling window in periods. Default 63.

    Returns:
        Series of rolling annualized volatility.
    """
    rolling_std = returns.rolling(window).std()
    return rolling_std * np.sqrt(252)


def rolling_correlation(
    returns1: pd.Series,
    returns2: pd.Series,
    window: int = 63,
) -> pd.Series:
    """Calculate rolling correlation between two return series.

    Args:
        returns1: First series of returns.
        returns2: Second series of returns.
        window: Rolling window. Default 63.

    Returns:
        Series of rolling correlations.
    """
    df = pd.DataFrame({"r1": returns1, "r2": returns2})
    return df["r1"].rolling(window).corr(df["r2"])


def cumulative_returns(returns: pd.Series) -> pd.Series:
    """Calculate cumulative returns (log-normal compounding).

    Args:
        returns: Series of periodic returns.

    Returns:
        Series of cumulative returns.
    """
    return (1 + returns).cumprod() - 1


def calmar_ratio(
    returns: pd.Series,
) -> float:
    """Calculate Calmar ratio (return / max drawdown).

    Measures risk-adjusted return relative to downside risk.

    Args:
        returns: Series of returns.

    Returns:
        Calmar ratio (annualized return / max drawdown).
    """
    cum_returns = (1 + returns).cumprod()
    total_return = (cum_returns.iloc[-1] - 1) * 252 / len(returns)

    cummax = cum_returns.cummax()
    drawdown = (cum_returns - cummax) / cummax
    max_dd = -drawdown.min()

    if max_dd < 1e-6:
        return float("inf")
    return float(total_return / max_dd)
