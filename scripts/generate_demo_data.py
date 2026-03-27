"""Generate demo data for testing the dashboard.

Downloads real historical price data from Yahoo Finance for demo portfolio assets.
"""

import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Demo portfolio tickers
DEMO_TICKERS = ["AAPL", "MSFT", "TSLA", "GLD", "TLT", "USO", "BTC", "ETH", "SPY", "QQQ"]


def download_demo_data(output_path: str = "data/demo_data.csv") -> pd.DataFrame:
    """Download 1 year of historical data for demo portfolio.

    Args:
        output_path: Path to save CSV file.

    Returns:
        DataFrame of adjusted close prices.
    """
    logger.info(f"Downloading data for {len(DEMO_TICKERS)} tickers...")

    end = datetime.now()
    start = end - timedelta(days=252)

    try:
        data = yf.download(DEMO_TICKERS, start=start, end=end, progress=False)["Adj Close"]
        logger.info(f"Downloaded {len(data)} rows")

        # Save to CSV
        data.to_csv(output_path)
        logger.info(f"Saved to {output_path}")

        # Calculate stats
        returns = data.pct_change().dropna()
        logger.info(f"\nStats (last 252 days):")
        logger.info(f"  Returns mean: {returns.mean():.4f}")
        logger.info(f"  Returns std: {returns.std():.4f}")
        logger.info(f"  Correlation:\n{returns.corr().round(3)}")

        return data

    except Exception as e:
        logger.error(f"Error downloading data: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    download_demo_data()
