import pytest
import threading
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from services.cache import TTLCache
from services.risk_service import RiskMetricsService
from services.performance_service import PerformanceBreakdownService
from services.advanced_returns_service import AdvancedReturnsService
from services.portfolio_service import PortfolioService
from models.models import Asset, TradeHistory, BrokerCash, Transaction


class TestAuditFixesComprehensive:

    def test_total_return_no_double_commission(self, session):
        """
        Verifica que el Total Return NO deduzca las comisiones dos veces.
        - Compra: 1 acción a $100 con $2 de comisión. Costo base = $102 (10200 cents).
        - Venta: 1 acción a $120 con $2 de comisión. Neto = $118, Ganancia realizada = $118 - $102 = $16.
        - Comisiones totales = $4 ($2 + $2).
        - Total Return debe ser $16.00 neto, NO $12.00 (que resultaría si se vuelven a restar los $4).
        """
        # Registrar compra
        trade_buy = TradeHistory(
            ticker="ABC",
            tipo="BUY",
            cantidad=1.0,
            precio=10000,
            total=10200,
            commission=200,
            fecha=datetime.now() - timedelta(days=2)
        )
        session.add(trade_buy)

        # Registrar venta
        trade_sell = TradeHistory(
            ticker="ABC",
            tipo="SELL",
            cantidad=1.0,
            precio=12000,
            total=11800,
            commission=200,
            ganancia_realizada=1600, # $16.00
            fecha=datetime.now() - timedelta(days=1)
        )
        session.add(trade_sell)
        session.commit()

        # Act
        result = PerformanceBreakdownService.calculate(session)

        # Assert
        assert result["realized_gain"]["value"] == 16.00
        assert result["total_costs"]["transaction_costs"] == 4.00
        # Total return debe ser exactamente $16.00 (no $12.00 por doble deducción)
        assert result["total_return"]["value"] == 16.00

    def test_max_drawdown_anchored_from_start(self):
        """
        Verifica que una serie de retornos que comienza con caídas
        registre correctamente el drawdown desde el valor base 1.0.
        """
        # Día 1: -10%, Día 2: -5%
        returns = pd.Series([-0.10, -0.05])
        dd = RiskMetricsService.calculate_max_drawdown(returns)
        
        # 1.0 * 0.90 = 0.90 (caída del 10%)
        # 0.90 * 0.95 = 0.855 (caída del 14.5%)
        # El Max Drawdown debe ser -14.5% (-0.145), NO 0% ni solo la segunda caída
        assert dd == pytest.approx(-0.145, abs=1e-3)

    def test_ttl_cache_thread_safety(self):
        """
        Verifica que TTLCache sea thread-safe bajo concurrencia extrema
        sin lanzar KeyError ni corromper el OrderedDict.
        """
        cache = TTLCache(maxsize=20, ttl_seconds=60)
        errors = []

        def worker(thread_id):
            try:
                for i in range(200):
                    key = f"key_{i % 30}"
                    cache.set(key, f"val_{thread_id}_{i}")
                    val = cache.get(key)
                    if i % 10 == 0:
                        _ = len(cache)
                        _ = key in cache
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errores en hilos de cache: {errors}"
        assert len(cache) <= 20

    def test_xirr_with_broker_cash_included(self, session):
        """
        Verifica que XIRR incluya el efectivo disponible en caja de broker
        cuando se registran depósitos, evitando pérdidas ficticias por liquidez no desplegada.
        """
        # Depósito de $10,000 hace 30 días
        deposit = TradeHistory(
            ticker="CASH",
            tipo="DEPOSIT",
            cantidad=1.0,
            precio=1000000,
            total=1000000,
            commission=0,
            fecha=datetime.now() - timedelta(days=30)
        )
        session.add(deposit)

        # Caja de broker con $5,000 no invertidos
        broker_cash = BrokerCash(id=1, saldo_usd=500000)
        session.add(broker_cash)

        # Activo con valor actual de $5,100 ($5,000 invertidos que subieron $100)
        asset = Asset(
            ticker="AAPL",
            cantidad_total=10.0,
            precio_promedio=50000,
            cached_price=51000,
            last_updated=datetime.now()
        )
        session.add(asset)
        session.commit()

        # Mock MarketDataService
        from services.market_service import MarketDataService
        original_get = MarketDataService.get_market_prices
        MarketDataService.get_market_prices = lambda s, a: {"AAPL": 51000}

        try:
            result = AdvancedReturnsService.calculate(session)
            # Portafolio total = $5,100 (acciones) + $5,000 (caja) = $10,100
            # Retorno positivo leve sobre $10,000 iniciales
            assert result["irr_annual"] is not None
            assert result["irr_annual"] > 0
        finally:
            MarketDataService.get_market_prices = original_get

    def test_xirr_direct_trades_without_deposit(self, session):
        """
        Verifica que inversores que no usan depósitos (solo compras y ventas directas)
        obtengan un XIRR válido en lugar de None.
        """
        # Compra directa de $1,000 hace 60 días
        buy = TradeHistory(
            ticker="MSFT",
            tipo="BUY",
            cantidad=10.0,
            precio=10000,
            total=100000,
            commission=0,
            fecha=datetime.now() - timedelta(days=60)
        )
        session.add(buy)

        asset = Asset(
            ticker="MSFT",
            cantidad_total=10.0,
            precio_promedio=10000,
            cached_price=12000, # Subió a $120
            last_updated=datetime.now()
        )
        session.add(asset)
        session.commit()

        from services.market_service import MarketDataService
        original_get = MarketDataService.get_market_prices
        MarketDataService.get_market_prices = lambda s, a: {"MSFT": 12000}

        try:
            result = AdvancedReturnsService.calculate(session)
            # $1,000 invertidos ahora valen $1,200 (+20% en 60 días)
            assert result["irr_annual"] is not None
            assert result["irr_annual"] > 0
        finally:
            MarketDataService.get_market_prices = original_get
