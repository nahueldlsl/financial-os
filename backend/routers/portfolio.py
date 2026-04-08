# backend/routers/portfolio.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from typing import List, Optional
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from database import get_session
from models.models import Asset, BrokerCash, TradeHistory, Transaction
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["portfolio"])

class TradeSchema(BaseModel):
    ticker: str
    type: str # "BUY" or "SELL"
    quantity: float
    price: float
    date: Optional[datetime] = None
    applied_fee: float = 0.0
    usar_caja_broker: bool = True

class TransactionDateUpdate(BaseModel):
    date: datetime


class TradeAction(BaseModel):
    ticker: str
    cantidad: float
    precio: float
    fecha: Optional[datetime] = None
    applied_fee: float = 0.0
    usar_caja_broker: bool = True # Si True, descuenta/suma al saldo del broker

class BrokerFund(BaseModel):
    monto_enviado: float   # <--- Verifica que tengas estos dos nombres exactos
    monto_recibido: float
    tipo: str              # "DEPOSIT" | "WITHDRAW"

class ImportRequest(BaseModel):
    content: str
# --- AUXILIARES ---
# Eliminadas funciones duplicadas (get_or_create_broker_cash, get_dolar_price) en favor de PortfolioService

# --- ENDPOINTS DE CAJA (BUYING POWER) ---

# --- ENDPOINTS DE CAJA (BUYING POWER) ---
@router.get("/broker/cash")
def get_broker_cash(session: Session = Depends(get_session)):
    from services.portfolio_service import PortfolioService
    cash = PortfolioService.get_or_create_broker_cash(session)
    # Return Dollars
    return {"saldo_usd": cash.saldo_usd / 100.0}

# 2. ACTUALIZAMOS LA LÓGICA DE FONDEO
@router.post("/broker/fund")
def fund_broker(fund: BrokerFund, session: Session = Depends(get_session)):
    from services.portfolio_service import PortfolioService
    # Usamos el servicio
    cash = PortfolioService.get_or_create_broker_cash(session)
    
    # Inputs en Dólares (Float)
    monto_enviado_cents = int(round(fund.monto_enviado * 100))
    monto_recibido_cents = int(round(fund.monto_recibido * 100))
    
    comision_cents = monto_enviado_cents - monto_recibido_cents
    
    if fund.tipo == "DEPOSIT":
        # Aumentamos saldo Broker (Cents)
        cash.saldo_usd += monto_recibido_cents
        
        # REGISTRO AUTOMÁTICO EN CASH FLOW (Billetera Principal)
        # 1. El dinero que salió de la cuenta (Transferencia)
        gasto_transferencia = Transaction(
            tipo="gasto",
            monto=monto_recibido_cents, # CENTS
            moneda="USD",
            categoria="Transferencia a Broker",
            fecha=datetime.now()
        )
        session.add(gasto_transferencia)

        # 2. Si hubo comisión, la registramos aparte para tener control
        if comision_cents > 0:
            gasto_comision = Transaction(
                tipo="gasto",
                monto=comision_cents, # CENTS
                moneda="USD",
                categoria="Comisión Broker / Transferencia",
                fecha=datetime.now()
            )
            session.add(gasto_comision)

    elif fund.tipo == "WITHDRAW":
        if cash.saldo_usd < monto_enviado_cents:
            raise HTTPException(status_code=400, detail="Saldo insuficiente en broker")
        
        # Restamos del Broker
        cash.saldo_usd -= monto_enviado_cents # Aquí sale el total
        
        # Ingreso en Cash Flow (Banco)
        ingreso_banco = Transaction(
            tipo="ingreso",
            monto=monto_recibido_cents, # Llega menos por comisión (CENTS)
            moneda="USD",
            categoria="Retiro desde Broker",
            fecha=datetime.now()
        )
        session.add(ingreso_banco)

        if comision_cents > 0:
             # Opcional: Registrar la comisión de salida como gasto o simplemente registrar el ingreso neto
             pass 

    # Guardar Historial de Trading (Solo informativo)
    # Convertimos a CENTS para historial
    hist = TradeHistory(
        ticker="CASH", 
        tipo=fund.tipo, 
        cantidad=1, 
        precio=monto_recibido_cents, # Cents
        total=monto_recibido_cents    # Cents
    )
    session.add(hist)
    session.add(cash)
    session.commit()
    
    return {"nuevo_saldo": cash.saldo_usd / 100.0, "comision_registrada": comision_cents / 100.0}

