from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List

from database import get_session
from models.models import Asset, TradeHistory

from services.risk_service import RiskMetricsService
from services.benchmark_service import BenchmarkService
from services.valuation_service import ValuationService
from services.market_service import MarketDataService
from services.portfolio_service import PortfolioService
from services.oracle_service import OracleService
from services.analytics_service import AnalyticsService
from services.performance_service import PerformanceBreakdownService
from services.advanced_returns_service import AdvancedReturnsService

import pandas as pd

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/metrics")
def get_risk_metrics(session: Session = Depends(get_session), period: str = Query("1y")):
    """
    Retorna métricas cuantitativas como Volatilidad, Beta, Sharpe Ratio y Max Drawdown.
    """
    try:
        return RiskMetricsService.calculate_for_session(session, period=period)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmark")
def get_benchmark_chart(session: Session = Depends(get_session), period: str = Query("1y")):
    """
    Retorna la data base-100 para comparar el portafolio vs el Benchmark,
    usando el rendimiento real ponderado de los activos en el tiempo (Base 100).
    """
    assets = session.exec(select(Asset)).all()
    active_assets = [a for a in assets if a.cantidad_total > 0]
    tickers = [asset.ticker for asset in active_assets]
    
    if not tickers:
        return []

    try:
        # Lógica de Inception Date
        inception_date = session.exec(select(func.min(TradeHistory.fecha))).first()

        # Paso 1: Matriz con precios diarios de cierre
        prices_df = RiskMetricsService.fetch_historical_prices(tickers, period=period)
        
        if not prices_df.empty:
            if inception_date:
                inception_dt = pd.to_datetime(inception_date)
                if inception_dt.tzinfo is not None:
                    inception_dt = inception_dt.tz_localize(None)
                if prices_df.index.tz is not None:
                    inception_dt = inception_dt.tz_localize(prices_df.index.tz)
                # Aplicamos el truncamiento exacto: MAX(startDate, InceptionDate)
                prices_df = prices_df[prices_df.index >= inception_dt]

            # Retorno porcentual de cada activo (Precio_Hoy - Precio_Ayer) / Precio_Ayer
            # fillna(0) asegura que el Día 0 retenga retornos de 0% (base neutral)
            returns_df = prices_df.pct_change().fillna(0)
            
            # Paso 2: Calculo de pesos (weights) actuales basados en json/db
            current_prices = MarketDataService.get_market_prices(session, active_assets)
            weights_dict = {}
            total_value = 0.0
            
            for a in active_assets:
                if a.ticker in returns_df.columns:
                    price_cents = current_prices.get(a.ticker, 0)
                    val = (price_cents / 100.0) * float(a.cantidad_total)
                    weights_dict[a.ticker] = val
                    total_value += val
                    
            # Normalizar los pesos al 100%
            if total_value > 0:
                weights = pd.Series({k: v / total_value for k, v in weights_dict.items()})
            else:
                # Fallback equiponderado si no hay valor
                weights = pd.Series({k: 1.0 / len(returns_df.columns) for k in returns_df.columns})
            
            # Alinear los weights con las columnas de los retornos
            weights = weights.reindex(returns_df.columns).fillna(0)
            
            # Retorno Diario del Portafolio: suma de valores ponderados
            portfolio_daily_returns = (returns_df * weights).sum(axis=1)
            
            # Paso 3: Construcción Índice Base 100 Acumulativo
            # Al tener el ret=0 en el Día 0, matemáticamente el inicio será 100.
            base_100_portfolio = (1 + portfolio_daily_returns).cumprod() * 100
            
            chart_data = BenchmarkService.generate_comparative_chart_data(base_100_portfolio, period=period)
            return chart_data
        return []
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio-performance")
def get_portfolio_performance(session: Session = Depends(get_session)):
    """
    Retorna el crecimiento Real Acumulado del portafolio (vectorizado con Pandas O(N))
    versus el S&P 500, alineado matemáticamente a 0% en el inception_date.
    """
    try:
        data = AnalyticsService.get_portfolio_history(session)
        return {"data": data}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance-breakdown")
