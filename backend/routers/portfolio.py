# backend/routers/portfolio.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
import requests
from datetime import datetime
from database import get_session
from models.models import Asset, BrokerCash, TradeHistory
from models.schemas import TradeSchema, TradeAction, BrokerFund, ImportRequest, TransactionDateUpdate
from services.portfolio_service import PortfolioService
from services.market_service import MarketDataService
from services.import_service import ImportService
from utils.money import to_dollars

router = APIRouter(prefix="/api", tags=["portfolio"])

# --- ENDPOINTS DE CAJA (BUYING POWER) ---
@router.get("/broker/cash")
def get_broker_cash(session: Session = Depends(get_session)):
    cash = PortfolioService.get_or_create_broker_cash(session)
    return {"saldo_usd": to_dollars(cash.saldo_usd)}

@router.post("/broker/fund")
def fund_broker(fund: BrokerFund, session: Session = Depends(get_session)):
    return PortfolioService.fund_broker(
        session=session,
        monto_enviado=fund.monto_enviado,
        monto_recibido=fund.monto_recibido,
        tipo=fund.tipo
    )

@router.post("/portfolio/trade")
def execute_trade(trade: TradeSchema, session: Session = Depends(get_session)):
    try:
        trade_date = trade.get_date()
        cantidad = trade.get_quantity()
        precio = trade.get_price()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if trade.type.upper() == "BUY":
        return PortfolioService.execute_buy(
            session=session,
            ticker=trade.ticker,
            cantidad=cantidad,
            precio=precio,
            usar_caja_broker=trade.usar_caja_broker,
            applied_fee=trade.applied_fee,
            fecha=trade_date
        )
    elif trade.type.upper() == "SELL":
        return PortfolioService.execute_sell(
            session=session,
            ticker=trade.ticker,
            cantidad=cantidad,
            precio=precio,
            usar_caja_broker=trade.usar_caja_broker,
            applied_fee=trade.applied_fee,
            fecha=trade_date
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid trade type. Must be BUY or SELL")

@router.patch("/portfolio/transaction/{id}")
def update_transaction_date(id: int, update: TransactionDateUpdate, session: Session = Depends(get_session)):
    tx = session.get(TradeHistory, id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tx.fecha = update.date
    session.add(tx)
    session.commit()
    
    return {"status": "success", "message": "Transaction date updated", "new_date": tx.fecha}

# --- OPERACIONES DE TRADING (BUY / SELL) - SOPORTE COMPATIBILIDAD ---
@router.post("/trade/buy")
def comprar_accion(trade: TradeAction, session: Session = Depends(get_session)):
    return PortfolioService.execute_buy(
        session=session,
        ticker=trade.ticker,
        cantidad=trade.cantidad,
        precio=trade.precio,
        usar_caja_broker=trade.usar_caja_broker,
        applied_fee=trade.applied_fee,
        fecha=trade.fecha
    )

@router.post("/trade/sell")
def vender_accion(trade: TradeAction, session: Session = Depends(get_session)):
    return PortfolioService.execute_sell(
        session=session,
        ticker=trade.ticker,
        cantidad=trade.cantidad,
        precio=trade.precio,
        usar_caja_broker=trade.usar_caja_broker,
        applied_fee=trade.applied_fee,
        fecha=trade.fecha
    )

@router.post("/portfolio/import")
def import_snapshot(request: ImportRequest, session: Session = Depends(get_session)):
    try:
        return ImportService.import_snapshot(session, request.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/portfolio/transaction/{id}")
def delete_transaction(id: int, session: Session = Depends(get_session)):
    tx = session.get(TradeHistory, id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    ticker = tx.ticker
    session.delete(tx)
    session.commit()
    
    if ticker and ticker != "CASH":
        PortfolioService.recalculate_asset_from_history(session, ticker)
    
    return {"status": "success", "message": "Transaction deleted and asset recalculated via chronological replay"}

@router.get("/portfolio")
def obtener_portafolio(session: Session = Depends(get_session)):
    activos_db = session.exec(select(Asset).where(Asset.cantidad_total > 0)).all()
    if not activos_db:
        return {"resumen": {"valor_total_portafolio": 0, "ganancia_total_usd": 0, "rendimiento_total_porc": 0}, "posiciones": []}

    prices_map = MarketDataService.get_market_prices(session, activos_db)
    
    posiciones = []
    total_invertido = 0.0
    valor_actual = 0.0
    
    for asset in activos_db:
        price_cents = prices_map.get(asset.ticker, 0)
        precio_actual = to_dollars(price_cents)
        precio_promedio = to_dollars(asset.precio_promedio)
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
    res = []
    for h in hist:
        d = h.dict()
        d['precio'] = to_dollars(h.precio)
        d['total'] = to_dollars(h.total)
        d['commission'] = to_dollars(h.commission)
        if h.ganancia_realizada is not None:
            d['ganancia_realizada'] = to_dollars(h.ganancia_realizada)
        res.append(d)
    return res

# --- ENDPOINT PÚBLICO COTIZACIÓN DÓLAR ---
@router.get("/dolar-uy")
def obtener_cotizacion_endpoint():
    try:
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
        return {
            "compra": 39.0, 
            "venta": 41.0, 
            "fuente": "Backup (Error API)", 
            "error": str(e)
        }