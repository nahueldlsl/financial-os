from datetime import datetime
from typing import List, Optional, Dict
from sqlmodel import Session, select
from sqlalchemy import func, case
import math
from fastapi import HTTPException

# Models
from models.models import Asset, Transaction, BrokerCash, TradeHistory
# Services
from services.market_service import MarketDataService
# Utils (podríamos moverlas a utils, pero por ahora aquí)
def safe_float(val):
    try:
        if val is None: return 0.0
        f = float(val)
        if math.isnan(f) or math.isinf(f): return 0.0
        return f
    except: return 0.0

class PortfolioService:
    
    @staticmethod
    def get_dolar_price() -> float:
        # Aquí podrías inyectar un servicio de Dólar si quisieras
        # Por simplicidad, replicamos la lógica o la importamos. 
        # Idealmente: Services shouldn't import from Routers.
        # Duplicamos la lógica simple requests aquí para desacoplar.
        try:
            import requests
            resp = requests.get("https://uy.dolarapi.com/v1/cotizaciones/usd", timeout=3)
            return float(resp.json().get('venta', 41.0))
        except:
            return 41.0

    @staticmethod
    def get_dashboard_summary(session: Session) -> Dict:
        # 1. Cotización Dólar
        dolar_val = PortfolioService.get_dolar_price()

        # 2. Efectivo Billetera (Cash Flow) - OPTIMIZADO CON SQL
        # Usamos CASE para sumar condicionalmente en BD
        # total_wallet_usd = SUM(CASE WHEN moneda='USD' THEN (CASE WHEN tipo='gasto' THEN -monto ELSE monto END) ELSE 0 END)
        # total_wallet_uyu = SUM(CASE WHEN moneda!='USD' THEN (CASE WHEN tipo='gasto' THEN -monto ELSE monto END) ELSE 0 END)
        
        statement = select(
            func.sum(
                case(
                    (Transaction.moneda == 'USD', 
                     case((Transaction.tipo == 'gasto', -Transaction.monto), else_=Transaction.monto)
                    ), 
                    else_=0.0
                )
            ).label("total_usd"),
            func.sum(
                case(
                    (Transaction.moneda != 'USD', 
                     case((Transaction.tipo == 'gasto', -Transaction.monto), else_=Transaction.monto)
                    ), 
                    else_=0.0
                )
            ).label("total_uyu")
        )

        result = session.exec(statement).one()
        
        # result puede traer None si no hay registros, así que usamos 'or 0.0'
        total_wallet_usd = safe_float(result[0] if result[0] is not None else 0.0)
        total_wallet_uyu = safe_float(result[1] if result[1] is not None else 0.0)
        
        wallet_equivalent = total_wallet_usd + (total_wallet_uyu / dolar_val if dolar_val > 0 else 0)

        # 3. Efectivo Broker (Buying Power)
        broker_cash_obj = session.get(BrokerCash, 1)
        broker_cash_val = safe_float(broker_cash_obj.saldo_usd) if broker_cash_obj else 0.0

        # 4. Inversiones (Stocks)
        activos = session.exec(select(Asset)).all()
        investments_total = 0.0
        investments_performance = 0.0
        
        # --- NUEVA LÓGICA CON SERVICIO DE MERCADO ---
        # Delegamos la obtención de precios al MarketDataService (con caché)
        prices_map = MarketDataService.get_market_prices(session, activos)
        
        for asset in activos:
            price = prices_map.get(asset.ticker, 0.0)
            
            # Cálculos por activo
            cantidad = safe_float(asset.cantidad_total)
            precio_promedio = safe_float(asset.precio_promedio)

            val_mercado = cantidad * price
            costo_base = cantidad * precio_promedio
            
            investments_total += val_mercado
            investments_performance += (val_mercado - costo_base)

        # 5. TOTALES UNIFICADOS
        wallet_safe = safe_float(wallet_equivalent)
        broker_safe = safe_float(broker_cash_val)
        investments_safe = safe_float(investments_total)
        performance_safe = safe_float(investments_performance)

        # Net Worth
        total_cash_global = wallet_safe + broker_safe
        net_worth = total_cash_global + investments_safe
        
        base_invested = net_worth - performance_safe
        perc = (performance_safe / base_invested * 100) if base_invested > 0 else 0.0

        return {
            "net_worth": round(safe_float(net_worth), 2),
            "performance": {
                "value": round(performance_safe, 2),
                "percentage": round(safe_float(perc), 2),
                "isPositive": bool(performance_safe >= 0)
            },
            "assets": [
                {"id": "stk", "name": "Acciones", "category": "Stock", "amount": round(investments_safe, 2)},
                {"id": "c_wallet", "name": "Billetera Personal", "category": "Cash", "amount": round(wallet_safe, 2)},
                {"id": "c_broker", "name": "Caja Broker", "category": "Cash", "amount": round(broker_safe, 2)}
            ],
            "chart_data": [
                {"name": "Acciones", "value": round(investments_safe, 2), "color": "#3b82f6"},
                {"name": "Billetera", "value": round(wallet_safe, 2), "color": "#10b981"},
                {"name": "Broker", "value": round(broker_safe, 2), "color": "#6366f1"}
            ]
        }

    @staticmethod
    def get_or_create_broker_cash(session: Session) -> BrokerCash:
        cash = session.get(BrokerCash, 1)
        if not cash:
            cash = BrokerCash(id=1, saldo_usd=0.0)
            session.add(cash)
            session.commit()
            session.refresh(cash)
        return cash

    @staticmethod
    def execute_buy(session: Session, ticker: str, cantidad: float, precio: float, usar_caja_broker: bool, applied_fee: float = 0.0, fecha: Optional[datetime] = None):
        total_costo = (cantidad * precio) + applied_fee
        
        # 1. Verificar Caja
        if usar_caja_broker:
            cash = PortfolioService.get_or_create_broker_cash(session)
            if cash.saldo_usd < total_costo:
                raise HTTPException(status_code=400, detail=f"Saldo insuficiente. Tienes ${cash.saldo_usd:.2f}")
            cash.saldo_usd -= total_costo
            session.add(cash)

        # 2. Actualizar o Crear Activo
        asset = session.exec(select(Asset).where(Asset.ticker == ticker)).first()
        
        if not asset:
            asset = Asset(
                ticker=ticker,
                cantidad_total=cantidad,
                precio_promedio=precio,
                drip_enabled=False
            )
        else:
            costo_anterior = asset.cantidad_total * asset.precio_promedio
            nuevo_costo = costo_anterior + total_costo
            nueva_cantidad = asset.cantidad_total + cantidad
            
            asset.cantidad_total = nueva_cantidad
            asset.precio_promedio = nuevo_costo / nueva_cantidad if nueva_cantidad > 0 else 0

        session.add(asset)

        # 3. Guardar en Historial
        hist = TradeHistory(
            ticker=ticker,
            tipo="BUY",
            cantidad=cantidad,
            precio=precio,
            total=total_costo,
            commission=applied_fee,
            fecha=fecha or datetime.now()
        )
        session.add(hist)
        session.commit()
        
        return {"mensaje": "Compra exitosa", "nuevo_promedio": asset.precio_promedio}

    @staticmethod
    def execute_sell(session: Session, ticker: str, cantidad: float, precio: float, usar_caja_broker: bool, applied_fee: float = 0.0, fecha: Optional[datetime] = None):
        # 1. Verificar si tenemos la acción
        asset = session.exec(select(Asset).where(Asset.ticker == ticker)).first()
        if not asset or asset.cantidad_total < cantidad:
            raise HTTPException(status_code=400, detail="No tienes suficientes acciones para vender")

        total_venta_bruta = cantidad * precio
        total_venta_neta = total_venta_bruta - applied_fee
        
        # 2. Calcular Ganancia Realizada
        costo_proporcional = cantidad * asset.precio_promedio
        ganancia = total_venta_neta - costo_proporcional

        # 3. Actualizar Activo
        asset.cantidad_total -= cantidad
        if asset.cantidad_total <= 0.00001:
            asset.cantidad_total = 0
            asset.precio_promedio = 0 
        
        session.add(asset)

        # 4. Actualizar Caja Broker
        if usar_caja_broker:
            cash = PortfolioService.get_or_create_broker_cash(session)
            cash.saldo_usd += total_venta_neta
            session.add(cash)

        # 5. Guardar Historial
        hist = TradeHistory(
            ticker=ticker,
            tipo="SELL",
            cantidad=cantidad,
            precio=precio,
            total=total_venta_neta,
            ganancia_realizada=ganancia,
            commission=applied_fee,
            fecha=fecha or datetime.now()
        )
        session.add(hist)
        session.commit()
        
        return {"mensaje": "Venta exitosa", "ganancia_realizada": ganancia}
