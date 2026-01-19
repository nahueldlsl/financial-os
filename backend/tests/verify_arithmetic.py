import sys
import os

# Add backend to sys.path
sys.path.append('/app')

from services.portfolio_service import PortfolioService
from models.models import Asset, Transaction, BrokerCash, TradeHistory
from services.market_service import MarketDataService
from sqlmodel import Session, create_engine, SQLModel

# Setup In-Memory DB
engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(engine)

def test_arithmetic():
    with Session(engine) as session:
        # User has $10 cost basis (1000 cents)
        asset = Asset(
            ticker="TST", 
            cantidad_total=1.0, 
            precio_promedio=1000,
            cached_price=1001, # Market $10.01 (1001 cents)
            last_updated=None,

        )
        session.add(asset)
        session.commit()

        # Determine strict mock for MarketData
        def mock_get_market_prices(session, assets):
            print("MOCK CALLED")
            return {a.ticker: a.cached_price for a in assets}
            
        MarketDataService.get_market_prices = mock_get_market_prices
        
        # Mock Dolar to 1.0 to avoid noise
        PortfolioService.get_dolar_price = lambda: 1.0
        
        summary = PortfolioService.get_dashboard_summary(session)
        
        print("Summary:", summary)
        
        # Check Net Worth
        if summary["net_worth"] != 10.01:
            print(f"FAIL: Net Worth {summary['net_worth']} != 10.01")
            sys.exit(1)
            
        # Check Performance
        perf_val = summary["performance"]["value"]
        if perf_val != 0.01:
            print(f"FAIL: Performance Value {perf_val} != 0.01")
            # Potential float precision issue? 0.0100000001?
            # Code uses round(..., 2). So it should be fine.
            sys.exit(1)
            
        print("PASS")

if __name__ == "__main__":
    test_arithmetic()
