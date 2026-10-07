import json
from sqlmodel import Session, select
from models.models import Asset

class ImportService:
    @staticmethod
    def parse_unstructured_text(text: str):
        """
        Intenta parsear texto a JSON.
        Esta función es un placeholder para futura integración con IA.
        Por ahora, asume que el input es un JSON string válido.
        """
        try:
            # Limpieza básica por si viene con markdown blocks ```json ... ```
            clean_text = text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parseando JSON: {str(e)}")

    @staticmethod
    def import_snapshot(session: Session, content: str):
        """
        Procesa el JSON de snapshot y actualiza/crea los assets.
        JSON Esperado:
        [
            { "Ticker": "ADBE", "Cantidad_Total": 0.03047, "Precio_Promedio": 370.8 },
            ...
        ]
        """
        data = ImportService.parse_unstructured_text(content)
        
        if not isinstance(data, list):
            raise ValueError("El JSON debe ser una lista de objetos.")

        processed_count = 0
        
        
        # Guardamos inicialmente para asegurar que el Asset tiene estado base en DB (aunque no es estrictamente necesario si usamos el objeto en memoria, pero el usuario pidió commit dentro del loop o flujo similar, aqui haremos upsert y luego precio)
        # El usuario pidió: "Dentro del bucle... despues de session.add y session.commit... llama a MarketService"
        # Para eficiencia, podemos mantener el session.add(asset) en el loop, y llamar al servicio al final, PERO el usuario fue especifico sobre "Inmediatamente despues". 
        # Si hacemos commit por cada uno es lento. Mejor haremos un commit intermedio si es critico o usamos el objeto asset que ya está "attached" a la session.
        # Vamos a seguir la instruccion de "Dentro del bucle" para asegurar que cada activo quede listo.
        
        from services.market_service import MarketDataService

        from models.models import TradeHistory
        from services.portfolio_service import PortfolioService
        from datetime import datetime

        # FIX-12: Collect all entries first, then batch commit + recalculate
        unique_tickers = set()

        for item in data:
            # 1. Validar claves
            ticker = item.get("Ticker")
            cantidad = item.get("Cantidad_Total")
            precio_promedio_float = item.get("Precio_Promedio")

            if not ticker or cantidad is None or precio_promedio_float is None:
                continue

            # Normalizar ticker
            ticker_normalized = str(ticker).strip().upper()
            unique_tickers.add(ticker_normalized)

            # 2. Conversión de Tipos
            precio_promedio_cents = int(round(precio_promedio_float * 100))
            cantidad_float = float(cantidad)
            
            # Calcular total (Costo Base Aproximado)
            total_cents = int(round(cantidad_float * precio_promedio_cents))

            # Extraer fecha si viene en el snapshot, de lo contrario datetime.now()
            trade_date = datetime.now()
            fecha_raw = item.get("fecha") or item.get("date") or item.get("Fecha")
            if fecha_raw:
                try:
                    trade_date = datetime.fromisoformat(str(fecha_raw))
                except (ValueError, TypeError):
                    pass

            hist_entry = TradeHistory(
                ticker=ticker_normalized,
                tipo="BUY",
                cantidad=cantidad_float,
                precio=precio_promedio_cents,
                total=total_cents,
                commission=0,
                fecha=trade_date,
                ganancia_realizada=0
            )
            
            session.add(hist_entry)
            processed_count += 1

        # Un solo commit para todas las historias
        session.commit()
        
        # Recalcular solo los tickers únicos (no repetir)
        for ticker in unique_tickers:
            PortfolioService.recalculate_asset_from_history(session, ticker)
        
        # Actualizar precios de mercado en batch
        try:
            all_assets = [session.exec(select(Asset).where(Asset.ticker == t)).first() for t in unique_tickers]
            valid_assets = [a for a in all_assets if a is not None]
            if valid_assets:
                MarketDataService.get_market_prices(session, valid_assets)
        except Exception:
            pass
        
        return {"processed": processed_count, "message": "Importación completada exitosamente"}
