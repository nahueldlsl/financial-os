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

# Utils
def safe_float(val):
    try:
        if val is None: return 0.0
        f = float(val)
        if math.isnan(f) or math.isinf(f): return 0.0
        return f
    except: return 0.0

def to_cents(val_float: float) -> int:
    """Convierte monto en DÓLARES (float) a CENTAVOS (int)."""
    return int(round(val_float * 100))

def to_dollars(val_cents: int) -> float:
    """Convierte CENTAVOS (int) a DÓLARES (float) para UI."""
    return safe_float(val_cents) / 100.0

class PortfolioService:
    
    @staticmethod
    def get_dolar_price() -> float:
        """
        Obtiene la cotización. Si falla o es nula, DEVUELVE 1.0 para NO ROMPER EL DASHBOARD.
        El dashboard asumirá paridad 1:1 o usará el valor anterior si existiera persistencia, 
        pero aquí garantizamos que no retorne 0 ni lance excepción.
        """
        try:
            import requests
            # Timeout corto para no bloquear la UI si la API externa está lenta
            resp = requests.get("https://uy.dolarapi.com/v1/cotizaciones/usd", timeout=2)
            val = float(resp.json().get('venta', 0))
            if val > 0:
                return val
            return 1.0 # Fallback safe
        except Exception:
            # Log error internally if needed
            return 1.0 # Fallback safe para que la UI muestre datos en USD

    @staticmethod
    def get_dashboard_summary(session: Session) -> Dict:
        # 1. Cotización Dólar (Safe Fallback implementado)
        dolar_val = PortfolioService.get_dolar_price()

        # 2. Efectivo Billetera (Cash Flow) - CENTS stored in DB
        # Transaction.monto is now INTEGER (cents).
        
        statement = select(
            func.sum(
                case(
                    (Transaction.moneda == 'USD', 
                     case((Transaction.tipo == 'gasto', -Transaction.monto), else_=Transaction.monto)
                    ), 
                    else_=0
                )
            ).label("total_usd_cents"),
            func.sum(
                case(
                    (Transaction.moneda != 'USD', 
                     case((Transaction.tipo == 'gasto', -Transaction.monto), else_=Transaction.monto)
                    ), 
                    else_=0
                )
            ).label("total_uyu_cents")
        )

        result = session.exec(statement).one()
        
        # Totales en centavos
        wallet_usd_cents = result[0] if result[0] is not None else 0
        wallet_uyu_cents = result[1] if result[1] is not None else 0
        
        # Convertir billetera unificada a Dólares (Float)
        # wallet_uyu_cents / 100 -> Pesos
        # / dolar_val -> Dólares
        wallet_uyu_in_usd = (safe_float(wallet_uyu_cents) / 100.0) / dolar_val if dolar_val > 0 else 0.0
        
        wallet_usd_total_dollars = to_dollars(wallet_usd_cents) + wallet_uyu_in_usd
        
        # 3. Efectivo Broker (Buying Power) - CENTS stored in DB
        broker_cash_obj = session.get(BrokerCash, 1)
        broker_cash_cents = broker_cash_obj.saldo_usd if broker_cash_obj else 0
        broker_cash_dollars = to_dollars(broker_cash_cents)

        # 4. Inversiones (Stocks)
        activos = session.exec(select(Asset)).all()
        investments_total_cents = 0.0 # Float temporal acumulando (Cantidad * PrecioCents)
        investments_performance_cents = 0.0
        
        # Prices are now cached in CENTS
        prices_map_cents = MarketDataService.get_market_prices(session, activos)
        
        for asset in activos:
            price_cents = prices_map_cents.get(asset.ticker, 0)
            
            # Cantidad es float (ej: 10.5 acciones)
            cantidad = safe_float(asset.cantidad_total)
            # Precio Promedio es int (cents)
            precio_promedio_cents = asset.precio_promedio

            # Val Mercado = 10.5 * 10050 cents = 105525.0
            val_mercado_cents = cantidad * price_cents
            
            # Costo Base = 10.5 * 9000 cents = 94500.0
            costo_base_cents = cantidad * precio_promedio_cents
            
            investments_total_cents += val_mercado_cents
            investments_performance_cents += (val_mercado_cents - costo_base_cents)

        # 5. TOTALES UNIFICADOS (EN DOLLARS PARA RETURN)
        
        # Convertir todo a dolares aqui, al final
        wallet_usd_dollars = to_dollars(wallet_usd_cents)
        investments_total_dollars = to_dollars(investments_total_cents)
        performance_total_dollars = to_dollars(investments_performance_cents)
        
        total_cash_global_dollars = wallet_usd_dollars + wallet_uyu_in_usd + broker_cash_dollars
        net_worth_dollars = total_cash_global_dollars + investments_total_dollars
        
        base_invested_dollars = net_worth_dollars - performance_total_dollars
        perc = (performance_total_dollars / base_invested_dollars * 100) if base_invested_dollars > 0 else 0.0

        # FORMAT OUTPUT (Rounding)
        return {
            "net_worth": round(net_worth_dollars, 2),
            "performance": {
                "value": round(performance_total_dollars, 2),
                "percentage": round(perc, 2),
                "isPositive": bool(performance_total_dollars >= 0)
            },
            "assets": [
                {"id": "stk", "name": "Acciones", "category": "Stock", "amount": round(investments_total_dollars, 2)},
                {"id": "c_wallet", "name": "Billetera Personal", "category": "Cash", "amount": round(wallet_usd_total_dollars, 2)},
                {"id": "c_broker", "name": "Caja Broker", "category": "Cash", "amount": round(broker_cash_dollars, 2)}
            ],
            "chart_data": [
                {"name": "Acciones", "value": round(investments_total_dollars, 2), "color": "#3b82f6"},
                {"name": "Billetera", "value": round(wallet_usd_total_dollars, 2), "color": "#10b981"},
                {"name": "Broker", "value": round(broker_cash_dollars, 2), "color": "#6366f1"}
            ]
        }

    @staticmethod
    def get_or_create_broker_cash(session: Session) -> BrokerCash:
        cash = session.get(BrokerCash, 1)
        if not cash:
            # Saldo inicial 0 cents
            cash = BrokerCash(id=1, saldo_usd=0)
            session.add(cash)
            session.commit()
            session.refresh(cash)
        return cash

    @staticmethod
    def execute_buy(session: Session, ticker: str, cantidad: float, precio: float, usar_caja_broker: bool, applied_fee: float = 0.0, fecha: Optional[datetime] = None):
        # Convertir INPUTS a CENTS
        precio_cents = to_cents(precio)
        fee_cents = to_cents(applied_fee)
        
        # Total Costo = (Cantidad * Precio) + Fee
        # Ojo: Cantidad es float.
        # Costo Base Operación (cents) = 10.5 * 10050 = 105525.0
        costo_bruto_cents = cantidad * precio_cents
        total_costo_cents = int(round(costo_bruto_cents + fee_cents)) # Final integer cents to deduct
        
        # 1. Verificar Caja
        if usar_caja_broker:
            cash = PortfolioService.get_or_create_broker_cash(session)
            if cash.saldo_usd < total_costo_cents:
                # Mostrar error amigable en Dólares
                saldo_dollars = to_dollars(cash.saldo_usd)
                costo_dollars = to_dollars(total_costo_cents)
                raise HTTPException(status_code=400, detail=f"Saldo insuficiente. Requerido: ${costo_dollars:.2f}, Disponible: ${saldo_dollars:.2f}")
            
            cash.saldo_usd -= total_costo_cents
            session.add(cash)

        # 2. Actualizar o Crear Activo
        asset = session.exec(select(Asset).where(Asset.ticker == ticker)).first()
        
        if not asset:
            asset = Asset(
                ticker=ticker,
                cantidad_total=cantidad,
                precio_promedio=precio_cents, # STORE AS CENTS
            )
        else:
            # Recalcular Promedio Ponderado
            # Costo anterior (total cents val)
            costo_anterior_cents = asset.cantidad_total * asset.precio_promedio # Float result
            
            # Nuevo costo total implícito (sin contar fees usualmente para el promedio, o si? 
            # Estándar fiscal: precio + comision es tu base de costo.
            # Según user prompt, "commission" es un campo aparte, pero "monto" es lo que pagas.
            # Vamos a sumar la comisión al costo base del activo para reflejar el costo real de adquisición (Break Even adecuado).
            
            nuevo_costo_total_cents = costo_anterior_cents + total_costo_cents 
            nueva_cantidad = asset.cantidad_total + cantidad
            
            asset.cantidad_total = nueva_cantidad
            
            # Nuevo promedio = Total Costo Cents / Nueva Cantidad
            if nueva_cantidad > 0:
                asset.precio_promedio = int(round(nuevo_costo_total_cents / nueva_cantidad))
            else:
                asset.precio_promedio = 0

        session.add(asset)

        # 3. Guardar en Historial (Input values stored as CENTS)
        hist = TradeHistory(
            ticker=ticker,
            tipo="BUY",
            cantidad=cantidad,
            precio=precio_cents,
            total=total_costo_cents,
            commission=fee_cents,
            fecha=fecha or datetime.now()
        )
        session.add(hist)
        session.commit()
        
        return {"mensaje": "Compra exitosa", "nuevo_promedio": to_dollars(asset.precio_promedio)}

    @staticmethod
    def execute_sell(session: Session, ticker: str, cantidad: float, precio: float, usar_caja_broker: bool, applied_fee: float = 0.0, fecha: Optional[datetime] = None):
        # Convert Inputs
        precio_cents = to_cents(precio)
        fee_cents = to_cents(applied_fee)
        
        # 1. Verificar si tenemos la acción
        asset = session.exec(select(Asset).where(Asset.ticker == ticker)).first()
        if not asset or asset.cantidad_total < cantidad:
            raise HTTPException(status_code=400, detail="No tienes suficientes acciones para vender")

        # Cálculos Venta
        total_venta_bruta_cents = cantidad * precio_cents # Float
        # Net proceeds = Bruto - Fee
        total_venta_neta_cents = int(round(total_venta_bruta_cents - fee_cents))
        
        # 2. Calcular Ganancia Realizada (FIFO o Promedio? Usamos Promedio según modelo simplificado)
        # Costo de la parte vendida
        costo_proporcional_cents = cantidad * asset.precio_promedio
        # Ganancia = Net Proceeds - Cost Basis
        ganancia_cents = int(round(total_venta_neta_cents - costo_proporcional_cents))

        # 3. Actualizar Activo
        asset.cantidad_total -= cantidad
        if asset.cantidad_total <= 0.00001:
            asset.cantidad_total = 0
            asset.precio_promedio = 0 
        
        session.add(asset)

        # 4. Actualizar Caja Broker
        if usar_caja_broker:
            cash = PortfolioService.get_or_create_broker_cash(session)
            # Sumamos lo neto (lo que realmente entró al bolsillo)
            cash.saldo_usd += total_venta_neta_cents
            session.add(cash)

        # 5. Guardar Historial
        hist = TradeHistory(
            ticker=ticker,
            tipo="SELL",
            cantidad=cantidad,
            precio=precio_cents,
            total=total_venta_neta_cents,
            ganancia_realizada=ganancia_cents,
            commission=fee_cents,
            fecha=fecha or datetime.now()
        )
        session.add(hist)
        session.commit()
        
        return {"mensaje": "Venta exitosa", "ganancia_realizada": to_dollars(ganancia_cents)}
