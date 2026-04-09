"""
Suite de Tests: Auditoría Extrema — Pilar 4
=============================================
Cubre: Aritmética de centavos, TTLCache, safe_pct, NaN guards, y edge cases.
Framework: pytest
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from datetime import datetime
from services.portfolio_service import to_cents, to_dollars, safe_float
from services.cache import TTLCache
from models.models import TradeHistory, Asset
import time


# ═══════════════════════════════════════════════════
# TEST GROUP 1: Aritmética de Centavos (to_cents / to_dollars)
# ═══════════════════════════════════════════════════

class TestCentsArithmetic:
    """Verifica que la conversión cents ↔ dollars es precisa."""

    def test_basic_conversions(self):
        assert to_cents(0.01) == 1
        assert to_cents(1.00) == 100
        assert to_cents(10.50) == 1050
        assert to_cents(0.0) == 0

    def test_reverse_conversions(self):
        assert to_dollars(1) == 0.01
        assert to_dollars(100) == 1.0
        assert to_dollars(1050) == 10.50
        assert to_dollars(0) == 0.0

    def test_ieee_754_notorious_cases(self):
        """0.1 + 0.2 != 0.3 en IEEE 754, pero en centavos sí."""
        assert to_cents(0.1) == 10
        assert to_cents(0.2) == 20
        # Acumulación: 0.1 + 0.2 como float → to_cents
        assert to_cents(0.1 + 0.2) == 30  # No 29 ni 31

    def test_negative_values(self):
        assert to_cents(-10.50) == -1050
        assert to_dollars(-1050) == -10.50

    def test_large_values(self):
        """Portfolios de millones."""
        assert to_cents(1_000_000.99) == 100_000_099
        assert to_dollars(100_000_099) == 1_000_000.99


# ═══════════════════════════════════════════════════
# TEST GROUP 2: safe_float — Inputs adversarios
# ═══════════════════════════════════════════════════

class TestSafeFloat:
    """safe_float debe manejar NaN, Infinity, None, strings sin crashear."""

    def test_none(self):
        assert safe_float(None) == 0.0

    def test_nan(self):
        assert safe_float(float('nan')) == 0.0

    def test_infinity(self):
        assert safe_float(float('inf')) == 0.0
        assert safe_float(float('-inf')) == 0.0

    def test_string(self):
        assert safe_float("not_a_number") == 0.0

    def test_zero(self):
        assert safe_float(0) == 0.0

    def test_valid_negative(self):
        assert safe_float(-100.5) == -100.5

    def test_valid_positive(self):
        assert safe_float(42) == 42.0
        assert safe_float(3.14) == 3.14


# ═══════════════════════════════════════════════════
# TEST GROUP 3: TTLCache — Comportamiento LRU + TTL
# ═══════════════════════════════════════════════════

class TestTTLCache:
    """Verifica que TTLCache expira, evicta, y no leakea memoria."""

    def test_basic_set_get(self):
        cache = TTLCache(maxsize=10, ttl_seconds=60)
        cache.set("key1", {"data": 42})
        assert cache.get("key1") == {"data": 42}

    def test_miss(self):
        cache = TTLCache(maxsize=10, ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_expiration(self):
        cache = TTLCache(maxsize=10, ttl_seconds=1)  # 1 second TTL
        cache.set("key1", "value")
        assert cache.get("key1") == "value"
        time.sleep(1.1)  # Wait for expiration
        assert cache.get("key1") is None

    def test_maxsize_eviction(self):
        cache = TTLCache(maxsize=3, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Adding 4th should evict "a" (oldest)
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("d") == 4

    def test_lru_order(self):
        cache = TTLCache(maxsize=3, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Access "a" to make it recently used
        cache.get("a")
        # Now insert "d" — should evict "b" (least recently used), not "a"
        cache.set("d", 4)
        assert cache.get("a") == 1  # Still alive (was accessed)
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_overwrite(self):
        cache = TTLCache(maxsize=10, ttl_seconds=60)
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"
        assert len(cache) == 1

    def test_clear(self):
        cache = TTLCache(maxsize=10, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert len(cache) == 0
        assert cache.get("a") is None

    def test_contains(self):
        cache = TTLCache(maxsize=10, ttl_seconds=60)
        cache.set("exists", True)
        assert "exists" in cache
        assert "missing" not in cache


# ═══════════════════════════════════════════════════
# TEST GROUP 4: Risk Metrics — Max Drawdown edge cases
# ═══════════════════════════════════════════════════

class TestMaxDrawdown:
    """Max Drawdown debe ser robusto con series vacías, flat, y adversarias."""

    def test_empty_series(self):
        from services.risk_service import RiskMetricsService
        result = RiskMetricsService.calculate_max_drawdown(pd.Series([]))
        assert result == 0.0

    def test_flat_series(self):
        from services.risk_service import RiskMetricsService
        flat = pd.Series([0.0, 0.0, 0.0, 0.0])
        assert RiskMetricsService.calculate_max_drawdown(flat) == 0.0

    def test_only_positive_returns(self):
        from services.risk_service import RiskMetricsService
        up_only = pd.Series([0.01, 0.02, 0.03, 0.01, 0.02])
        dd = RiskMetricsService.calculate_max_drawdown(up_only)
        assert dd <= 0.0, f"Drawdown debe ser <= 0 para serie con drawdowns, obtuvo {dd}"


# ═══════════════════════════════════════════════════
# TEST GROUP 5: Portfolio edge cases con DB
# ═══════════════════════════════════════════════════

class TestPortfolioEdgeCases:
    """Tests que requieren la fixture de session para interactuar con la DB."""

    def test_empty_portfolio_dashboard(self, session):
        """Un portafolio completamente vacío no debe crashear."""
        from services.portfolio_service import PortfolioService
        summary = PortfolioService.get_dashboard_summary(session)
        assert summary["net_worth"] == 0
        assert summary["performance"]["value"] == 0
        assert summary["performance"]["percentage"] == 0

    def test_buy_and_full_sell(self, session):
        """Comprar y vender todo no debe dejar activo residual ni crashear."""
        from services.portfolio_service import PortfolioService

        # Buy 10 shares at $100
        PortfolioService.execute_buy(session, "TST", 10.0, 100.0, usar_caja_broker=False, applied_fee=0.0)
        
        # Sell all 10 shares at $120
        PortfolioService.execute_sell(session, "TST", 10.0, 120.0, usar_caja_broker=False, applied_fee=0.0)
        
        # Asset should have 0 quantity
        asset = session.query(Asset).filter(Asset.ticker == "TST").first()
        assert asset is not None
        assert asset.cantidad_total == 0

    def test_fractional_shares(self, session):
        """Compras de acciones fraccionarias extremas."""
        from services.portfolio_service import PortfolioService
        PortfolioService.execute_buy(session, "FRAC", 0.00001, 150000.0, usar_caja_broker=False, applied_fee=0.0)
        
        asset = session.query(Asset).filter(Asset.ticker == "FRAC").first()
        assert asset is not None
        assert asset.cantidad_total == pytest.approx(0.00001, abs=1e-6)
