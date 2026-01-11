from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from database import get_session
from models.models import Asset

router = APIRouter(prefix="/api", tags=["portfolio"])

# --- FUNCIONES AUXILIARES ---
def get_dolar_price():
    """Obtiene precio del dólar (Venta) de DolarAPI o fallback"""
    try:
        resp = requests.get("https://uy.dolarapi.com/v1/cotizaciones/usd", timeout=3)
        data = resp.json()
        return float(data.get('venta', 41.0))
    except:
        return 41.0 # Fallback manual

@router.get("/dolar-uy")
def obtener_cotizacion_endpoint():
    try:
        resp = requests.get("https://uy.dolarapi.com/v1/cotizaciones/usd", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return {
            "moneda": data.get("moneda"),
            "compra": data.get("compra"),
            "venta": data.get("venta"),
            "fecha": data.get("fechaActualizacion"),
            "fuente": "DolarApi.com"
        }
    except Exception as e:
        return {"compra": 39.0, "venta": 41.0, "fuente": "Backup", "error": str(e)}

@router.get("/portfolio")
def obtener_portafolio(session: Session = Depends(get_session)):
    # 1. Leer Activos de la DB
    activos_db = session.exec(select(Asset)).all()
    if not activos_db:
        return {"resumen": {"valor_total_portafolio": 0, "ganancia_total_usd": 0, "rendimiento_total_porc": 0}, "posiciones": []}

    # 2. Convertir a DataFrame para procesar igual que antes
    data = [asset.dict() for asset in activos_db]
    df = pd.DataFrame(data)
    
    # 3. Yahoo Finance Batch Download
    lista_tickers = df['ticker'].unique().tolist()
    if lista_tickers:
        datos_mercado = yf.download(lista_tickers, period="1d", threads=True)['Close']
        precios_actuales = datos_mercado.iloc[-1] if not datos_mercado.empty else pd.Series()
    else:
        precios_actuales = pd.Series()

    def get_precio_live(ticker):
        try:
            if isinstance(precios_actuales, pd.Series):
                val = precios_actuales.get(ticker, 0)
                return float(val)
            else:
                return float(precios_actuales) if lista_tickers[0] == ticker else 0.0
        except:
            return 0.0

    # 4. Cálculos
    df['Precio_Actual'] = df['ticker'].apply(get_precio_live).fillna(0)
    df['Valor_Mercado'] = df['cantidad_total'] * df['Precio_Actual']
    df['Costo_Base'] = df['cantidad_total'] * df['precio_promedio']
    df['Ganancia_USD'] = df['Valor_Mercado'] - df['Costo_Base']
    df['Rendimiento_Porc'] = df.apply(lambda x: (x['Ganancia_USD'] / x['Costo_Base'] * 100) if x['Costo_Base'] > 0 else 0, axis=1)

    # 5. Formato Final
    total_invertido = df['Costo_Base'].sum()
    valor_actual = df['Valor_Mercado'].sum()
    ganancia_total = valor_actual - total_invertido
    rendimiento_total = (ganancia_total / total_invertido * 100) if total_invertido > 0 else 0

    # Mapeo para frontend (respetando mayúsculas que espera tu React)
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