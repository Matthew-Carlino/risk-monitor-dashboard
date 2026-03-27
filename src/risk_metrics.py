"""Core risk metrics calculations for portfolio analysis.

This module implements institutional-grade risk metrics including Value at Risk (VaR),
Conditional VaR, drawdown analysis, and correlation regime detection.

References:
    Jorion, P. (2007). Value at Risk: The New Benchmark for Managing Financial Risk
    Hull, J. (2018). Risk Management and Financial Institutions
"""

import logging
from typing import Tuple, Optional
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def parametric_var(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.99,
    horizon: int = 1,
) -> float:
    """Calculate parametric Value at Risk assuming normal distribution.

    Uses the delta-normal approach: VaR = -mean - z_score * std * sqrt(horizon).
    Fast and parametric, assumes normal distribution.

    Args:
        returns: Series of asset returns (daily or periodic).
        confidence: Confidence level (0.95 = 95%, 0.99 = 99%). Default 0.99.
        horizon: Number of periods (1 for 1-day VaR, 5 for 5-day VaR). Default 1.

    Returns:
        Parametric VaR as a decimal (e.g., 0.05 = 5% loss).

    Raises:
        ValueError: If confidence is not in (0, 1) or horizon < 1.

    Examples:
        >>> returns = pd.Series([-0.02, 0.01, -0.015, 0.03, -0.01])
        >>> var = parametric_var(returns, confidence=0.99)
        >>> print(f"99% 1-day VaR: {var:.4f}")
    """
    if not (0 < confidence < 1):
        raise ValueError(f"Confidence must be in (0, 1), got {confidence}")
    if horizon < 1:
        raise ValueError(f"Horizon must be >= 1, got {horizon}")

    returns = np.asarray(returns)
    mean = np.mean(returns)
    std = np.std(returns, ddof=1)

    z_score = stats.norm.ppf(1 - confidence)
    var = -(mean + z_score * std * np.sqrt(horizon))
    return max(var, 0.0)


def historical_var(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.99,
) -> float:
    """Calculate historical simulation Value at Risk.

    Computes the empirical quantile from historical returns. Model-free approach
    that captures non-normality and tail risk without distributional assumptions.

    Args:
        returns: Series of historical asset returns.
        confidence: Confidence level (0.99 = 99th percentile). Default 0.99.

    Returns:
        Historical VaR as a decimal.

    Raises:
        ValueError: If confidence is not in (0, 1).

    Examples:
        >>> returns = pd.Series([-0.02, 0.01, -0.015, 0.03, -0.01, -0.04])
        >>> var = historical_var(returns, confidence=0.95)
        >>> print(f"95% Historical VaR: {var:.4f}")
    """
    if not (0 < confidence < 1):
        raise ValueError(f"Confidence must be in (0, 1), got {confidence}")

    returns = np.asarray(returns)
    percentile = (1 - confidence) * 100
    var = np.abs(np.percentile(returns, percentile))
    return var


def cornish_fisher_var(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.99,
) -> float:
    """Calculate Cornish-Fisher adjusted VaR.

    Adjusts parametric VaR for skewness and excess kurtosis, providing better
    estimates for non-normal distributions with fat tails.

    Formula:
        z_cf = z + (z^2 - 1) * skew / 6 + (z^3 - 3*z) * kurt / 24 - (2*z^3 - 5*z) * skew^2 / 36
        CF-VaR = mean - z_cf * std

    Args:
        returns: Series of historical returns.
        confidence: Confidence level. Default 0.99.

    Returns:
        Cornish-Fisher adjusted VaR as a decimal.

    Examples:
        >>> returns = pd.Series(np.random.standard_t(df=5, size=500))
        >>> cf_var = cornish_fisher_var(returns, confidence=0.99)
        >>> parametric = parametric_var(returns, confidence=0.99)
        >>> print(f"CF-VaR captures fat tails: {cf_var > parametric}")
    """
    if not (0 < confidence < 1):
        raise ValueError(f"Confidence must be in (0, 1), got {confidence}")

    returns = np.asarray(returns)
    mean = np.mean(returns)
    std = np.std(returns, ddof=1)

    z = stats.norm.ppf(1 - confidence)
    skewness = stats.skew(returns)
    kurtosis = stats.kurtosis(returns)

    z_cf = (
        z
        + (z**2 - 1) * skewness / 6
        + (z**3 - 3 * z) * kurtosis / 24
        - (2 * z**3 - 5 * z) * skewness**2 / 36
    )

    var = -(mean + z_cf * std)
    return max(var, 0.0)


