from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import yfinance as yf
import pandas as pd
import math # <--- Necesario para detectar NaN
from database import get_session
from models.models import Asset, Transaction, BrokerCash
from .portfolio import get_dolar_price

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# --- FUNCIÓN DE SEGURIDAD ---
def safe_float(val):
    """Convierte NaNs e Infinitos a 0.0 para que no rompan el JSON"""
    try:
        if val is None:
            return 0.0
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except:
        return 0.0

@router.get("")
def obtener_dashboard(session: Session = Depends(get_session)):
    try:
        # 1. Cotización Dólar
        dolar_val = safe_float(get_dolar_price())

        # 2. Efectivo Billetera (Cash Flow)
        movimientos = session.exec(select(Transaction)).all()
        total_wallet_usd = 0.0
        total_wallet_uyu = 0.0

        for m in movimientos:
            monto = safe_float(m.monto)
            if m.tipo == 'gasto': monto = -monto
            
            if m.moneda == 'USD': total_wallet_usd += monto
            else: total_wallet_uyu += monto
        
        wallet_equivalent = total_wallet_usd + (total_wallet_uyu / dolar_val if dolar_val > 0 else 0)

        # 3. Efectivo Broker (Buying Power)
        broker_cash_obj = session.get(BrokerCash, 1)
        broker_cash_val = safe_float(broker_cash_obj.saldo_usd) if broker_cash_obj else 0.0

        # 4. Inversiones (Stocks)
        activos = session.exec(select(Asset)).all()
        investments_total = 0.0
        investments_performance = 0.0
        
        if activos:
            df = pd.DataFrame([a.dict() for a in activos])
            tickers = df['ticker'].unique().tolist()
            if tickers:
                try:
                    # Descargamos datos
                    data = yf.download(tickers, period="1d", threads=True)['Close']
                    
                    # Extraer última fila de precios
                    current_prices = data.iloc[-1] if not data.empty else pd.Series()
                    
                    for asset in activos:
                        try:
                            # Obtener precio de la Serie de Pandas de forma segura
                            raw_price = 0.0
                            if isinstance(current_prices, pd.Series):
                                # Si el ticker está en la serie, lo tomamos
                                if asset.ticker in current_prices:
                                    raw_price = current_prices[asset.ticker]
                            else:
                                # Caso borde: un solo ticker devuelve un valor escalar a veces
                                if tickers[0] == asset.ticker:
                                    raw_price = current_prices
                            
                            price = safe_float(raw_price)
                            
                            # Cálculos por activo
                            cantidad = safe_float(asset.cantidad_total)
                            precio_promedio = safe_float(asset.precio_promedio)

                            val_mercado = cantidad * price
                            costo_base = cantidad * precio_promedio
                            
                            investments_total += val_mercado
                            investments_performance += (val_mercado - costo_base)
                        except Exception as e_inner:
                            print(f"Error procesando activo {asset.ticker}: {e_inner}")
                            continue
                except Exception as e_yf:
                    print(f"Error descargando Yahoo Finance: {e_yf}")

        # 5. TOTALES UNIFICADOS
        wallet_safe = safe_float(wallet_equivalent)
        broker_safe = safe_float(broker_cash_val)
        investments_safe = safe_float(investments_total)
        performance_safe = safe_float(investments_performance)

        # Net Worth = Billetera + Broker + Acciones
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

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))