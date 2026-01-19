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

# --- OPERACIONES DE TRADING (BUY / SELL) ---
@router.post("/trade/buy")
def comprar_accion(trade: TradeAction, session: Session = Depends(get_session)):
    # Delegar lógica compleja al servicio
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


# --- GETTERS ---
@router.get("/portfolio")
def obtener_portafolio(session: Session = Depends(get_session)):
    # ... (Tu código anterior de obtener_portafolio, MANTENLO IGUAL) ...
    # Solo agrega al principio para incluir el saldo en caja si quieres retornarlo aqui tambien
    # Pero idealmente el Dashboard lo pide por separado.
    # COPIA AQUI TU LOGICA DE OBTENER_PORTAFOLIO QUE YA TENIAS EN EL MENSAJE ANTERIOR
    # O SI QUIERES TE LA PEGO DE NUEVO COMPLETA ABAJO
    
    activos_db = session.exec(select(Asset).where(Asset.cantidad_total > 0)).all() # Filtramos los que estan en 0
    if not activos_db:
         return {"resumen": {"valor_total_portafolio": 0, "ganancia_total_usd": 0, "rendimiento_total_porc": 0}, "posiciones": []}

    data = [asset.dict() for asset in activos_db]
    df = pd.DataFrame(data)
    
    # CONVERTIR CENTS A DOLLARS para cálculos de visualización
    # precio_promedio viene en Cents desde DB
    df['precio_promedio'] = df['precio_promedio'] / 100.0

    lista_tickers = df['ticker'].unique().tolist()
    precios_actuales = pd.Series()
    
    if lista_tickers:
        try:
            datos_mercado = yf.download(lista_tickers, period="1d", threads=True)['Close']
            precios_actuales = datos_mercado.iloc[-1] if not datos_mercado.empty else pd.Series()
        except: pass

    def get_precio_live(ticker):
        try:
            if isinstance(precios_actuales, pd.Series): return float(precios_actuales.get(ticker, 0))
            return float(precios_actuales) if lista_tickers[0] == ticker else 0.0
        except: return 0.0

    df['Precio_Actual'] = df['ticker'].apply(get_precio_live).fillna(0)
    df['Valor_Mercado'] = df['cantidad_total'] * df['Precio_Actual']
    
    # Costo Base (Dollars) = Cantidad * PrecioPromedio(Dollars)
    df['Costo_Base'] = df['cantidad_total'] * df['precio_promedio']
    
    df['Ganancia_USD'] = df['Valor_Mercado'] - df['Costo_Base']
    df['Rendimiento_Porc'] = df.apply(lambda x: (x['Ganancia_USD'] / x['Costo_Base'] * 100) if x['Costo_Base'] > 0 else 0, axis=1)

    total_invertido = df['Costo_Base'].sum()
    valor_actual = df['Valor_Mercado'].sum()
    ganancia_total = valor_actual - total_invertido
    rendimiento_total = (ganancia_total / total_invertido * 100) if total_invertido > 0 else 0

    posiciones = []
    for _, row in df.iterrows():
        posiciones.append({
            "Ticker": row['ticker'],
            "Cantidad_Total": round(float(row['cantidad_total']), 5),
            "Precio_Promedio": round(float(row['precio_promedio']), 2),
            "Precio_Actual": round(float(row['Precio_Actual']), 2),
            "Valor_Mercado": round(float(row['Valor_Mercado']), 2),
            "Ganancia_USD": round(float(row['Ganancia_USD']), 2),
            "Rendimiento_Porc": round(float(row['Rendimiento_Porc']), 2),

        })

    return {
        "resumen": {
            "valor_total_portafolio": round(float(valor_actual), 2),
            "ganancia_total_usd": round(float(ganancia_total), 2),
            "rendimiento_total_porc": round(float(rendimiento_total), 2)
        },
        "posiciones": posiciones
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