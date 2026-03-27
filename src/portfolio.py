"""Portfolio class for position and exposure management."""

import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Sector mapping for demo assets
SECTOR_MAP = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "TSLA": "Automotive",
    "GLD": "Commodities",
    "TLT": "Fixed Income",
    "USO": "Commodities",
    "BTC": "Crypto",
    "ETH": "Crypto",
    "SPY": "Broad Market",
    "QQQ": "Technology",
}


class Portfolio:
    """Portfolio management class.

    Maintains positions, calculates weights, exposure, and leverage metrics.

    Args:
        positions: Dict of {ticker: quantity}.
        prices: Dict of {ticker: price}.
    """

    def __init__(self, positions: Dict[str, float], prices: Dict[str, float]):
        """Initialize portfolio.

        Args:
            positions: Dict of {ticker: quantity}.
            prices: Dict of {ticker: price}.
        """
        self.positions = positions.copy()
        self.prices = prices.copy()
        self._validate()

    def _validate(self) -> None:
        """Validate portfolio consistency."""
        missing = set(self.positions.keys()) - set(self.prices.keys())
        if missing:
            logger.warning(f"Missing prices for: {missing}")

    @property
    def notional_values(self) -> Dict[str, float]:
        """Get notional value (quantity * price) per position."""
        return {
            ticker: self.positions[ticker] * self.prices.get(ticker, 0)
            for ticker in self.positions
        }

    @property
    def gross_value(self) -> float:
        """Total gross exposure (long + short absolute values)."""
        return sum(abs(v) for v in self.notional_values.values())

    @property
    def net_value(self) -> float:
        """Net portfolio value (sum of all positions)."""
        return sum(self.notional_values.values())

    @property
    def total_long(self) -> float:
        """Total long exposure."""
        return sum(v for v in self.notional_values.values() if v > 0)

    @property
    def total_short(self) -> float:
        """Total short exposure (absolute value)."""
        return abs(sum(v for v in self.notional_values.values() if v < 0))

    @property
    def gross_leverage(self) -> float:
        """Gross leverage ratio."""
        if self.net_value == 0:
            return 0.0
        return self.gross_value / abs(self.net_value)

    @property
    def weights(self) -> Dict[str, float]:
        """Portfolio weights (normalized by net value)."""
        if self.net_value == 0:
            return {}
        return {ticker: v / self.net_value for ticker, v in self.notional_values.items()}

    @property
    def weights_array(self) -> np.ndarray:
        """Weights as numpy array (sorted by ticker)."""
        tickers = sorted(self.positions.keys())
        w = self.weights
        return np.array([w.get(t, 0) for t in tickers])

    @property
    def sector_exposure(self) -> Dict[str, float]:
        """Exposure by sector."""
        sector_exp = {}
        for ticker, value in self.notional_values.items():
            sector = SECTOR_MAP.get(ticker, "Other")
            sector_exp[sector] = sector_exp.get(sector, 0) + value
        return sector_exp

    @property
    def concentration(self) -> Dict[str, float]:
        """Position concentration metrics."""
        w = self.weights
        weights_array = np.array(list(w.values()))

        # Herfindahl index
        hhi = float(np.sum(weights_array**2))

        # Top 3 concentration
        top_3 = sum(sorted(weights_array)[-3:]) if len(weights_array) >= 3 else 1.0

        return {
            "herfindahl_index": hhi,
            "top_3_concentration": float(top_3),
            "n_positions": len(self.positions),
        }

    def update_prices(self, prices: Dict[str, float]) -> None:
        """Update asset prices.

        Args:
            prices: Dict of {ticker: new_price}.
        """
        self.prices.update(prices)

    def update_positions(self, positions: Dict[str, float]) -> None:
        """Update positions (rebalance).

        Args:
            positions: Dict of {ticker: new_quantity}.
        """
        self.positions.update(positions)

    @staticmethod
    def from_demo() -> "Portfolio":
        """Create demo portfolio with 10 assets.

        Returns:
            Portfolio instance.
        """
        positions = {
            "AAPL": 100,
            "MSFT": 75,
            "TSLA": 50,
            "GLD": 200,
            "TLT": 150,
            "USO": 100,
            "BTC": 0.5,
            "ETH": 5.0,
            "SPY": 25,
            "QQQ": 40,
        }

        prices = {
            "AAPL": 150.0,
            "MSFT": 320.0,
            "TSLA": 240.0,
            "GLD": 190.0,
            "TLT": 95.0,
            "USO": 70.0,
            "BTC": 45000.0,
            "ETH": 2500.0,
            "SPY": 430.0,
            "QQQ": 360.0,
        }

        return Portfolio(positions, prices)

    def __repr__(self) -> str:
        return (
            f"Portfolio(net_value=${self.net_value:,.0f}, "
            f"gross_leverage={self.gross_leverage:.2f}x, "
            f"positions={len(self.positions)})"
        )
