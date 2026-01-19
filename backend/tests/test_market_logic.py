
import pytest
from unittest.mock import MagicMock, patch
from services.market_service import MarketDataService
from models.models import Asset
import pandas as pd
from datetime import datetime

def test_market_service_typo_handling(session):
    # Setup
    asset_typo = Asset(ticker="APPL", cached_price=None, last_updated=None) # Typo
    asset_ok = Asset(ticker="AAPL", cached_price=None, last_updated=None)
    
    # We patch yfinance at the module level where it's imported in market_service (or just yfinance.download)
    # market_service imports yfinance as yf. So we patch 'yfinance.download'
    with patch('yfinance.download') as mock_download:
        # Simulate yfinance return structure
        # When calling multiple tickers, it returns a DF.
        
        # Create a Mock DataFrame for 'Close'
        data = {
            "AAPL": [150.0, 151.0, 152.0],
            # APPL is effectively missing (not in columns) or NaN
        }
        df_close = pd.DataFrame(data)
        df_close.index = pd.date_range(start='2023-01-01', periods=3)
        
        # The service calls yf.download(...)['Close']
        # So we mock return_value['Close'] to be our df_close
        mock_return_obj = MagicMock()
        mock_return_obj.__getitem__.side_effect = lambda key: df_close if key == 'Close' else None
        
        mock_download.return_value = mock_return_obj
        
        # Act
        prices = MarketDataService.get_market_prices(session, [asset_typo, asset_ok])
        
        # Assert
        
        # 1. AAPL should be updated
        assert "AAPL" in prices
        assert prices["AAPL"] == 15200 # 152.0 * 100
        
        # 2. APPL should be 0 (fallback) and should print WARNING
        # Note: Asset uses original ticker case in map? Logic uses asset.ticker.
        # Logic: asset.ticker is "APPL". prices_map key is "APPL".
        assert "APPL" in prices
        assert prices["APPL"] == 0

def test_market_service_weekend_logic(session):
     # Setup
    asset = Asset(ticker="MSFT", cached_price=None, last_updated=None)
    
    with patch('yfinance.download') as mock_download:
        # Simulate logic: Data exists for index 0, but NaN for index 1
        # last_valid_index should pick 0.
        
        series = pd.Series([300.0, float('nan')], index=[0, 1]) 
        df_close = pd.DataFrame({"MSFT": series})
        
        mock_return_obj = MagicMock()
        mock_return_obj.__getitem__.return_value = df_close
        mock_download.return_value = mock_return_obj
        
        prices = MarketDataService.get_market_prices(session, [asset])
        
        # Should pick last valid (300.0) -> 30000
        assert prices["MSFT"] == 30000
