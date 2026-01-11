from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import yfinance as yf
import pandas as pd
from database import get_session
from models.models import Asset, Transaction
from .portfolio import get_dolar_price # Reutilizamos la función del dólar

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("")
def obtener_dashboard(session: Session = Depends(get_session)):
    try:
        # 1. Cotización Dólar
        dolar_val = get_dolar_price()

        # 2. Efectivo (Desde DB)
        movimientos = session.exec(select(Transaction)).all()
        total_cash_usd = 0.0
        total_cash_uyu = 0.0

        for m in movimientos:
            monto = float(m.monto)
            if m.tipo == 'gasto': monto = -monto
            
            if m.moneda == 'USD': total_cash_usd += monto
            else: total_cash_uyu += monto
        
        cash_equivalent = total_cash_usd + (total_cash_uyu / dolar_val if dolar_val > 0 else 0)

        # 3. Inversiones (Desde DB + Yahoo)
        activos = session.exec(select(Asset)).all()
        investments_total = 0.0
        investments_performance = 0.0
        
        if activos:
            df = pd.DataFrame([a.dict() for a in activos])
            tickers = df['ticker'].unique().tolist()
            if tickers:
                data = yf.download(tickers, period="1d", threads=True)['Close']
                current_prices = data.iloc[-1] if not data.empty else pd.Series()
                
                for asset in activos:
                    try:
                        # Obtener precio
                        if isinstance(current_prices, pd.Series):
                            price = float(current_prices.get(asset.ticker, 0))
                        else:
                            price = float(current_prices) if tickers[0] == asset.ticker else 0.0
                        
                        val_mercado = asset.cantidad_total * price
                        costo_base = asset.cantidad_total * asset.precio_promedio
                        
                        investments_total += val_mercado
                        investments_performance += (val_mercado - costo_base)
                    except:
                        pass

        # 4. Totales
        net_worth = cash_equivalent + investments_total
        base_invested = net_worth - investments_performance
        perc = (investments_performance / base_invested * 100) if base_invested > 0 else 0.0

        return {
            "net_worth": round(float(net_worth), 2),
            "performance": {
                "value": round(float(investments_performance), 2),
                "percentage": round(float(perc), 2),
                "isPositive": bool(investments_performance >= 0)
            },
            "assets": [
                {"id": "s1", "name": "Bolsa", "category": "Stock", "amount": round(float(investments_total), 2)},
                {"id": "c1", "name": "Caja", "category": "Cash", "amount": round(float(cash_equivalent), 2)}
            ],
            "chart_data": [
                {"name": "Bolsa", "value": round(float(investments_total), 2), "color": "#3b82f6"},
                {"name": "Efectivo", "value": round(float(cash_equivalent), 2), "color": "#10b981"}
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))