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
    usar_caja_broker: bool = True # Si True, descuenta/suma al saldo del broker

class BrokerFund(BaseModel):
    monto_enviado: float   # <--- Verifica que tengas estos dos nombres exactos
    monto_recibido: float
    tipo: str              # "DEPOSIT" | "WITHDRAW"
# --- AUXILIARES ---
def get_or_create_broker_cash(session: Session) -> BrokerCash:
    cash = session.get(BrokerCash, 1)
    if not cash:
        cash = BrokerCash(id=1, saldo_usd=0.0)
        session.add(cash)
        session.commit()
        session.refresh(cash)
    return cash

def get_dolar_price():
    try:
        resp = requests.get("https://uy.dolarapi.com/v1/cotizaciones/usd", timeout=3)
        return float(resp.json().get('venta', 41.0))
    except:
        return 41.0

# --- ENDPOINTS DE CAJA (BUYING POWER) ---
@router.get("/broker/cash")
def get_broker_cash(session: Session = Depends(get_session)):
    cash = get_or_create_broker_cash(session)
    return {"saldo_usd": cash.saldo_usd}



# ... (Endpoints de Cash y Dolar siguen igual) ...

# 2. ACTUALIZAMOS LA LÓGICA DE FONDEO
@router.post("/broker/fund")
def fund_broker(fund: BrokerFund, session: Session = Depends(get_session)):
    cash = get_or_create_broker_cash(session)
    
    comision = fund.monto_enviado - fund.monto_recibido
    
    if fund.tipo == "DEPOSIT":
        # Aumentamos saldo Broker
        cash.saldo_usd += fund.monto_recibido
        
        # REGISTRO AUTOMÁTICO EN CASH FLOW (Billetera Principal)
        # 1. El dinero que salió de la cuenta (Transferencia)
        gasto_transferencia = Transaction(
            tipo="gasto",
            monto=fund.monto_recibido, # Registramos lo neto como transferencia
            moneda="USD",
            categoria="Transferencia a Broker",
            fecha=datetime.now()
        )
        session.add(gasto_transferencia)

        # 2. Si hubo comisión, la registramos aparte para tener control
        if comision > 0:
            gasto_comision = Transaction(
                tipo="gasto",
                monto=comision,
                moneda="USD",
                categoria="Comisión Broker / Transferencia",
                fecha=datetime.now()
            )
            session.add(gasto_comision)

    elif fund.tipo == "WITHDRAW":
        if cash.saldo_usd < fund.monto_enviado:
            raise HTTPException(status_code=400, detail="Saldo insuficiente en broker")
        
        # Restamos del Broker
        cash.saldo_usd -= fund.monto_enviado # Aquí sale el total
        
        # Ingreso en Cash Flow (Banco)
        ingreso_banco = Transaction(
            tipo="ingreso",
            monto=fund.monto_recibido, # Llega menos por comisión
            moneda="USD",
            categoria="Retiro desde Broker",
            fecha=datetime.now()
        )
        session.add(ingreso_banco)

        if comision > 0:
             # Opcional: Registrar la comisión de salida como gasto o simplemente registrar el ingreso neto
             pass 

    # Guardar Historial de Trading (Solo informativo)
    hist = TradeHistory(
        ticker="CASH", 
        tipo=fund.tipo, 
        cantidad=1, 
        precio=fund.monto_recibido, 
        total=fund.monto_recibido
    )
    session.add(hist)
    session.add(cash)
    session.commit()
    
    return {"nuevo_saldo": cash.saldo_usd, "comision_registrada": comision}

# --- OPERACIONES DE TRADING (BUY / SELL) ---
@router.post("/trade/buy")
def comprar_accion(trade: TradeAction, session: Session = Depends(get_session)):
    # 1. Verificar Caja (si aplica)
    total_costo = trade.cantidad * trade.precio
    if trade.usar_caja_broker:
        cash = get_or_create_broker_cash(session)
        if cash.saldo_usd < total_costo:
            raise HTTPException(status_code=400, detail=f"Saldo insuficiente. Tienes ${cash.saldo_usd:.2f}")
        cash.saldo_usd -= total_costo
        session.add(cash)

    # 2. Actualizar o Crear Activo (Lógica de Promedio Ponderado)
    asset = session.exec(select(Asset).where(Asset.ticker == trade.ticker)).first()
    
    if not asset:
        # Activo Nuevo
        asset = Asset(
            ticker=trade.ticker,
            cantidad_total=trade.cantidad,
            precio_promedio=trade.precio,
            drip_enabled=False
        )
    else:
        # Activo Existente -> Recalcular Precio Promedio
        costo_anterior = asset.cantidad_total * asset.precio_promedio
        nuevo_costo = costo_anterior + total_costo
        nueva_cantidad = asset.cantidad_total + trade.cantidad
        
        asset.cantidad_total = nueva_cantidad
        asset.precio_promedio = nuevo_costo / nueva_cantidad if nueva_cantidad > 0 else 0

    session.add(asset)

    # 3. Guardar en Historial
    hist = TradeHistory(
        ticker=trade.ticker,
        tipo="BUY",
        cantidad=trade.cantidad,
        precio=trade.precio,
        total=total_costo,
        fecha=trade.fecha or datetime.now()
    )
    session.add(hist)
    
    session.commit()
    return {"mensaje": "Compra exitosa", "nuevo_promedio": asset.precio_promedio}

