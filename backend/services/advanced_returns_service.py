"""
Pilar 2: Advanced Returns Service
Matemáticas Avanzadas — IRR (XIRR) y TWR con benchmark S&P 500.

IRR:
  Tasa Interna de Retorno calculada con XIRR (Newton-Raphson).
  Usa los flujos de caja reales (compras, ventas, dividendos, depósitos, retiros)
  con sus fechas, y el valor actual del portafolio como flujo final positivo.

TWR:
  Time-Weighted Return calculado subdividiendo el portafolio en sub-períodos
  cada vez que hay un flujo de caja externo, y multiplicando geométricamente.
  Se aplica la misma fórmula al S&P 500 para benchmark justo.
"""

import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

import pandas as pd
import numpy as np
import yfinance as yf
from sqlmodel import Session, select

from models.models import Asset, TradeHistory
from services.market_service import MarketDataService


def _safe_float(val) -> float:
    try:
        if val is None:
            return 0.0
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except Exception:
        return 0.0


def _to_dollars(cents) -> float:
    return _safe_float(cents) / 100.0


class AdvancedReturnsService:

    # ═══════════════════════════════════════════════
    #  IRR (XIRR) — Newton-Raphson
    # ═══════════════════════════════════════════════

    @staticmethod
    def calculate_xirr(
        cashflows: List[Tuple[datetime, float]],
        guess: float = 0.1,
        tol: float = 1e-6,
        max_iter: int = 200
    ) -> Optional[float]:
        """
        Calcula la Tasa Interna de Retorno Extendida (XIRR).

        cashflows: Lista de tuplas (fecha, monto_en_dolares)
                   - Negativo = dinero que SALE (compras, depósitos)
                   - Positivo = dinero que ENTRA (ventas, dividendos, valor actual)

        Fórmula:
            f(r) = Σ [CFi / (1+r)^((di - d0) / 365)] = 0

        Usa Newton-Raphson para resolver iterativamente.
        """
        if not cashflows or len(cashflows) < 2:
            return None

        # Ordenar por fecha
        cashflows = sorted(cashflows, key=lambda x: x[0])
        d0 = cashflows[0][0]

        # Convertir fechas a años fraccionarios
        years = [(cf[0] - d0).days / 365.0 for cf in cashflows]
        amounts = [cf[1] for cf in cashflows]

        # Validar que hay al menos un flujo positivo y uno negativo
        has_positive = any(a > 0 for a in amounts)
        has_negative = any(a < 0 for a in amounts)
        if not has_positive or not has_negative:
            return None

        rate = guess

        for _ in range(max_iter):
            # f(r) = Σ [CF_i * (1+r)^(-t_i)]
            f_val = 0.0
            f_deriv = 0.0

            for i in range(len(amounts)):
                t = years[i]
                cf = amounts[i]

                # Protección contra (1+r) negativo
                base = 1.0 + rate
                if base <= 0:
                    rate = rate / 2.0 + 0.01
                    base = 1.0 + rate

                try:
                    discount = base ** (-t)
                    f_val += cf * discount
                    # f'(r) = Σ [-t_i * CF_i * (1+r)^(-t_i - 1)]
                    f_deriv += -t * cf * (base ** (-t - 1))
                except (OverflowError, ZeroDivisionError):
                    return None

            # Newton-Raphson step
            if abs(f_deriv) < 1e-12:
                # Derivada casi cero — no podemos avanzar
                break

            new_rate = rate - f_val / f_deriv

            # Convergencia
            if abs(new_rate - rate) < tol:
                # Sanity check: IRR debería estar entre -95% y +1000%
                if -0.95 <= new_rate <= 10.0:
                    return round(new_rate * 100, 2)  # Retornar como porcentaje
                return None

            rate = new_rate

            # Bound check para evitar divergencia
            if rate < -0.95:
                rate = -0.90
            elif rate > 10.0:
                rate = 5.0

        # No convergió
        return None

    # ═══════════════════════════════════════════════
    #  TWR (Time-Weighted Return)
    # ═══════════════════════════════════════════════

    @staticmethod
    def calculate_twr(
        daily_values: List[dict]
    ) -> Optional[float]:
        """
        Calcula el TWR del Portafolio de Activos.
        Formula: Rt = (V_fin - Flows) / V_inicio
        """
        if not daily_values or len(daily_values) < 2:
            return None

        sorted_days = sorted(daily_values, key=lambda x: x["fecha"])
        compound = 1.0
        has_started = False
        v_prev = 0.0

        for day in sorted_days:
            v_end = day["asset_value"]
            flow = day["net_flow"] # Capital in/out of the asset bucket (BUY - SELL)

            if not has_started:
                if v_end > 0:
                    has_started = True
                    v_prev = v_end
                continue
            
            # Si v_prev es 0 pero hubo un flujo hoy (ej: primera compra tras venta total)
            if v_prev <= 0 and v_end > 0:
                v_prev = v_end
                continue

            if v_prev > 0:
                # Retorno diario aislando el flujo
                # Si hoy compraste $1000, ese salto no es rentabilidad.
                r_t = (v_end - flow) / v_prev
                # Clipping de seguridad (un retorno de >1000% o <-90% diario suele ser error de datos)
                if 0.01 < r_t < 10.0:
                    compound *= r_t
            
            v_prev = v_end

        twr = (compound - 1) * 100
        return round(twr, 2)

    # ═══════════════════════════════════════════════
    #  TWR S&P 500 (Benchmark)
    # ═══════════════════════════════════════════════

    @staticmethod
    def calculate_sp500_twr(start_date: datetime, end_date: datetime) -> Optional[float]:
        """
        Calcula el TWR del S&P 500 en la misma ventana temporal.
        Simple: (Precio_Final / Precio_Inicio - 1) * 100

        Para el S&P no hay flujos de caja, así que TWR = HPR.
        """
        try:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')

            sp500 = yf.download('^GSPC', start=start_str, end=end_str, progress=False)

            if sp500.empty:
                return None

            close_col = sp500['Close']
            if isinstance(close_col, pd.DataFrame):
                close_col = close_col.iloc[:, 0]

            first_price = float(close_col.iloc[0])
            last_price = float(close_col.iloc[-1])

            if first_price <= 0:
                return None

            twr_sp500 = ((last_price / first_price) - 1) * 100
            return round(twr_sp500, 2)

        except Exception as e:
            print(f"Error calculando TWR S&P 500: {e}")
            return None

    # ═══════════════════════════════════════════════
    #  ORQUESTADOR PRINCIPAL
    # ═══════════════════════════════════════════════

    @staticmethod
    def calculate(session: Session) -> dict:
        """
        Punto de entrada. Calcula IRR y TWR del portafolio.
        Ahora usa el modelo "Asset-Performance" (ignora cash libre no trackeado).
        """
        trades = session.exec(
            select(TradeHistory).order_by(TradeHistory.fecha.asc())
        ).all()

        if not trades:
            return {"irr_annual": None, "twr": {"portfolio": None, "sp500": None}, "alpha": None}

        # 1. Flujos para XIRR (Inversión absoluta)
        cashflows_xirr = []
        
        # 2. Flujos para TWR de Activos (Inyecciones/Retiros al balde de acciones)
        # BUY = Entrada (+), SELL = Salida (-), DIVIDEND = Salida si es cash (-)
        daily_asset_flows = {}

        for trade in trades:
            fecha_key = trade.fecha.date()
            total_dollars = _to_dollars(trade.total)
            
            # XIRR: Dinero que sale/entra al bolsillo (Depósitos/Retiros/Dividendos)
            if trade.tipo == "DEPOSIT":
                cashflows_xirr.append((trade.fecha, -abs(total_dollars)))
            elif trade.tipo == "WITHDRAW":
                cashflows_xirr.append((trade.fecha, abs(total_dollars)))
            elif trade.tipo == "DIVIDEND":
                cashflows_xirr.append((trade.fecha, abs(total_dollars)))
                # TWR Activos: Si cobras dividendo, "sale" del bucket de activos al bucket de cash
                daily_asset_flows[fecha_key] = daily_asset_flows.get(fecha_key, 0.0) - abs(total_dollars)
            
            # TWR Activos: Compras y Ventas son los flujos del bucket
            if trade.tipo == "BUY":
                daily_asset_flows[fecha_key] = daily_asset_flows.get(fecha_key, 0.0) + abs(total_dollars)
            elif trade.tipo == "SELL":
                daily_asset_flows[fecha_key] = daily_asset_flows.get(fecha_key, 0.0) - abs(total_dollars)

        # 3. Valor actual
        assets = session.exec(select(Asset)).all()
        active_assets = [a for a in assets if a.cantidad_total > 0]
        current_val = 0.0
        if active_assets:
            prices_map = MarketDataService.get_market_prices(session, active_assets)
            for a in active_assets:
                current_val += _safe_float(a.cantidad_total) * prices_map.get(a.ticker, 0) / 100.0
        
        cashflows_xirr.append((datetime.now(), current_val))
        irr = AdvancedReturnsService.calculate_xirr(cashflows_xirr)

        # 4. TWR
        from services.analytics_service import AnalyticsService
        try:
            history = AnalyticsService.get_portfolio_history(session)
            if history:
                daily_twr_data = []
                for d in history:
                    d_date = datetime.strptime(d["fecha"], "%Y-%m-%d").date()
                    daily_twr_data.append({
                        "fecha": d_date,
                        "asset_value": d["valor_mercado"],
                        "net_flow": daily_asset_flows.get(d_date, 0.0)
                    })
                twr_portfolio = AdvancedReturnsService.calculate_twr(daily_twr_data)
                
                # Sincronizar Inception del S&P 500 con el primer día real de activos
                first_active_day = None
                for d in daily_twr_data:
                    if d["asset_value"] > 0:
                        first_active_day = datetime.combine(d["fecha"], datetime.min.time())
                        break
                
                twr_sp500 = AdvancedReturnsService.calculate_sp500_twr(
                    first_active_day or trades[0].fecha, datetime.now()
                )
            else:
                twr_portfolio = twr_sp500 = None
        except Exception as e:
            print(f"Error TWR: {e}")
            twr_portfolio = twr_sp500 = None

        alpha = round(twr_portfolio - twr_sp500, 2) if twr_portfolio is not None and twr_sp500 is not None else None
        return {"irr_annual": irr, "twr": {"portfolio": twr_portfolio, "sp500": twr_sp500}, "alpha": alpha}
