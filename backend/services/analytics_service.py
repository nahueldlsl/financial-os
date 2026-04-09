import pandas as pd
import yfinance as yf
import numpy as np
from sqlmodel import Session, select
from models.models import TradeHistory
import warnings

# Ignorar FutureWarnings de yfinance y pandas
warnings.simplefilter(action='ignore', category=FutureWarning)

class AnalyticsService:
    @staticmethod
    def get_portfolio_history(session: Session):
        # 1. Fetch transactions
        trades = session.exec(select(TradeHistory).order_by(TradeHistory.fecha.asc())).all()
        if not trades:
            return []
        
        # Convert to dicts
        trades_data = []
        for t in trades:
            trades_data.append({
                "ticker": t.ticker,
                "fecha": t.fecha,
                "precio": float(t.precio) / 100.0,
                "cantidad": float(t.cantidad),
                "operacion": "Compra" if t.tipo == "BUY" else "Venta",
                "total_dollars": float(t.total) / 100.0
            })
            
        df_tx = pd.DataFrame(trades_data)
        df_tx['fecha'] = pd.to_datetime(df_tx['fecha'])
        df_tx = df_tx.sort_values('fecha')
        
        # Efectivo Invertido (solo cuenta dinero que sale o entra por operaciones netas)
        df_tx['flujo_caja'] = df_tx.apply(
            lambda r: r['total_dollars'] if r['operacion'] == 'Compra' else -r['total_dollars'], axis=1
        )
        
        inception_date = df_tx['fecha'].min().normalize()
        if hasattr(inception_date, 'tz') and inception_date.tz is not None:
            inception_date = inception_date.tz_localize(None)
        today = pd.Timestamp.today().normalize()
        rango_fechas = pd.date_range(start=inception_date, end=today, freq='D')
        
        # 3. Capital Invertido Acumulado
        df_capital = df_tx.groupby(df_tx['fecha'].dt.normalize())['flujo_caja'].sum().reset_index()
        df_capital = df_capital.set_index('fecha')
        df_capital = df_capital.reindex(rango_fechas, fill_value=0)
        df_capital['capital_invertido'] = df_capital['flujo_caja'].cumsum()
        
        # 4. Matriz de Posiciones (Cantidad diaria)
        df_pos = df_tx.copy()
        df_pos['cantidad_ajustada'] = df_pos.apply(
            lambda r: r['cantidad'] if r['operacion'] == 'Compra' else -r['cantidad'], axis=1
        )
        
        df_pos_pivot = df_pos.groupby([df_pos['fecha'].dt.normalize(), 'ticker'])['cantidad_ajustada'].sum().unstack(fill_value=0)
        df_pos_diario = df_pos_pivot.reindex(rango_fechas, fill_value=0).cumsum()
        
        # 5. yfinance Prices
        tickers_list = df_pos_diario.columns.tolist()
        if not tickers_list:
            return []
            
        end_date_str = (today + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        start_date_str = inception_date.strftime('%Y-%m-%d')
        
        try:
            precios_mercado = yf.download(tickers_list, start=start_date_str, end=end_date_str, group_by='ticker', auto_adjust=False, progress=False)
            
            if len(tickers_list) == 1:
                tc = tickers_list[0]
                df_prices = pd.DataFrame(index=precios_mercado.index)
                df_prices[tc] = precios_mercado['Close']
                precios_mercado = df_prices
            else:
                precios_mercado = precios_mercado.loc[:, (slice(None), 'Close')]
                precios_mercado.columns = precios_mercado.columns.droplevel(1)
            
            # Quitar tz data
            if precios_mercado.index.tz is not None:
                precios_mercado.index = precios_mercado.index.tz_localize(None)
            precios_mercado.index = precios_mercado.index.normalize()
            
            precios_mercado = precios_mercado.reindex(rango_fechas).ffill().bfill() 
        except Exception as e:
            precios_mercado = pd.DataFrame(index=rango_fechas, columns=tickers_list).fillna(0)

        # FIX-2: Eliminar tickers sin ningún dato de precio válido (NaN propagation guard)
        valid_tickers = precios_mercado.columns[precios_mercado.notna().any()]
        invalid_tickers = set(precios_mercado.columns) - set(valid_tickers)
        if invalid_tickers:
            print(f"⚠️ Tickers sin datos de precio (excluidos del cálculo): {invalid_tickers}")
        precios_mercado = precios_mercado[valid_tickers]
        # Alinear posiciones diarias con los tickers válidos
        common_tickers = df_pos_diario.columns.intersection(valid_tickers)
        df_pos_diario = df_pos_diario[common_tickers]
        precios_mercado = precios_mercado[common_tickers]
            
        # Calcular valor sumado ($ valor_mercado)
        valor_por_ticker = df_pos_diario * precios_mercado
        valor_por_ticker = valor_por_ticker.fillna(0)
        df_capital['valor_mercado'] = valor_por_ticker.sum(axis=1)
        
        # FIX-1: Rentabilidad Porcentual con protección contra división por cero
        def safe_pct(row):
            ci = row['capital_invertido']
            vm = row['valor_mercado']
            if ci <= 0:
                # Capital neto <= 0: Si aún hay valor, cap al 100% (ganancia total)
                if vm > 0:
                    return 100.0
                return 0.0
            return ((vm - ci) / ci) * 100

        df_capital['pct_portafolio'] = df_capital.apply(safe_pct, axis=1)

        # Forzar Day 1 to be exactly 0%
        if len(df_capital) > 0:
            df_capital.iloc[0, df_capital.columns.get_loc('pct_portafolio')] = 0.0

        # FIX-6: Post-liquidación — congelar pct al último valor válido
        last_valid_pct = 0.0
        pct_col_idx = df_capital.columns.get_loc('pct_portafolio')
        for i in range(len(df_capital)):
            ci = df_capital.iloc[i]['capital_invertido']
            vm = df_capital.iloc[i]['valor_mercado']
            if ci > 0:
                last_valid_pct = df_capital.iloc[i]['pct_portafolio']
            elif vm == 0 and ci <= 0 and i > 0:
                df_capital.iloc[i, pct_col_idx] = last_valid_pct
        
        # Step 3: S&P 500 Synchronization
        try:
            sp500 = yf.download('^GSPC', start=start_date_str, end=end_date_str, progress=False)
            if not sp500.empty:
                if sp500.index.tz is not None:
                    sp500.index = sp500.index.tz_localize(None)
                sp500.index = sp500.index.normalize()
                
                sp500_diario = pd.DataFrame(index=rango_fechas)
                sp500_diario['SP500_Close'] = sp500['Close']
                sp500_diario = sp500_diario.ffill().bfill()
                
                precio_dia_1 = sp500_diario['SP500_Close'].iloc[0]
                sp500_diario['pct_sp500'] = ((sp500_diario['SP500_Close'] - precio_dia_1) / precio_dia_1) * 100
                sp500_diario.iloc[0, sp500_diario.columns.get_loc('pct_sp500')] = 0.0
                
                df_capital = df_capital.join(sp500_diario[['pct_sp500']])
            else:
                df_capital['pct_sp500'] = 0.0
        except Exception:
            df_capital['pct_sp500'] = 0.0
            
        df_capital['pct_sp500'] = df_capital['pct_sp500'].fillna(0)
        df_capital.index.name = 'fecha'
        df_final = df_capital.reset_index()
        
        fechas_transaccion = set(df_tx['fecha'].dt.normalize().dt.strftime('%Y-%m-%d'))
        
        result = []
        for _, row in df_final.iterrows():
            fecha_str = row['fecha'].strftime('%Y-%m-%d')
            result.append({
                "fecha": fecha_str,
                "capital_invertido": round(float(row['capital_invertido']), 2),
                "valor_mercado": round(float(row['valor_mercado']), 2),
                "pct_portafolio": round(float(row['pct_portafolio']), 2),
                "pct_sp500": round(float(row['pct_sp500']), 2),
                "hubo_transaccion": fecha_str in fechas_transaccion
            })
            
        return result
