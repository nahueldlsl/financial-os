from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from sqlmodel import Session
from typing import List, Dict
from models.models import Asset

class MarketDataService:
    CACHE_DURATION_MINUTES = 15

    @staticmethod
    def get_market_prices(session: Session, assets: List[Asset]) -> Dict[str, int]:
        """
        Devuelve un diccionario {ticker: precio_actual_en_centavos}.
        Usa caché si el dato en DB tiene menos de 15 minutos.
        Si está viejo, descarga en batch desde Yahoo Finance y actualiza la DB.
        """
        if not assets:
            return {}

        now = datetime.now()
        prices_map = {} # Ticker -> Cents (int)
        tickers_to_update = []
        ticker_to_asset_map = {} # Map uppercase ticker to asset for easy lookup

        # 1. Identificar qué tickers necesitan actualización
        for asset in assets:
            # Ensure asset ticker is treated as uppercase for processing
            ticker_upper = asset.ticker.upper()
            ticker_to_asset_map[ticker_upper] = asset
            
            needs_update = True
            if asset.cached_price is not None and asset.last_updated is not None:
                # Calcular edad del caché
                age = now - asset.last_updated
                if age < timedelta(minutes=MarketDataService.CACHE_DURATION_MINUTES):
                    needs_update = False
                    prices_map[asset.ticker] = asset.cached_price
            
            if needs_update:
                tickers_to_update.append(ticker_upper)
        
        # 2. Descargar datos frescos en BATCH (solo para los necesarios)
        if tickers_to_update:
            try:
                # threads=True acelera la descarga masiva
                print(f"Descargando precios para: {tickers_to_update}")
                # Use period="5d" to catch weekend/holiday gaps
                data = yf.download(tickers_to_update, period="5d", threads=True)['Close']
                
                # Manejo de respuesta de yfinance (puede ser Series o DataFrame)
                # Normalize data structure to handle single or multiple tickers uniformly if possible, 
                # but yfinance is tricky.
                
                # 3. Actualizar DB y completar el mapa
                for ticker in tickers_to_update:
                    asset = ticker_to_asset_map.get(ticker)
                    if not asset:
                        continue

                    new_price_float = 0.0
                    
                    # Extraer precio seguro
                    try:
                        # Logic to get the last valid price
                        if isinstance(data, pd.DataFrame):
                            if ticker in data.columns:
                                series = data[ticker]
                                last_valid_idx = series.last_valid_index()
                                if last_valid_idx is not None:
                                    new_price_float = float(series.loc[last_valid_idx])
                        elif isinstance(data, pd.Series):
                             # If single ticker result, yfinance returns Series named 'Close' or the ticker itself depending on version/context
                             # Usually for multiple it's DF, for single it might be Series.
                             # If we requested a list (even length 1), let's see. 
                             # If it's a Series, check if it's time-series or ticker-series. 
                             # 'Close' with period='5d' should be a Series with DateTime index if 1 ticker.
                             last_valid_idx = data.last_valid_index()
                             if last_valid_idx is not None:
                                 new_price_float = float(data.loc[last_valid_idx])
                                 
                    except Exception as e:
                        print(f"Error extracting price for {ticker}: {e}")
                        new_price_float = 0.0 # Fallback
                    
                    # Validar precio > 0 para guardar
                    if new_price_float > 0:
                        # CONVERT TO CENTS (Strict Logic)
                        new_price_cents = int(new_price_float * 100)
                        
                        asset.cached_price = new_price_cents
                        asset.last_updated = now
                        session.add(asset) # Marcar para UPDATE en DB
                        prices_map[asset.ticker] = new_price_cents
                    else:
                        print(f"WARNING: No se encontró precio para {ticker}. Verifica si está bien escrito.")
                        # Si falló la descarga, usamos el caché viejo si existe (or 0)
                        prices_map[asset.ticker] = asset.cached_price or 0

                session.commit() # Guardar cambios en lote
                
            except Exception as e:
                print(f"Error actualizando precios: {e}")
                # En caso de error masivo, intentar usar caché viejo para todos los fallidos
                for t in tickers_to_update:
                    asset = ticker_to_asset_map.get(t)
                    if asset:
                        prices_map[asset.ticker] = asset.cached_price or 0

        return prices_map
