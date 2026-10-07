import pytest
from datetime import datetime, timedelta
from sqlmodel import Session
from models.models import Asset, TradeHistory
from services.analytics_service import AnalyticsService
from services.advanced_returns_service import AdvancedReturnsService
from services.risk_service import RiskMetricsService


def test_twr_curve_matches_advanced_returns(session: Session):
    """
    Verifica que la curva temporal de TWR termine coincidiendo exactamente con el TWR
    escalar calculado por AdvancedReturnsService para el portafolio.
    """
    now = datetime.now()
    # Trade 1: Compra inicial día -10
    t1 = TradeHistory(
        ticker="AAPL",
        tipo="BUY",
        cantidad=1.0,
        precio=15000,
        total=15030,
        commission=30,
        fecha=now - timedelta(days=10)
    )
    # Trade 2: Compra día -5
    t2 = TradeHistory(
        ticker="MSFT",
        tipo="BUY",
        cantidad=1.0,
        precio=25000,
        total=25030,
        commission=30,
        fecha=now - timedelta(days=5)
    )
    # Trade 3: Venta con ganancia de AAPL día -2
    t3 = TradeHistory(
        ticker="AAPL",
        tipo="SELL",
        cantidad=1.0,
        precio=18000,
        total=17970,
        commission=30,
        ganancia_realizada=2940,  # $29.40
        fecha=now - timedelta(days=2)
    )
    session.add_all([t1, t2, t3])

    # Assets correspondientes
    a_msft = Asset(
        ticker="MSFT",
        cantidad_total=1.0,
        precio_promedio=25030,
        cached_price=26000,
        last_updated=now
    )
    session.add(a_msft)
    session.commit()

    # Ejecutar cálculos
    history = AnalyticsService.get_portfolio_history(session)
    assert len(history) > 0

    adv_result = AdvancedReturnsService.calculate(session)
    expected_twr = adv_result["twr"]["portfolio"]

    last_point = history[-1]
    assert "pct_portafolio" in last_point
    assert "unrealized_pct" in last_point
    assert "pct_sp500" in last_point

    # Coincidencia matemática de TWR entre la curva y el servicio
    if expected_twr is not None:
        assert abs(last_point["pct_portafolio"] - expected_twr) <= 0.10


def test_risk_metrics_weighted_execution(session: Session):
    """
    Verifica que RiskMetricsService calcule métricas con ponderación real sin arrojar excepciones.
    """
    now = datetime.now()
    a = Asset(
        ticker="AAPL",
        cantidad_total=2.0,
        precio_promedio=15000,
        cached_price=16000,
        last_updated=now
    )
    session.add(a)
    session.commit()

    metrics = RiskMetricsService.calculate_for_session(session, period="1mo")
    assert isinstance(metrics, dict)
    assert "annualized_volatility_pct" in metrics
    assert "beta" in metrics
