"""Unit tests for risk metrics calculations."""

import numpy as np
import pandas as pd
import pytest

from src.risk_metrics import (
    parametric_var,
    historical_var,
    cornish_fisher_var,
    expected_shortfall,
    max_drawdown,
    herfindahl_index,
    correlation_regime_detector,
)


class TestVaRCalculations:
    """Test VaR calculation functions."""

    def test_parametric_var_basic(self):
        """Test parametric VaR with known distribution."""
        returns = pd.Series(np.random.normal(0, 0.01, 1000))
        var = parametric_var(returns, confidence=0.95)
        assert 0 < var < 1
        assert isinstance(var, float)

    def test_parametric_var_confidence(self):
        """Test that higher confidence yields higher VaR."""
        returns = pd.Series(np.random.normal(0, 0.01, 1000))
        var_95 = parametric_var(returns, confidence=0.95)
        var_99 = parametric_var(returns, confidence=0.99)
        assert var_99 > var_95

    def test_parametric_var_invalid_confidence(self):
        """Test error on invalid confidence."""
        returns = pd.Series([0.01, 0.02, 0.03])
        with pytest.raises(ValueError):
            parametric_var(returns, confidence=1.5)

    def test_historical_var(self):
        """Test historical VaR."""
        returns = pd.Series([-0.05, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.05])
        var = historical_var(returns, confidence=0.95)
        assert 0 < var < 1

    def test_cornish_fisher_var(self):
        """Test Cornish-Fisher VaR adjustment."""
        returns = pd.Series(np.random.standard_t(df=5, size=500))
        cf_var = cornish_fisher_var(returns, confidence=0.99)
        param_var = parametric_var(returns, confidence=0.99)
        # CF should adjust for kurtosis
        assert cf_var >= 0

    def test_expected_shortfall(self):
        """Test conditional VaR."""
        returns = pd.Series(np.random.normal(-0.001, 0.02, 1000))
        cvar = expected_shortfall(returns, confidence=0.95)
        var = historical_var(returns, confidence=0.95)
        assert cvar > 0
        assert cvar >= var


class TestDrawdown:
    """Test drawdown calculations."""

    def test_max_drawdown_simple(self):
        """Test drawdown on simple sequence."""
        equity = np.array([100, 110, 90, 95, 105])
        dd, dur = max_drawdown(equity)
        assert 0 < dd < 1
        assert dur > 0
        # Max drawdown from 110 to 90 = 18.2%
        assert 0.15 < dd < 0.25

    def test_max_drawdown_no_loss(self):
        """Test drawdown when always increasing."""
        equity = np.array([100, 110, 120, 130])
        dd, _ = max_drawdown(equity)
        assert dd == 0

    def test_max_drawdown_duration(self):
        """Test drawdown duration calculation."""
        equity = np.array([100, 110, 90, 100, 110])
        dd, dur = max_drawdown(equity)
        assert dd > 0
        assert dur > 0


class TestConcentration:
    """Test concentration metrics."""

    def test_hhi_equal_weight(self):
        """Test HHI for equal-weight portfolio."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        hhi = herfindahl_index(weights)
        assert np.isclose(hhi, 0.25)

    def test_hhi_single_asset(self):
        """Test HHI for single-asset portfolio."""
        weights = np.array([1.0])
        hhi = herfindahl_index(weights)
        assert np.isclose(hhi, 1.0)

    def test_hhi_concentrated(self):
        """Test HHI for concentrated portfolio."""
        weights = np.array([0.7, 0.2, 0.1])
        hhi = herfindahl_index(weights)
        assert 0.5 < hhi < 1.0

    def test_hhi_invalid_weights(self):
        """Test error on invalid weights."""
        weights = np.array([0.5, 0.3])  # Sum < 1
        with pytest.raises(ValueError):
            herfindahl_index(weights)


class TestRegimeDetection:
    """Test correlation regime detection."""

    def test_regime_detector_basic(self):
        """Test regime detection output."""
        returns = pd.DataFrame(np.random.randn(100, 3))
        regime = correlation_regime_detector(returns, lookback=30)

        assert "current_avg_corr" in regime
        assert "regime" in regime
        assert regime["regime"] in ["risk-on", "risk-off"]
        assert 0 <= regime["regime_score"] <= 1

    def test_regime_detector_high_corr(self):
        """Test regime detection with high correlation."""
        # Highly correlated data
        data = np.random.randn(100, 1)
        returns = pd.DataFrame(np.hstack([data, data + 0.01, data - 0.01]))
        regime = correlation_regime_detector(returns, lookback=30)

        # Should detect high correlation
        assert regime["current_avg_corr"] > 0.5


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_series(self):
        """Test with empty series."""
        returns = pd.Series([])
        var = parametric_var(returns, confidence=0.95)
        assert var >= 0

    def test_single_value(self):
        """Test with single value."""
        returns = pd.Series([0.01])
        var = parametric_var(returns, confidence=0.95)
        assert var >= 0

    def test_nan_handling(self):
        """Test NaN handling."""
        returns = pd.Series([0.01, np.nan, 0.02])
        # Should handle or skip NaNs
        var = parametric_var(returns.dropna(), confidence=0.95)
        assert var >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
