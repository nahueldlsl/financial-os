"""
Pilar 1: Performance Breakdown Service
Motor Financiero — Desglose profesional del rendimiento del portafolio.

Calcula:
  - Capital Invertido (suma neta de compras - ventas)
  - Unrealized Gain (precio mercado vs costo base, en $ y %)
  - Realized Gain (P&L bloqueado de ventas, en $ y %)
  - Dividendos (DIVIDEND entries en historial)
  - Transaction Costs (comisiones acumuladas)
  - Total Return (Unrealized + Realized + Dividends - Costs)
  - Portfolio P/E ponderado por peso de mercado
"""

import math
from sqlmodel import Session, select
from sqlalchemy import func

from models.models import Asset, TradeHistory
from services.market_service import MarketDataService
from services.valuation_service import ValuationService
from utils.money import safe_float as _safe_float, to_dollars as _to_dollars


class PerformanceBreakdownService:

    @staticmethod
    def calculate(session: Session) -> dict:
        """
        Punto de entrada principal.
        Retorna el JSON completo del desglose de rendimiento.
        """

        # ──────────────────────────────────────────────
        # 1. INVESTED CAPITAL (Costo Base de Posiciones Abiertas)
        #    Siguiendo la definición del usuario ($925 aprox).
        #    = Σ(cantidad * precio_promedio)
        # ──────────────────────────────────────────────
        assets = session.exec(select(Asset)).all()
        active_assets = [a for a in assets if a.cantidad_total > 0]
        
        # total_cost_basis_cents: Σ(qty * avg_price_cents)
        total_cost_basis_cents = 0.0
        for asset in active_assets:
            total_cost_basis_cents += _safe_float(asset.cantidad_total) * _safe_float(asset.precio_promedio)

        invested_capital_dollars = _to_dollars(total_cost_basis_cents)

        # ──────────────────────────────────────────────
        # 2. MARKET VALUE & UNREALIZED GAIN
        # ──────────────────────────────────────────────
        prices_map_cents = MarketDataService.get_market_prices(session, active_assets)
        total_market_value_cents = 0.0

        for asset in active_assets:
            price_cents = prices_map_cents.get(asset.ticker, 0)
            total_market_value_cents += _safe_float(asset.cantidad_total) * price_cents

        unrealized_gain_cents = total_market_value_cents - total_cost_basis_cents
        unrealized_gain_dollars = _to_dollars(unrealized_gain_cents)

        unrealized_pct = 0.0
        if total_cost_basis_cents > 0:
            unrealized_pct = (unrealized_gain_cents / total_cost_basis_cents) * 100

        # ──────────────────────────────────────────────
        # 3. DIVIDENDOS
        # ──────────────────────────────────────────────
        dividends_cents = session.exec(
            select(func.sum(TradeHistory.total))
            .where(TradeHistory.tipo == "DIVIDEND")
        ).first() or 0

        dividends_dollars = _to_dollars(dividends_cents)
        
        # ──────────────────────────────────────────────
        # 4. REALIZED GAIN
        # ──────────────────────────────────────────────
        realized_gain_cents = session.exec(
            select(func.sum(TradeHistory.ganancia_realizada))
            .where(TradeHistory.tipo == "SELL")
        ).first() or 0

        realized_gain_dollars = _to_dollars(realized_gain_cents)

        # ──────────────────────────────────────────────
        # 5. TRANSACTION COSTS (Comisiones)
        # ──────────────────────────────────────────────
        total_commission_cents = session.exec(
            select(func.sum(TradeHistory.commission))
        ).first() or 0

        transaction_costs_dollars = _to_dollars(total_commission_cents)

        # ──────────────────────────────────────────────
        # 6. TOTAL RETURN & PERCENTAGES
        # ──────────────────────────────────────────────
        # Las comisiones ya están capitalizadas en el costo base de las posiciones abiertas (unrealized_gain)
        # y deducidas de los ingresos netos en las ventas cerradas (realized_gain).
        # Se exponen informativamente en transaction_costs, pero no se restan doblemente.
        total_return_cents = (
            unrealized_gain_cents
            + _safe_float(realized_gain_cents)
            + _safe_float(dividends_cents)
        )
        total_return_dollars = _to_dollars(total_return_cents)
        
        total_return_pct = 0.0
        if total_cost_basis_cents > 0:
            total_return_pct = (total_return_cents / total_cost_basis_cents) * 100

        # Porcentajes adicionales para la UI
        dividends_pct = 0.0
        if invested_capital_dollars > 0:
            dividends_pct = (dividends_dollars / invested_capital_dollars) * 100
            
        realized_pct = 0.0
        if invested_capital_dollars > 0:
            realized_pct = (realized_gain_dollars / invested_capital_dollars) * 100

        # ──────────────────────────────────────────────
        # 7. PORTFOLIO P/E PONDERADO
        # ──────────────────────────────────────────────
        portfolio_pe = PerformanceBreakdownService._calculate_weighted_pe(
            active_assets, prices_map_cents
        )

        # ──────── OUTPUT ────────
        return {
            "invested_capital": round(invested_capital_dollars, 2),
            "market_value": round(_to_dollars(total_market_value_cents), 2),
            "unrealized_gain": {
                "value": round(unrealized_gain_dollars, 2),
                "percentage": round(unrealized_pct, 2)
            },
            "realized_gain": {
                "value": round(realized_gain_dollars, 2),
                "percentage": round(realized_pct, 2)
            },
            "dividends": {
                "value": round(dividends_dollars, 2),
                "percentage": round(dividends_pct, 2)
            },
            "total_costs": {
                "transaction_costs": round(transaction_costs_dollars, 2),
                "total": round(transaction_costs_dollars, 2)
            },
            "total_return": {
                "value": round(total_return_dollars, 2),
                "percentage": round(total_return_pct, 2)
            },
            "portfolio_pe": round(portfolio_pe, 1) if portfolio_pe else None
        }

    @staticmethod
    def _calculate_weighted_pe(active_assets: list, prices_map_cents: dict) -> float:
        """
        Calcula el P/E Ratio promedio ponderado del portafolio.
        Peso = valor_mercado_ticker / valor_mercado_total.
        Ignora tickers con PE ≤ 0 o None.
        """
        if not active_assets:
            return 0.0

        # Obtener fundamentales en batch
        tickers = [a.ticker for a in active_assets]
        fundamentals_batch = ValuationService.evaluate_assets_batch(tickers)

        weighted_pe_sum = 0.0
        total_eligible_weight = 0.0
        total_market_value = 0.0

        # Calcular valor de mercado total primero
        asset_market_vals = {}
        for asset in active_assets:
            price_cents = prices_map_cents.get(asset.ticker, 0)
            mkt_val = _safe_float(asset.cantidad_total) * price_cents
            asset_market_vals[asset.ticker] = mkt_val
            total_market_value += mkt_val

        if total_market_value <= 0:
            return 0.0

        for asset in active_assets:
            fundamentals = fundamentals_batch.get(asset.ticker, {})
            pe = _safe_float(fundamentals.get("pe_ratio", 0))

            # Ignorar PE negativos, cero o anormalmente altos (> 500 = ruido)
            if pe <= 0 or pe > 500:
                continue

            weight = asset_market_vals.get(asset.ticker, 0) / total_market_value
            weighted_pe_sum += pe * weight
            total_eligible_weight += weight

        # Renormalizar por los activos elegibles
        if total_eligible_weight > 0:
            return weighted_pe_sum / total_eligible_weight

        return 0.0
