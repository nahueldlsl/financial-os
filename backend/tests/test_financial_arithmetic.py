from services.portfolio_service import PortfolioService, to_cents, to_dollars
from models.models import Asset
from unittest.mock import MagicMock
from sqlmodel import Session

def test_arithmetic_precision(session):
    # Setup Data in Cents
    # Buy 1 share at $10.00 (1000 cents)
    # Market Price goes to $10.01 (1001 cents)
    
    asset = Asset(
        ticker="TST", 
        cantidad_total=1.0, 
        precio_promedio=1000 # Cost $10.00
    )
    asset.cached_price = 1001 # Market $10.01
    
    session.add(asset)
    session.commit()
    
    # Mock MarketDataService to just return cached_price without fetching
    original_get = PortfolioService.get_market_prices 
    # Wait, PortfolioService calls MarketDataService.get_market_prices. We can mock that.
    
    from services.market_service import MarketDataService
    
    # Mock return dict
    def mock_get_prices(session, assets):
        return {a.ticker: a.cached_price for a in assets}
    
    # Monkeypatch
    MarketDataService.get_market_prices = mock_get_prices

    # Run Dashboard Summary
    summary = PortfolioService.get_dashboard_summary(session)
    
    # Net Worth should be:
    # Asset Value: 1 * 1001 = 1001 cents = $10.01
    # Cash: 0
    # Total: $10.01
    
    assert summary["net_worth"] == 10.01
    
    # Performance:
    # Value $10.01
    # Cost $10.00
    # Gain $0.01
    assert summary["performance"]["value"] == 0.01
    assert summary["performance"]["percentage"] > 0
