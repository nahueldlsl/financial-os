import yfinance as yf
import pandas as pd
from fastapi import APIRouter
from datetime import datetime
from services.cache import TTLCache

router = APIRouter(prefix="/api/market", tags=["market"])
_search_cache = TTLCache(maxsize=300, ttl_seconds=3600)


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


@router.get("/fundamentals/{ticker}")
def get_asset_fundamentals(ticker: str, refresh: bool = False):
    """
    Retorna el análisis fundamental completo y valoración multimodelo de una acción o ETF.
    """
    from services.fundamental_service import FundamentalService
    return FundamentalService.get_fundamentals(ticker, force_refresh=refresh)


@router.get("/technical/{ticker}")
def get_asset_technical(ticker: str, refresh: bool = False):
    """
    Retorna los indicadores de análisis técnico (RSI, SMA 50/200, Bollinger, MACD, etc.).
    """
    from services.technical_service import TechnicalService
    return TechnicalService.get_technical_analysis(ticker, force_refresh=refresh)


@router.get("/confluence/{ticker}")
def get_asset_confluence(ticker: str, refresh: bool = False):
    """
    Retorna la síntesis de confluencia (Análisis Fundamental + Análisis Técnico).
    """
    from services.technical_service import TechnicalService
    return TechnicalService.get_confluence_analysis(ticker, force_refresh=refresh)


@router.get("/search")
def search_global_assets(q: str):
    """
    Busca acciones, ETFs y activos en el mercado global por símbolo o nombre.
    """
    query = q.strip()
    if not query:
        return {"results": []}

    cache_key = query.lower()
    cached = _search_cache.get(cache_key)
    if cached is not None:
        return {"results": cached}

    try:
        s = yf.Search(query, max_results=8)
        results = []
        for quote in (s.quotes or []):
            symbol = quote.get("symbol")
            if symbol:
                results.append({
                    "symbol": symbol,
                    "name": quote.get("shortname") or quote.get("longname") or symbol,
                    "exchange": quote.get("exchDisp") or quote.get("exchange") or "",
                    "type": quote.get("quoteType") or "EQUITY",
                    "sector": quote.get("sectorDisp") or quote.get("sector") or ""
                })
        
        if not results:
            clean_ticker = query.upper()
            results.append({
                "symbol": clean_ticker,
                "name": clean_ticker,
                "exchange": "",
                "type": "EQUITY",
                "sector": ""
            })

        _search_cache.set(cache_key, results)
        return {"results": results}
    except Exception as e:
        clean_ticker = query.upper()
        return {"results": [{
            "symbol": clean_ticker,
            "name": clean_ticker,
            "exchange": "",
            "type": "EQUITY",
            "sector": ""
        }]}