def expected_shortfall(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.99,
) -> float:
    """Calculate Conditional VaR (Expected Shortfall).

    Measures the expected loss conditional on exceeding VaR. Better tail risk
    measure than VaR alone, satisfies subadditivity (coherent risk metric).

    Formula:
        CVaR = E[Loss | Loss > VaR]

    Args:
        returns: Series of historical returns.
        confidence: Confidence level. Default 0.99.

    Returns:
        CVaR as a decimal (typically > VaR).

    Examples:
        >>> returns = pd.Series([-0.05, -0.03, -0.02, -0.01, 0.01, 0.02])
        >>> var = historical_var(returns, 0.95)
        >>> cvar = expected_shortfall(returns, 0.95)
        >>> print(f"CVaR exceeds VaR: {cvar > var}")
    """
    if not (0 < confidence < 1):
        raise ValueError(f"Confidence must be in (0, 1), got {confidence}")

    returns = np.asarray(returns)
    var_threshold = np.percentile(returns, (1 - confidence) * 100)
    cvar = np.mean(returns[returns <= var_threshold])
    return np.abs(cvar)


def component_var(
    weights: np.ndarray | pd.Series,
    returns: pd.DataFrame,
    confidence: float = 0.99,
) -> pd.Series:
    """Decompose portfolio VaR into per-asset contributions.

    Calculates marginal VaR (impact of adding 1% to each position) and multiplies
    by current weight to get component VaR. Shows which assets drive portfolio risk.

    Args:
        weights: Portfolio weights (must sum to 1.0).
        returns: DataFrame of asset returns (assets as columns).
        confidence: Confidence level. Default 0.99.

    Returns:
        Series of component VaR by asset.

    Raises:
        ValueError: If weights don't sum to approximately 1.0.

    Examples:
        >>> returns = pd.DataFrame(
        ...     np.random.randn(252, 3) * 0.01,
        ...     columns=['AAPL', 'MSFT', 'GOOGL']
        ... )
        >>> weights = np.array([0.4, 0.35, 0.25])
        >>> comp_var = component_var(weights, returns)
        >>> print(comp_var.sort_values(ascending=False))
    """
    weights = np.asarray(weights).flatten()
    if not np.isclose(weights.sum(), 1.0, atol=0.01):
        raise ValueError(f"Weights must sum to ~1.0, got {weights.sum()}")

    returns = np.asarray(returns)
    n_assets = returns.shape[1]

    # Portfolio returns
    portfolio_returns = returns @ weights

    # Covariance matrix
    cov_matrix = np.cov(returns, rowvar=False)

    # Portfolio volatility
    portfolio_std = np.sqrt(weights @ cov_matrix @ weights)

    # Marginal VaR = derivative of portfolio VaR w.r.t. weight
    z = stats.norm.ppf(1 - confidence)
    marginal_var = np.zeros(n_assets)

    for i in range(n_assets):
        marginal_var[i] = -(z * (cov_matrix[i, :] @ weights) / portfolio_std)

    # Component VaR = Marginal VaR * Weight
    component_var_values = marginal_var * weights

    return pd.Series(
        component_var_values,
        index=returns.columns if hasattr(returns, "columns") else None,
    )


def max_drawdown(
    equity_curve: pd.Series | np.ndarray,
) -> Tuple[float, int]:
    """Calculate maximum drawdown and recovery period.

    Identifies peak-to-trough decline, measuring largest percentage loss from peak
    to subsequent trough. Also returns duration (periods to recover).

    Args:
        equity_curve: Series of portfolio values over time (daily/periodic).

    Returns:
        Tuple of (max_drawdown_pct, duration_periods).
        max_drawdown_pct: As decimal (0.20 = 20% drawdown).
        duration_periods: Number of periods from peak to recovery.

    Examples:
        >>> equity = pd.Series([100, 110, 95, 105, 100, 120])
        >>> dd, dur = max_drawdown(equity)
        >>> print(f"Max drawdown: {dd:.2%}, Duration: {dur} periods")
    """
    equity = np.asarray(equity_curve)
    cummax = np.maximum.accumulate(equity)
    drawdown = (equity - cummax) / cummax
    max_dd = np.min(drawdown)

    # Duration: periods from peak to recovery
    max_dd_idx = np.argmin(drawdown)
    recovery_idx = np.where(equity[max_dd_idx:] >= cummax[max_dd_idx])[0]
    duration = (
        len(recovery_idx) + max_dd_idx if len(recovery_idx) > 0 else len(equity)
    )

    return np.abs(max_dd), duration


