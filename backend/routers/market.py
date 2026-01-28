import yfinance as yf
import pandas as pd
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/market", tags=["market"])

@router.get("/history/{ticker}")
def get_market_history(ticker: str, range: str = "1y"):
    # Configuración "Perfil Inversor"
    interval = "1d"
    period = "1y"
    
    range = range.lower()

    if range == "1d":
        period = "1d"
        interval = "15m" # 15 min para detalle diario
    elif range == "1w":
        period = "5d"
        interval = "60m" # Horas para la semana (forma detallada)
    elif range == "1m":
        period = "1mo"
        interval = "1d"
    elif range == "3m":
        period = "3mo"
        interval = "1d" # Trimestre (NUEVO)
    elif range == "max":
        period = "max"
        interval = "1d"
    
    print(f"DEBUG: Fetching {ticker} | Period: {period} | Interval: {interval}")

    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period=period, interval=interval, auto_adjust=True)
        
        if hist.empty:
            return {"data": []}

        data = []
        for index, row in hist.iterrows():
            # Validación de datos sucios
            if pd.isna(row['Close']):
                continue
                
            # Conversión Timestamp -> Unix Seconds
            # index es un datetime con timezone, timestamp() lo maneja a UTC
            ts = int(index.timestamp())
            
            data.append({
                "time": ts,
                "value": round(float(row['Close']), 2)
            })
            
        return {"data": data}

    except Exception as e:
        print(f"ERROR: Fallo en yfinance para {ticker}: {e}")
        return {"data": [], "error": "Failed to fetch market data"}
