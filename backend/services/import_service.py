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

        for item in data:
            # 1. Validar claves
            ticker = item.get("Ticker")
            cantidad = item.get("Cantidad_Total")
            precio_promedio_float = item.get("Precio_Promedio")

            if not ticker or cantidad is None or precio_promedio_float is None:
                continue

            # Normalizar ticker
            ticker_normalized = str(ticker).strip().upper()

            # 2. Conversión de Tipos
            precio_promedio_cents = int(round(precio_promedio_float * 100))
            cantidad_float = float(cantidad)
            
            # CRÍTICO: No tocamos Asset directamente.
            # Creamos una transacción "BUY" histórica base.
            
            # Calcular total (Costo Base Aproximado)
            total_cents = int(round(cantidad_float * precio_promedio_cents))

            # Verificar si ya existe alguna historia para no duplicar en importaciones sucesivas?
            # Por simplicidad del requerimiento "Event Replay", asumimos que es una importación
            # o snapshot. Idealmente borraríamos historia previa si es un "Full Import".
            # Pero agregaremos un flag o description para identificarlo.
            
            hist_entry = TradeHistory(
                ticker=ticker_normalized,
                tipo="BUY", # Tratamos el saldo inicial como una COMPRA
                cantidad=cantidad_float,
                precio=precio_promedio_cents,
                total=total_cents,
                commission=0,
                fecha=datetime(2024, 1, 1), # Fecha base fija para ordenar al inicio
                ganancia_realizada=0
            )
            
            session.add(hist_entry)
            session.commit() # Guardar historia
            
            # 3. TRIGGER EVENT REPLAY
            PortfolioService.recalculate_asset_from_history(session, ticker_normalized)
            
            # 4. Actualizar Precio Mercado (Opcional, pero bueno para UX inmediata)
            try:
                # Buscamos el asset recién creado/actualizado por el Replay
                asset = session.exec(select(Asset).where(Asset.ticker == ticker_normalized)).first()
                if asset:
                    MarketDataService.get_market_prices(session, [asset])
            except Exception:
                pass
            
            processed_count += 1
        
        return {"processed": processed_count, "message": "Importación completada exitosamente"}
