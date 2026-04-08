from sqlmodel import Session, select
from models.models import Asset, TradeHistory
from datetime import datetime
import re

class BrokerImportService:
    @staticmethod
    def _parse_spanish_date(date_str: str) -> datetime:
        """Convierte '27 mar 2026 11:23' a un objeto datetime nativo de Python"""
        if not date_str:
            return None
            
        meses = {
            "ene": "01", "feb": "02", "mar": "03", "abr": "04",
            "may": "05", "jun": "06", "jul": "07", "ago": "08",
            "sep": "09", "oct": "10", "nov": "11", "dic": "12"
        }
        
        # Limpiar el input para prevenir problemas con espacios extra
        date_str = date_str.strip().lower()
        
        # Mapear mes a número (reemplazamos por texto el mes en el string y parseamos a int)
        for mes_str, mes_num in meses.items():
            if mes_str in date_str:
                date_str = date_str.replace(mes_str, mes_num)
                break
                
        try:
            # Ahora debería quedar como "27 03 2026 11:23"
            # Ojo: si hay extra espacios se maneja bien con %d %m %Y %H:%M
            # Para estar 100% seguros parseamos con Regex para sacar las partes
            match = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+):(\d+)", date_str)
            if match:
                dia, mes, asno, hora, min = match.groups()
                return datetime(int(asno), int(mes), int(dia), int(hora), int(min))
        except Exception as e:
            print("Error parsing Spanish date:", date_str, e)
            
        return datetime.now()

    @staticmethod
    def process_broker_data(session: Session, historial_json: list, posiciones_json: list):
        """
        Cruza el historial con las posiciones actuales para calcular
        la Inversión Neta y actualizar los Assets en la Base de Datos.
        """
        # 1. Calcular Inversión Neta y Fechas por Ticker
        inversion_neta_por_ticker = {}
        fechas_transacciones = {} # { ticker: { "compras": [], "todas": [] } }
        transacciones_validas = {} # { ticker: [] }
        
        for tx in historial_json:
            estado = tx.get("estado")
            if estado and estado != "Terminado":
                continue
                
            ticker = tx.get("ticker")
            if not ticker:
                continue
                
            monto = float(tx.get("monto", 0))
            operacion = tx.get("operacion", "").lower()
            fecha_str = tx.get("fecha", "")
            
            # Parsing robusto de fecha
            dt = BrokerImportService._parse_spanish_date(fecha_str) if fecha_str else None
            
            if ticker not in inversion_neta_por_ticker:
                inversion_neta_por_ticker[ticker] = 0.0
                fechas_transacciones[ticker] = { "compras": [], "todas": [] }
                transacciones_validas[ticker] = []
                
            inversion_neta_por_ticker[ticker] -= monto
            
            if dt:
                fechas_transacciones[ticker]["todas"].append(dt)
                if "compra" in operacion:
                    fechas_transacciones[ticker]["compras"].append(dt)

            transacciones_validas[ticker].append({
                "monto": monto,
                "operacion": operacion.upper(), # 'COMPRA...' o 'VENTA...'
                "fecha": dt if dt else datetime.now()
            })
            
        # 2. Procesar Posiciones y crear/actualizar Assets
        for pos in posiciones_json:
            ticker = pos.get("ticker")
            if not ticker:
                continue
                
            cantidad_acciones = float(pos.get("cantidad_acciones", 0.0))
            valor_actual_total = float(pos.get("valor_total_usd", 0.0))
            
            inversion_neta = inversion_neta_por_ticker.get(ticker, 0.0)
            
            # Precio promedio (en dólares) -> a CENTAVOS para la DB
            if cantidad_acciones > 0.000001:
                precio_promedio_usd = inversion_neta / cantidad_acciones
                cached_price_usd = valor_actual_total / cantidad_acciones
            else:
                precio_promedio_usd = 0.0
                cached_price_usd = 0.0
                
            precio_promedio_cents = int(round(precio_promedio_usd * 100))
            cached_price_cents = int(round(cached_price_usd * 100))
            
            # Mapeo de Fechas Agregadas usando el Join Array
            ticker_fechas = fechas_transacciones.get(ticker, { "compras": [], "todas": [] })
            compras = ticker_fechas["compras"]
            todas = ticker_fechas["todas"]
            
            primera_compra = min(compras) if compras else None
            ultima_operacion = max(todas) if todas else None
            
            # Actualizar DB
            statement = select(Asset).where(Asset.ticker == ticker)
            existing_asset = session.exec(statement).first()
            
            if existing_asset:
                existing_asset.cantidad_total = cantidad_acciones
                existing_asset.precio_promedio = precio_promedio_cents
                existing_asset.cached_price = cached_price_cents
                existing_asset.last_updated = datetime.now()
                # Enriquecemos con los dates reales del Broker Histórico
                if primera_compra: existing_asset.fecha_primera_compra = primera_compra
                if ultima_operacion: existing_asset.fecha_ultima_operacion = ultima_operacion
                session.add(existing_asset)
            else:
                new_asset = Asset(
                    ticker=ticker,
                    cantidad_total=cantidad_acciones,
                    precio_promedio=precio_promedio_cents,
                    cached_price=cached_price_cents,
                    last_updated=datetime.now(),
                    fecha_primera_compra=primera_compra,
                    fecha_ultima_operacion=ultima_operacion
                )
                session.add(new_asset)
                
            # ---- ACTULIZAR TRADE HISTORY ----
            # Borrar las trades anteriores para no acular duplicados
            old_trades = session.exec(select(TradeHistory).where(TradeHistory.ticker == ticker)).all()
            for old_t in old_trades:
                session.delete(old_t)
                
            # Insertar los historiales con cálculos proporcionales
            txs_ticker = transacciones_validas.get(ticker, [])
            for tx_info in txs_ticker:
                monto_trade = tx_info["monto"]
                is_buy = monto_trade < 0
                op_type = "BUY" if is_buy else "SELL"
                abs_monto = abs(monto_trade)
                total_cents = int(round(abs_monto * 100))
                
                if precio_promedio_usd > 0.0001:
                    qty = abs_monto / precio_promedio_usd
                else:
                    qty = 0.0
                    
                new_trade = TradeHistory(
                    ticker=ticker,
                    tipo=op_type,
                    cantidad=qty,
                    precio=precio_promedio_cents,
                    total=total_cents,
                    fecha=tx_info["fecha"],
                    commission=0,
                    ganancia_realizada=0
                )
                session.add(new_trade)
                
        # 3. Limpiar Assets que ya no existen en posiciones (ej: Venta total)
        posiciones_tickers = { pos.get("ticker") for pos in posiciones_json if pos.get("ticker") }
        all_assets = session.exec(select(Asset)).all()
        
        for db_asset in all_assets:
            if db_asset.ticker not in posiciones_tickers:
                # El activo ya no está en el portafolio actual (se vendió todo)
                session.delete(db_asset)
                
        # Commit se hace desde el router