@router.post("/portfolio/trade")
def execute_trade(trade: TradeSchema, session: Session = Depends(get_session)):
    from services.portfolio_service import PortfolioService
    
    # 1. Determinar Fecha Real
    trade_date = trade.date if trade.date else datetime.utcnow()
    
    try:
        if trade.type.upper() == "BUY":
            return PortfolioService.execute_buy(
                session=session,
                ticker=trade.ticker,
                cantidad=trade.quantity,
                precio=trade.price,
                usar_caja_broker=trade.usar_caja_broker,
                applied_fee=trade.applied_fee,
                fecha=trade_date
            )
        elif trade.type.upper() == "SELL":
            return PortfolioService.execute_sell(
                session=session,
                ticker=trade.ticker,
                cantidad=trade.quantity,
                precio=trade.price,
                usar_caja_broker=trade.usar_caja_broker,
                applied_fee=trade.applied_fee,
                fecha=trade_date
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid trade type. Must be BUY or SELL")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/portfolio/transaction/{id}")
def update_transaction_date(id: int, update: TransactionDateUpdate, session: Session = Depends(get_session)):
    # 1. Buscar la transacción
    tx = session.get(TradeHistory, id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # 2. Actualizar solo la fecha
    tx.fecha = update.date
    session.add(tx)
    session.commit()
    
    return {"status": "success", "message": "Transaction date updated", "new_date": tx.fecha}


# --- OPERACIONES DE TRADING (BUY / SELL) - LEGACY SUPPORT (Optional, keeping for now) ---
@router.post("/trade/buy")
def comprar_accion(trade: TradeAction, session: Session = Depends(get_session)):
    from services.portfolio_service import PortfolioService
    try:
        resultado = PortfolioService.execute_buy(
            session=session,
            ticker=trade.ticker,
            cantidad=trade.cantidad,
            precio=trade.precio,
            usar_caja_broker=trade.usar_caja_broker,
            applied_fee=trade.applied_fee,
            fecha=trade.fecha
        )
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade/sell")
def vender_accion(trade: TradeAction, session: Session = Depends(get_session)):
    # Delegar lógica compleja al servicio
    from services.portfolio_service import PortfolioService
    try:
        resultado = PortfolioService.execute_sell(
            session=session,
            ticker=trade.ticker,
            cantidad=trade.cantidad,
            precio=trade.precio,
            usar_caja_broker=trade.usar_caja_broker,
            applied_fee=trade.applied_fee,
            fecha=trade.fecha
        )
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/import")
def import_snapshot(request: ImportRequest, session: Session = Depends(get_session)):
    from services.import_service import ImportService
    try:
        result = ImportService.import_snapshot(session, request.content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/portfolio/transaction/{id}")
def delete_transaction(id: int, session: Session = Depends(get_session)):
    """
    Elimina una transacción y revierte sus efectos en el Activo (Asset).
    ACID: Todo sucede en una sesión.
    """
    # 1. Obtener Transacción
    tx = session.get(TradeHistory, id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # 2. Obtener Activo asociado
    asset = session.exec(select(Asset).where(Asset.ticker == tx.ticker)).first()
    
    # Si no hay activo (raro, pero posible si se borró manualmente), solo borramos la tx?
    # Asumimos consistencia: Si hay historial, debería haber asset o al menos rastro.
    # Pero si 'asset' es None, no podemos revertir matemática.
    # Procedemos a borrar la TX solamente si no hay asset, o lanzamos error?
    # Para robustez, si no hay asset, asumimos que ya está en 0 o borrado.
    
    if asset:
        qty_borrada = tx.cantidad
        precio_borrado_cents = tx.precio
        
        # 3. Lógica Inversa (Undo Math)
        if tx.tipo == "BUY":
            # Restamos la quantity al Asset
            nuevo_total_qty = asset.cantidad_total - qty_borrada
            
            # Validación de Seguridad
            if nuevo_total_qty < 0:
                raise HTTPException(status_code=400, detail="Inconsistencia: Borrar esta compra dejaría saldo negativo en el activo.")
            
            if nuevo_total_qty == 0:
                # Si queda en 0, reseteamos promedio y total
                asset.cantidad_total = 0.0
                asset.precio_promedio = 0
            else:
                # Recálculo de Precio Promedio (Revertir Ponderado)
                # ValorActual (Cents) = QtyActual * PrecioPromActual
                curr_val_cents = asset.cantidad_total * asset.precio_promedio
                borrado_val_cents = qty_borrada * precio_borrado_cents
                
                nuevo_val_cents = curr_val_cents - borrado_val_cents
                
                # Nuevo Promedio
                nuevo_promedio = nuevo_val_cents / nuevo_total_qty
                
                asset.cantidad_total = nuevo_total_qty
                asset.precio_promedio = int(nuevo_promedio) # Mantenemos enteros (Cents)
                
        elif tx.tipo == "SELL":
            # Sumar la quantity de vuelta al Asset (te devuelven las acciones)
            asset.cantidad_total += qty_borrada
            # El precio promedio NO cambia al deshacer una venta (FIFO/LIFO aparte).
            # Se asume que vendiste acciones que tenías a un precio promedio X.
            # Al devolverlas, vuelven a formar parte del pool al mismo precio promedio X (idealmente).
            # Nota: Si tu lógica de Venta alteró el precio promedio (error común), esto no lo arregla.
            # Pero en contabilidad estándar, Venta no toca Average Cost.
        
        # Guardamos cambios en Asset
        session.add(asset)

    # 4. Borrado Físico
    session.delete(tx)
    
    # 5. Commit
    session.commit()
    
    return {"status": "success", "message": "Transaction deleted and asset updated"}


@router.get("/portfolio")
def obtener_portafolio(session: Session = Depends(get_session)):
    # FIX-11: Usar servicio cacheado en vez de yf.download directo
    from services.market_service import MarketDataService
    from services.portfolio_service import to_dollars
    
    activos_db = session.exec(select(Asset).where(Asset.cantidad_total > 0)).all()
    if not activos_db:
         return {"resumen": {"valor_total_portafolio": 0, "ganancia_total_usd": 0, "rendimiento_total_porc": 0}, "posiciones": []}

    # Usar el servicio cacheado (15 min TTL)
    prices_map = MarketDataService.get_market_prices(session, activos_db)
    
    posiciones = []
    total_invertido = 0.0
    valor_actual = 0.0
    
    for asset in activos_db:
        price_cents = prices_map.get(asset.ticker, 0)
        precio_actual = price_cents / 100.0
        precio_promedio = asset.precio_promedio / 100.0
        cantidad = float(asset.cantidad_total)
        
        val_mercado = cantidad * precio_actual
        costo_base = cantidad * precio_promedio
        ganancia = val_mercado - costo_base
        rendimiento = (ganancia / costo_base * 100) if costo_base > 0 else 0
        
        total_invertido += costo_base
        valor_actual += val_mercado
        
        posiciones.append({
            "Ticker": asset.ticker,
            "Cantidad_Total": round(cantidad, 5),
            "Precio_Promedio": round(precio_promedio, 2),
            "Precio_Actual": round(precio_actual, 2),
            "Valor_Mercado": round(val_mercado, 2),
            "Ganancia_USD": round(ganancia, 2),
            "Rendimiento_Porc": round(rendimiento, 2),
        })

    ganancia_total = valor_actual - total_invertido
    rendimiento_total = (ganancia_total / total_invertido * 100) if total_invertido > 0 else 0

    return {
        "resumen": {
            "valor_total_portafolio": round(valor_actual, 2),
            "ganancia_total_usd": round(ganancia_total, 2),
            "rendimiento_total_porc": round(rendimiento_total, 2)
        },
        "posiciones": sorted(posiciones, key=lambda x: x["Valor_Mercado"], reverse=True)
    }

@router.get("/trade/history")
def get_history(session: Session = Depends(get_session)):
    hist = session.exec(select(TradeHistory).order_by(TradeHistory.fecha.desc())).all()
    # Convert cents back to dollars for display
    # This might be slow if list is huge, but safe for MVP.
    # Alternatively, frontend handles formatting, but we promised to return dollars.
    # Better to do this in SQL or Pydantic, but manual is explicit.
    res = []
    for h in hist:
        d = h.dict()
        d['precio'] = h.precio / 100.0
        d['total'] = h.total / 100.0
        d['commission'] = h.commission / 100.0
        if h.ganancia_realizada is not None:
             d['ganancia_realizada'] = h.ganancia_realizada / 100.0
        res.append(d)
    return res


 

# --- ENDPOINT PÚBLICO COTIZACIÓN (Recuperado) ---
@router.get("/dolar-uy")
def obtener_cotizacion_endpoint():
    try:
        # Usamos la API pública de Uruguay
        resp = requests.get("https://uy.dolarapi.com/v1/cotizaciones/usd", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "moneda": data.get("moneda", "USD"),
            "compra": data.get("compra", 0),
            "venta": data.get("venta", 0),
            "fecha": data.get("fechaActualizacion", ""),
            "fuente": "DolarApi.com"
        }
    except Exception as e:
        print(f"Error obteniendo dólar: {e}")
        # Fallback manual por si la API falla
        return {
            "compra": 39.0, 
            "venta": 41.0, 
            "fuente": "Backup (Error API)", 
            "error": str(e)
        }