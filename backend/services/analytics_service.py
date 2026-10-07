import pandas as pd
import yfinance as yf
import numpy as np
from sqlmodel import Session, select
from models.models import TradeHistory
import warnings
from services.cache import TTLCache

# Ignorar FutureWarnings de yfinance y pandas
warnings.simplefilter(action='ignore', category=FutureWarning)

_analytics_prices_cache = TTLCache(maxsize=50, ttl_seconds=3600)
_sp500_cache = TTLCache(maxsize=20, ttl_seconds=3600)

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
        
        cache_key = (tuple(sorted(tickers_list)), start_date_str, end_date_str)
        cached_prices = _analytics_prices_cache.get(cache_key)
        if cached_prices is not None:
            precios_mercado = cached_prices
        else:
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
                precios_mercado = pd.DataFrame(index=rango_fechas, columns=tickers_list)

            # Blindaje contra fallos de red: Para cualquier ticker sin datos válidos, recurrir a la DB en vez de descartarlo
            from models.models import Asset
            db_assets = {a.ticker: a for a in session.exec(select(Asset)).all()}
            for tc in tickers_list:
                if tc not in precios_mercado.columns or precios_mercado[tc].isna().all() or (precios_mercado[tc] == 0).all():
                    db_a = db_assets.get(tc)
                    fallback_p = 0.0
                    if db_a:
                        fallback_p = (db_a.cached_price / 100.0) if db_a.cached_price else ((db_a.precio_promedio / 100.0) if db_a.precio_promedio else 0.0)
                    if fallback_p <= 0:
                        last_tx = df_tx[df_tx['ticker'] == tc]
                        if not last_tx.empty:
                            fallback_p = float(last_tx.iloc[-1]['precio'])
                    precios_mercado[tc] = fallback_p

            precios_mercado = precios_mercado.ffill().bfill().fillna(0)
            _analytics_prices_cache.set(cache_key, precios_mercado)

        common_tickers = df_pos_diario.columns.intersection(precios_mercado.columns)
        df_pos_diario = df_pos_diario[common_tickers]
        precios_mercado = precios_mercado[common_tickers]

        # Calcular el costo base diario por ticker respetando la regla contable de costo promedio
        cost_basis_by_ticker = {}
        for ticker in common_tickers:
            txs_ticker = df_tx[df_tx['ticker'] == ticker].sort_values('fecha')
            shares = 0.0
            total_cost = 0.0
            daily_cost = {}
            for _, tx in txs_ticker.iterrows():
                dt = tx['fecha'].normalize()
                qty = float(tx['cantidad'])
                price = float(tx['precio'])
                if tx['operacion'] == 'Compra':
                    total_cost += qty * price
                    shares += qty
                else:
                    if shares > 0:
                        avg_price = total_cost / shares
                        shares = max(0.0, shares - qty)
                        total_cost = shares * avg_price
                    else:
                        shares = 0.0
                        total_cost = 0.0
                daily_cost[dt] = total_cost

            s_cost = pd.Series(daily_cost).reindex(rango_fechas).ffill().fillna(0.0)
            cost_basis_by_ticker[ticker] = s_cost

        df_cost_basis = pd.DataFrame(cost_basis_by_ticker, index=rango_fechas)
        df_capital['capital_invertido'] = df_cost_basis.sum(axis=1) if not df_cost_basis.empty else 0.0
            
        # Calcular valor sumado ($ valor_mercado)
        valor_por_ticker = df_pos_diario * precios_mercado
        valor_por_ticker = valor_por_ticker.fillna(0)
        df_capital['valor_mercado'] = valor_por_ticker.sum(axis=1)
        # Flujos de caja diarios hacia el portafolio de activos para TWR institucional
        from utils.money import to_dollars as _to_dollars
        daily_asset_flows = {}
        for t in trades:
            fecha_key = pd.to_datetime(t.fecha).normalize()
            if hasattr(fecha_key, 'tz') and fecha_key.tz is not None:
                fecha_key = fecha_key.tz_localize(None)
            total_dollars = _to_dollars(t.total)
            if t.tipo == "DIVIDEND":
                daily_asset_flows[fecha_key] = daily_asset_flows.get(fecha_key, 0.0) - abs(total_dollars)
            elif t.tipo == "BUY":
                daily_asset_flows[fecha_key] = daily_asset_flows.get(fecha_key, 0.0) + abs(total_dollars)
            elif t.tipo == "SELL":
                daily_asset_flows[fecha_key] = daily_asset_flows.get(fecha_key, 0.0) - abs(total_dollars)

        # Calcular TWR acumulado continuo día a día (estándar institucional)
        twr_series = []
        compound = 1.0
        has_started = False
        v_prev = 0.0

        for dt in rango_fechas:
            v_end = round(float(df_capital.loc[dt, 'valor_mercado']), 2)
            flow = daily_asset_flows.get(dt, 0.0)

            if not has_started:
                if v_end > 0:
                    has_started = True
                    v_prev = v_end
                twr_series.append(0.0)
                continue

            if v_prev <= 0 and v_end > 0:
                v_prev = v_end
                twr_series.append(round((compound - 1.0) * 100.0, 2))
                continue

            if v_prev > 0:
                r_t = (v_end - flow) / v_prev
                if 0.01 < r_t < 10.0:
                    compound *= r_t

            v_prev = v_end
            twr_series.append(round((compound - 1.0) * 100.0, 2))

        df_capital['pct_portafolio'] = twr_series

        # Guardar también el porcentaje de ganancia no realizada puntual
        def safe_unrealized_pct(row):
            ci = row['capital_invertido']
            vm = row['valor_mercado']
            if ci > 0:
                return ((vm - ci) / ci) * 100.0
            return 0.0

        df_capital['unrealized_pct'] = df_capital.apply(safe_unrealized_pct, axis=1)
        
        # Step 3: S&P 500 Synchronization
        sp_cache_key = (start_date_str, end_date_str)
        cached_sp500 = _sp500_cache.get(sp_cache_key)
        if cached_sp500 is not None:
            sp500_diario = cached_sp500
        else:
            try:
                sp500 = yf.download('^GSPC', start=start_date_str, end=end_date_str, progress=False)
                if not sp500.empty:
                    if sp500.index.tz is not None:
                        sp500.index = sp500.index.tz_localize(None)
                    sp500.index = sp500.index.normalize()
                    
                    sp500_close = sp500['Close']
                    if isinstance(sp500_close, pd.DataFrame):
                        sp500_close = sp500_close.iloc[:, 0]

                    sp500_diario = pd.DataFrame(index=rango_fechas)
                    sp500_diario['SP500_Close'] = sp500_close
                    sp500_diario = sp500_diario.ffill().bfill()
                    
                    precio_dia_1 = float(sp500_diario['SP500_Close'].iloc[0])
                    if precio_dia_1 > 0:
                        sp500_diario['pct_sp500'] = ((sp500_diario['SP500_Close'] - precio_dia_1) / precio_dia_1) * 100
                        sp500_diario.iloc[0, sp500_diario.columns.get_loc('pct_sp500')] = 0.0
                    else:
                        sp500_diario['pct_sp500'] = 0.0
                    _sp500_cache.set(sp_cache_key, sp500_diario)
                else:
                    sp500_diario = pd.DataFrame(index=rango_fechas)
                    sp500_diario['pct_sp500'] = 0.0
            except Exception:
                sp500_diario = pd.DataFrame(index=rango_fechas)
                sp500_diario['pct_sp500'] = 0.0

        if 'pct_sp500' in df_capital.columns:
            df_capital['pct_sp500'] = sp500_diario['pct_sp500'].values
        else:
            df_capital = df_capital.join(sp500_diario[['pct_sp500']])
            
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
                "unrealized_pct": round(float(row.get('unrealized_pct', 0.0)), 2),
                "hubo_transaccion": fecha_str in fechas_transaccion
            })
            
        return result
