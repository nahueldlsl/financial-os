from models.models import Asset
from services.import_service import ImportService
from services.market_service import MarketDataService
import json
from unittest.mock import MagicMock

def test_import_snapshot_updates_price(session, monkeypatch):
    # Mock MarketDataService.get_market_prices
    # We want to verify it was called and it "updates" the asset (simulated)
    
    original_get_prices = MarketDataService.get_market_prices
    
    # Mock function that simulates what the real service does: updates cached_price
    def mock_get_market_prices(session, assets):
        for asset in assets:
            # Simulate fetching a price (e.g. $150.00 -> 15000 cents)
            asset.cached_price = 15000
            session.add(asset)
        session.commit()
    
    monkeypatch.setattr(MarketDataService, "get_market_prices", mock_get_market_prices)

    # Input JSON
    json_content = json.dumps([
        { "Ticker": "NVDA", "Cantidad_Total": 5.0, "Precio_Promedio": 100.0 }
    ])
    
    ImportService.import_snapshot(session, json_content)
    
    # Verify Asset is created AND cached_price is set
    asset = session.query(Asset).filter(Asset.ticker == "NVDA").first()
    assert asset is not None
    assert asset.cantidad_total == 5.0
    assert asset.precio_promedio == 10000 # Cost base
    assert asset.cached_price == 15000    # Market Price Updated by Mock
    
    monkeypatch.setattr(MarketDataService, "get_market_prices", original_get_prices)
