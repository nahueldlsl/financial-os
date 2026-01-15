from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from sqlmodel import Session
from typing import List, Dict
from models.models import Asset

class MarketDataService:
    CACHE_DURATION_MINUTES = 15

    @staticmethod
    def get_market_prices(session: Session, assets: List[Asset]) -> Dict[str, float]:
        """
        Devuelve un diccionario {ticker: precio_actual}.
        Usa caché si el dato en DB tiene menos de 15 minutos.
        Si está viejo, descarga en batch desde Yahoo Finance y actualiza la DB.
        """
        if not assets:
            return {}

        now = datetime.now()
        prices_map = {}
        tickers_to_update = []

        # 1. Identificar qué tickers necesitan actualización
        for asset in assets:
            needs_update = True
            if asset.cached_price is not None and asset.last_updated is not None:
                # Calcular edad del caché
                age = now - asset.last_updated
                if age < timedelta(minutes=MarketDataService.CACHE_DURATION_MINUTES):
                    needs_update = False
                    prices_map[asset.ticker] = asset.cached_price
            
            if needs_update:
                tickers_to_update.append(asset.ticker)
        
        # 2. Descargar datos frescos en BATCH (solo para los necesarios)
        if tickers_to_update:
            try:
                # threads=True acelera la descarga masiva
                print(f"Descargando precios para: {tickers_to_update}")
                data = yf.download(tickers_to_update, period="1d", threads=True)['Close']
                
                # Manejo de respuesta de yfinance (puede ser Series o DataFrame)
                current_prices = pd.Series()
                if not data.empty:
                    current_prices = data.iloc[-1]
                
                # 3. Actualizar DB y completar el mapa
                for asset in assets:
                    if asset.ticker in tickers_to_update:
                        new_price = 0.0
                        
                        # Extraer precio seguro
                        try:
                            if isinstance(current_prices, pd.Series):
                                if asset.ticker in current_prices:
                                    new_price = float(current_prices[asset.ticker])
                            else:
                                # Caso borde: un solo ticker devuelve float o scalar
                                if tickers_to_update[0] == asset.ticker:
                                    new_price = float(current_prices)
                        except Exception:
                            new_price = 0.0 # Fallback
                        
                        # Validar precio > 0 para guardar
                        if new_price > 0:
                            asset.cached_price = new_price
                            asset.last_updated = now
                            session.add(asset) # Marcar para UPDATE en DB
                            prices_map[asset.ticker] = new_price
                        else:
                            # Si falló la descarga, usamos el caché viejo si existe
                            prices_map[asset.ticker] = asset.cached_price or 0.0

                session.commit() # Guardar cambios en lote
                
            except Exception as e:
                print(f"Error actualizando precios: {e}")
                # En caso de error masivo, intentar usar caché viejo para todos los fallidos
                for t in tickers_to_update:
                    # Encontrar el asset para ese ticker
                    asset = next((a for a in assets if a.ticker == t), None)
                    if asset:
                        prices_map[t] = asset.cached_price or 0.0

        return prices_map
