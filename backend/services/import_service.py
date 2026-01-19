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

        for item in data:
            # 1. Validar claves (Case Sensitive Mapping)
            ticker = item.get("Ticker")
            cantidad = item.get("Cantidad_Total")
            precio_promedio_float = item.get("Precio_Promedio")

            if not ticker or cantidad is None or precio_promedio_float is None:
                continue # Skip invalid rows

            # Normalizar ticker
            ticker_normalized = str(ticker).strip().upper()

            # 2. Conversión de Tipos
            precio_promedio_cents = int(round(precio_promedio_float * 100))
            cantidad_float = float(cantidad)

            # 3. POO - Upsert Asset
            statement = select(Asset).where(Asset.ticker == ticker_normalized)
            asset = session.exec(statement).first()

            if asset:
                # Update
                asset.cantidad_total = cantidad_float
                asset.precio_promedio = precio_promedio_cents
            else:
                # Create
                asset = Asset(
                    ticker=ticker_normalized,
                    cantidad_total=cantidad_float,
                    precio_promedio=precio_promedio_cents
                )
                session.add(asset)
            
            # Commit parcial (o flush) para asegurar que existe y tiene ID si fuera necesario
            session.commit()
            session.refresh(asset)

            # 4. Actualización de Precio de Mercado (CRÍTICO)
            try:
                # Reutilizamos el servicio existente. Acepta lista, le pasamos [asset].
                # Esto internamente descarga de Yahoo, actualiza cached_price y hace commit.
                MarketDataService.get_market_prices(session, [asset])
                
                # Forzar refresco del objeto en memoria por si el servicio hizo cambios
                session.refresh(asset) 
                
            except Exception as e:
                print(f"Error obteniendo precio para {ticker_normalized}: {e}")
                # No rompemos el loop, seguimos con el siguiente
            
            processed_count += 1
        
        return {"processed": processed_count, "message": "Importación completada exitosamente"}
