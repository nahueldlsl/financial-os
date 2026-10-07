import pytest
from datetime import datetime, timedelta
from sqlmodel import Session
from unittest.mock import patch
import pandas as pd

from models.models import Asset, TradeHistory
from services.analytics_service import AnalyticsService, _analytics_prices_cache, _sp500_cache
from services.advanced_returns_service import AdvancedReturnsService


def test_analytics_resilience_when_yfinance_drops_ticker(session: Session):
    """
    Verifica que si yfinance falla o devuelve datos vacíos para un ticker,
    el ticker NO sea descartado de la cartera y se use el precio de respaldo de la DB.
    """
    _analytics_prices_cache.clear()
    _sp500_cache.clear()

    now = datetime.now()
    t1 = TradeHistory(
        ticker="AAPL",
        tipo="BUY",
        cantidad=1.0,
        precio=15000,
        total=15030,
        commission=30,
        fecha=now - timedelta(days=5)
    )
    session.add(t1)
    session.add(Asset(
        ticker="AAPL",
        cantidad_total=1.0,
        precio_promedio=15030,
        cached_price=16000,
        last_updated=now
    ))
    session.commit()

    # Simular que yfinance falla completamente arrojando una excepción
    with patch("yfinance.download") as mock_download:
        mock_download.side_effect = Exception("Yahoo Finance Rate Limit 429")

        history = AnalyticsService.get_portfolio_history(session)
        assert len(history) > 0
        last_pt = history[-1]
        # El activo debe haberse preservado con valor de mercado > 0 gracias al fallback
        assert last_pt["valor_mercado"] > 0
        assert last_pt["capital_invertido"] > 0


def test_sp500_cache_synchronization(session: Session):
    """
    Verifica que AdvancedReturnsService y AnalyticsService compartan la caché de S&P 500.
    """
    _sp500_cache.clear()
    now = datetime.now()
    start_str = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    end_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')

    fake_dates = pd.date_range(start=now - timedelta(days=30), end=now, freq='D')
    fake_sp = pd.DataFrame(index=fake_dates)
    fake_sp['SP500_Close'] = [5000.0 + i * 10 for i in range(len(fake_dates))]
    _sp500_cache.set((start_str, end_str), fake_sp)

    twr = AdvancedReturnsService.calculate_sp500_twr(now - timedelta(days=30), now)
    assert twr is not None
    assert twr > 0