def herfindahl_index(weights: np.ndarray | pd.Series) -> float:
    """Calculate Herfindahl-Hirschman Index (HHI).

    Measures portfolio concentration. HHI = sum(weight_i^2).
    Range: [1/N, 1] where 1/N is equal-weight (least concentrated)
    and 1 is single-asset (most concentrated).

    Args:
        weights: Portfolio weights (must sum to 1.0).

    Returns:
        HHI as decimal (0.1 = 10% concentration).

    Raises:
        ValueError: If weights don't sum to ~1.0.

    Examples:
        >>> weights = np.array([0.25, 0.25, 0.25, 0.25])  # Equal weight
        >>> hhi = herfindahl_index(weights)
        >>> print(f"HHI (equal-weight): {hhi:.4f}")  # Should be 0.25
        >>> weights = np.array([1.0])  # Single asset
        >>> hhi = herfindahl_index(weights)
        >>> print(f"HHI (single): {hhi:.4f}")  # Should be 1.0
    """
    weights = np.asarray(weights).flatten()
    if not np.isclose(weights.sum(), 1.0, atol=0.01):
        raise ValueError(f"Weights must sum to ~1.0, got {weights.sum()}")

    return float(np.sum(weights**2))


def correlation_regime_detector(
    returns: pd.DataFrame,
    lookback: int = 60,
) -> dict:
    """Detect market regime (risk-on/risk-off) from correlation structure.

    Analyzes rolling correlation of assets. Risk-off regime exhibits high correlation
    (diversification breakdown). Risk-on regime shows lower correlation (diversification works).

    Args:
        returns: DataFrame of asset returns (assets as columns).
        lookback: Lookback period for rolling correlation. Default 60 days.

    Returns:
        Dict with keys:
        - 'current_avg_corr': Current rolling average correlation
        - 'regime': 'risk-on' or 'risk-off'
        - 'regime_score': Float in [0, 1] where 0=risk-on, 1=risk-off
        - 'correlation_history': Series of rolling correlations
        - 'correlation_threshold': Threshold for regime classification

    Examples:
        >>> returns = pd.DataFrame(np.random.randn(252, 3), columns=['A', 'B', 'C'])
        >>> regime = correlation_regime_detector(returns, lookback=60)
        >>> print(f"Current regime: {regime['regime']}")
        >>> print(f"Avg correlation: {regime['current_avg_corr']:.3f}")
    """
    if len(returns) < lookback:
        logger.warning(
            f"Insufficient data: {len(returns)} < lookback {lookback}. Using all available."
        )
        lookback = len(returns) // 2

    # Calculate rolling correlation
    corr_history = []
    for i in range(lookback, len(returns)):
        window = returns.iloc[i - lookback : i]
        corr_matrix = window.corr()
        # Average absolute correlation (excluding diagonal)
        mask = ~np.eye(len(corr_matrix), dtype=bool)
        avg_corr = np.abs(corr_matrix.values[mask]).mean()
        corr_history.append(avg_corr)

    corr_series = pd.Series(corr_history, index=returns.index[lookback:])
    current_corr = corr_series.iloc[-1] if len(corr_series) > 0 else 0.5

    # Regime detection
    corr_median = corr_series.median() if len(corr_series) > 0 else 0.5
    corr_std = corr_series.std() if len(corr_series) > 1 else 0.1
    threshold = corr_median + 0.5 * corr_std

    regime_score = min(
        (current_corr - corr_median) / (corr_std + 1e-6) if corr_std > 0 else 0, 1.0
    )
    regime_score = max(0.0, regime_score)

    regime = "risk-off" if current_corr > threshold else "risk-on"

    return {
        "current_avg_corr": float(current_corr),
        "regime": regime,
        "regime_score": float(regime_score),
        "correlation_history": corr_series,
        "correlation_threshold": float(threshold),
    }
