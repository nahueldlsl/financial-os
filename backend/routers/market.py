from fastapi import APIRouter
import yfinance as yf
import pandas as pd
from datetime import datetime

router = APIRouter(prefix="/api/market", tags=["market"])

@router.get("/chart")
def get_market_chart(ticker: str, range: str = "1M"):
    """
    Endpoints agnóstico para gráficos.
    Range: 1D, 1W, 1M, 1Y
    """
    period = "1mo"
    interval = "1d"
    
    if range == "1D":
        period = "1d"
        interval = "5m" # Intraday granular
    elif range == "1W":
        period = "5d"
        interval = "1h"
    elif range == "1M":
        period = "1mo"
        interval = "1d"
    elif range == "1Y":
        period = "1y"
        interval = "1d"
        
    try:
        # Download data
        # auto_adjust=True gets Close adjusted for splits/dividends which is often better for charts
        data = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        
        if data.empty:
            return {"data": []}
            
        # Reset index to access Date
        data = data.reset_index()
        
        chart_data = []
        for _, row in data.iterrows():
            try:
                # Detect Time Column
                # Yfinance puts 'Date' or 'Datetime' depending on interval
                ts_col = 'Datetime' if 'Datetime' in data.columns else 'Date'
                
                ts_val = row[ts_col]
                price_val = row['Close']
                
                # Check for NaN
                if pd.isna(price_val):
                    continue
                    
                # Ensure we have a proper datetime object
                if isinstance(ts_val, (pd.Timestamp, datetime)):
                    ts_str = ts_val.strftime('%Y-%m-%d')
                else:
                    ts_str = str(ts_val).split(' ')[0] # Fallback
                
                chart_data.append({
                    "time": ts_str, 
                    "price": float(price_val)
                })
            except Exception:
                continue
                
        return {"data": chart_data}
        
    except Exception as e:
        print(f"Error fetching chart for {ticker}: {e}")
        return {"data": [], "error": "Failed to fetch market data"}