@router.post("/trade/sell")
def vender_accion(trade: TradeAction, session: Session = Depends(get_session)):
    # 1. Verificar si tenemos la acción
    asset = session.exec(select(Asset).where(Asset.ticker == trade.ticker)).first()
    if not asset or asset.cantidad_total < trade.cantidad:
        raise HTTPException(status_code=400, detail="No tienes suficientes acciones para vender")

    total_venta = trade.cantidad * trade.precio
    
    # 2. Calcular Ganancia Realizada (Realized Gain)
    # Asumimos reducción proporcional del costo base (Método Promedio)
    costo_proporcional = trade.cantidad * asset.precio_promedio
    ganancia = total_venta - costo_proporcional

    # 3. Actualizar Activo
    asset.cantidad_total -= trade.cantidad
    
    # Si vendemos todo, borramos el activo o lo dejamos en 0? Mejor dejar en 0 para historial
    if asset.cantidad_total <= 0.00001:
        asset.cantidad_total = 0
        asset.precio_promedio = 0 # Reset
    
    session.add(asset)

    # 4. Actualizar Caja Broker
    if trade.usar_caja_broker:
        cash = get_or_create_broker_cash(session)
        cash.saldo_usd += total_venta
        session.add(cash)

    # 5. Guardar Historial
    hist = TradeHistory(
        ticker=trade.ticker,
        tipo="SELL",
        cantidad=trade.cantidad,
        precio=trade.precio,
        total=total_venta,
        ganancia_realizada=ganancia,
        fecha=trade.fecha or datetime.now()
    )
    session.add(hist)
    
    session.commit()
    return {"mensaje": "Venta exitosa", "ganancia_realizada": ganancia}

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
            "DRIP": row['drip_enabled']
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
    return session.exec(select(TradeHistory).order_by(TradeHistory.fecha.desc())).all()


@router.post("/procesar-drip")
def procesar_drip(session: Session = Depends(get_session)):
    # 1. Obtener activos con DRIP activado
    activos = session.exec(select(Asset).where(Asset.drip_enabled == True)).all()
    cambios = []
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    FECHA_GLOBAL = "2025-12-23"

    for asset in activos:
        try:
            # Lógica de fechas
            fecha_inicio_str = asset.fecha_inicio_drip or FECHA_GLOBAL
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
            
            ultima_rev_str = asset.ultima_revision_div or fecha_inicio_str
            ultima_rev = datetime.strptime(ultima_rev_str, "%Y-%m-%d")
            
            fecha_corte = max(fecha_inicio, ultima_rev)

            # Yahoo Finance
            ticker_data = yf.Ticker(asset.ticker)
            dividends = ticker_data.dividends
            if dividends.empty: continue
            
            dividends.index = dividends.index.tz_localize(None)
            nuevos_divs = dividends[(dividends.index > fecha_corte) & (dividends.index <= hoy)]

            if not nuevos_divs.empty:
                for fecha_div, monto_por_accion in nuevos_divs.items():
                    # Cálculos Financieros
                    div_neto = (monto_por_accion * asset.cantidad_total) * 0.70 # 30% Tax
                    
                    historia = ticker_data.history(start=fecha_div, end=fecha_div + timedelta(days=5))
                    if historia.empty: continue
                    precio_reinversion = float(historia.iloc[0]['Close'])
                    
                    nuevas_acciones = div_neto / precio_reinversion
                    
                    # Actualizar Asset en Memoria
                    costo_anterior = asset.cantidad_total * asset.precio_promedio
                    nuevo_costo = costo_anterior + div_neto
                    asset.cantidad_total += nuevas_acciones
                    if asset.cantidad_total > 0:
                        asset.precio_promedio = nuevo_costo / asset.cantidad_total
                    
                    cambios.append({
                        "Ticker": asset.ticker,
                        "Fecha": fecha_div.strftime("%Y-%m-%d"),
                        "Nuevas": round(nuevas_acciones, 5)
                    })
                
                # Actualizar fecha y guardar en DB
                asset.ultima_revision_div = hoy.strftime("%Y-%m-%d")
                session.add(asset) # Marcar para guardar
                
        except Exception as e:
            print(f"Error DRIP en {asset.ticker}: {e}")

    session.commit() # Guardar todos los cambios
    return {"mensaje": "DRIP procesado", "total_procesados": len(cambios), "cambios": cambios} 

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