def get_performance_breakdown(session: Session = Depends(get_session)):
    """
    Pilar 1 + 2: Desglose profesional de rendimiento + IRR/TWR.
    Combina el motor financiero con las métricas de retorno avanzadas en un solo JSON.
    """
    try:
        # Pilar 1: Motor Financiero
        breakdown = PerformanceBreakdownService.calculate(session)

        # Pilar 2: IRR + TWR
        advanced = AdvancedReturnsService.calculate(session)

        # Merge ambos resultados
        breakdown["irr_annual"] = advanced.get("irr_annual")
        breakdown["twr"] = advanced.get("twr", {"portfolio": None, "sp500": None})
        breakdown["alpha"] = advanced.get("alpha")

        return breakdown
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diversification")
def get_diversification(session: Session = Depends(get_session)):
    """
    Agrupa el valor de mercado histórico actual del portafolio por sectores geográficos e industriales.
    """
    assets = session.exec(select(Asset)).all()
    active_assets = [a for a in assets if a.cantidad_total > 0]
    
    if not active_assets:
        return {"sectors": [], "countries": []}
        
    prices = MarketDataService.get_market_prices(session, active_assets)
    
    # FIX-9: Batch evaluation paralela en lugar de N llamadas secuenciales
    tickers_with_value = []
    ticker_market_vals = {}
    for a in active_assets:
        price_cents = prices.get(a.ticker, 0)
        market_val = (price_cents / 100.0) * float(a.cantidad_total)
        if market_val > 0:
            tickers_with_value.append(a.ticker)
            ticker_market_vals[a.ticker] = market_val

    fundamentals_batch = ValuationService.evaluate_assets_batch(tickers_with_value)
    
    sectors_aggr = {}
    countries_aggr = {}
    
    for ticker, market_val in ticker_market_vals.items():
        fundamentals = fundamentals_batch.get(ticker, {})
        sector = fundamentals.get("sector", "Unknown")
        country = fundamentals.get("country", "Unknown")
        
        sectors_aggr[sector] = sectors_aggr.get(sector, 0) + market_val
        countries_aggr[country] = countries_aggr.get(country, 0) + market_val
            
    return {
        "sectors": sorted([{"name": k, "value": round(v, 2)} for k, v in sectors_aggr.items()], key=lambda x: x["value"], reverse=True),
        "countries": sorted([{"name": k, "value": round(v, 2)} for k, v in countries_aggr.items()], key=lambda x: x["value"], reverse=True)
    }

@router.get("/valuation")
def get_intrinsic_valuation(session: Session = Depends(get_session)):
    """
    Calcula el intrinsic score ajustado por diversificación
    """
    try:
        return ValuationService.calculate_for_session(session)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/oracle")
def get_oracle_insights(session: Session = Depends(get_session)):
    """
    Orquesta los datos hacia el OracleService y provee los Insights sugeridos.
    """
    try:
        # Get risk metrics directly from service
        metrics = RiskMetricsService.calculate_for_session(session, period="1y")
        if isinstance(metrics, dict) and "error" in metrics:
            return {"insights": []}

        # Get valuation data directly from service
        val_response = ValuationService.calculate_for_session(session)
        val_data = val_response.get("analysis", []) if isinstance(val_response, dict) else []

        # Get cash logic via dashboard summary
        dashboard = PortfolioService.get_dashboard_summary(session)
        net_worth = dashboard.get("net_worth", 0)
        
        assets_list = dashboard.get("assets", [])
        # Summarize total uninvested cash (Wallet + Broker)
        cash_balance = sum([a.get("amount", 0) for a in assets_list if getattr(a, "category", a.get("category")) == "Cash"])

        insights = OracleService.generate_insights(
            risk_metrics=metrics,
            valuation_data=val_data,
            net_worth=net_worth,
            cash_balance=cash_balance
        )
        return {"insights": insights}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
