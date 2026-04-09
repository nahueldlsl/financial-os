import sys
import os
from datetime import datetime
from sqlmodel import Session, create_engine, select

# Adjust path to backend
sys.path.append(r"c:\Users\nahue\OneDrive\Escritorio\UCU\Proyectos\Visualizacion de inversion\backend")

from models.models import TradeHistory, Asset
from services.analytics_service import AnalyticsService

# postgres connection (Localhost access to Docker)
DB_URL = "postgresql://admin:secret@localhost:5432/financial_db"
engine = create_engine(DB_URL)

def debug_data():
    with Session(engine) as session:
        trades = session.exec(select(TradeHistory).order_by(TradeHistory.fecha.asc())).all()
        if not trades:
            print("No trades found.")
            return

        print(f"First trade: {trades[0].fecha} | Type: {trades[0].tipo} | Asset: {trades[0].ticker} | Amount: {trades[0].total}")
        print(f"Last trade: {trades[-1].fecha}")
        
        history = AnalyticsService.get_portfolio_history(session)
        if history:
            print(f"History length: {len(history)} days")
            print(f"First day in history: {history[0]}")
            print(f"Last day in history: {history[-1]}")
            
            # Check for any extremely small valor_mercado
            small_vals = [h for h in history if 0 < h['valor_mercado'] < 0.1]
            if small_vals:
                print(f"WARNING: Found {len(small_vals)} days with tiny portfolio value (< $0.10)")
                print(f"Example: {small_vals[0]}")
        else:
            print("No history returned by AnalyticsService.")

if __name__ == "__main__":
    try:
        debug_data()
    except Exception as e:
        print(f"Error: {e}")
