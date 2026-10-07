import pytest
from unittest.mock import patch
from sqlmodel import Session
from fastapi.testclient import TestClient

from models.models import Asset, WatchlistItem
from services.watchlist_service import WatchlistService
from services.screener_service import ScreenerService


def test_watchlist_service_crud(session: Session):
    # 1. Lista inicialmente vacía
    items = WatchlistService.get_watchlist(session)
    assert len(items) == 0

    # 2. Agregar ticker
    res = WatchlistService.add_to_watchlist(session, "NVDA", notes="IA Play")
    assert res["created"] is True
    assert res["ticker"] == "NVDA"
    assert res["notes"] == "IA Play"

    # 3. Verificar que existe
    assert WatchlistService.is_in_watchlist(session, "NVDA") is True
    assert WatchlistService.is_in_watchlist(session, "AAPL") is False

    # 4. Agregar idempotente (no duplica)
    res2 = WatchlistService.add_to_watchlist(session, "nvda", notes="Updated Notes")
    assert res2["created"] is False
    assert res2["notes"] == "Updated Notes"

    tickers = WatchlistService.get_watchlist_tickers(session)
    assert tickers == ["NVDA"]

    # 5. Eliminar ticker
    deleted = WatchlistService.remove_from_watchlist(session, "NVDA")
    assert deleted is True
    assert WatchlistService.is_in_watchlist(session, "NVDA") is False
    assert len(WatchlistService.get_watchlist(session)) == 0

    # 6. Eliminar inexistente
    assert WatchlistService.remove_from_watchlist(session, "NVDA") is False


def test_evaluate_single_ticker_mocked():
    mock_fund = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "current_price": 200.0,
        "is_etf": False,
        "summary": {
            "margin_of_safety_pct": 18.5,
            "verdict": "undervalued",
            "verdict_label": "Infravalorada",
            "average_fair_value": 237.0
        },
        "metrics": {
            "valuation": {"trailing_pe": 28.5},
            "growth_and_dividends": {"dividend_yield_pct": 0.5},
            "market_stats": {"market_cap": 3000000000000}
        },
        "profile": {"sector": "Technology"}
    }
    mock_tech = {
        "ticker": "AAPL",
        "current_price": 200.0,
        "timing": {"verdict": "bullish_trend"},
        "rsi": {"value": 45.2, "status": "neutral", "label": "Neutral"},
        "moving_averages": {"price_above_sma_200": True, "golden_cross": True}
    }
    mock_conf = {
        "confluence": {
            "verdict_id": "strong_buy_confluence",
            "title": "Oportunidad Fuerte",
            "color": "emerald",
            "action": "Considerar compra"
        }
    }

    with patch("services.screener_service.FundamentalService.get_fundamentals", return_value=mock_fund), \
         patch("services.screener_service.TechnicalService.get_technical_analysis", return_value=mock_tech), \
         patch("services.screener_service.TechnicalService.get_confluence_analysis", return_value=mock_conf):
        
        portfolio_info = {"cantidad": 10.0, "precio_promedio": 180.0}
        item = ScreenerService._evaluate_single_ticker(
            ticker="AAPL",
            portfolio_info=portfolio_info,
            is_watchlist=True,
            total_portfolio_val=2000.0
        )

        assert item["ticker"] == "AAPL"
        assert item["company_name"] == "Apple Inc."
        assert item["price"] == 200.0
        assert item["margin_of_safety_pct"] == 18.5
        assert item["valuation_verdict"] == "undervalued"
        assert item["fair_value"] == 237.0
        assert item["rsi"] == 45.2
        assert item["rsi_status"] == "neutral"
        assert item["trend"] == "bullish"
        assert item["golden_cross"] is True
        assert item["confluence_verdict"] == "strong_buy_confluence"
        assert item["in_portfolio"] is True
        assert item["in_watchlist"] is True
        assert item["portfolio_shares"] == 10.0
        assert item["unrealized_profit_usd"] == 200.0  # (200 - 180) * 10
        assert item["unrealized_profit_pct"] == pytest.approx(11.11, rel=1e-2)


def test_screener_api_endpoints(client: TestClient, session: Session):
    # 1. Test Presets
    res_presets = client.get("/api/screener/presets")
    assert res_presets.status_code == 200
    presets = res_presets.json()["presets"]
    assert len(presets) >= 4
    preset_ids = [p["id"] for p in presets]
    assert "deep_value" in preset_ids
    assert "strong_confluence" in preset_ids

    # 2. Test Watchlist API
    # Add
    res_add = client.post("/api/watchlist/TSLA?notes=Electrics")
    assert res_add.status_code == 200
    assert res_add.json()["status"] == "success"

    # Get
    res_wl = client.get("/api/watchlist")
    assert res_wl.status_code == 200
    assert "TSLA" in res_wl.json()["watchlist"]

    # Delete
    res_del = client.delete("/api/watchlist/TSLA")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "success"

    # Verify deleted
    res_wl_after = client.get("/api/watchlist")
    assert "TSLA" not in res_wl_after.json()["watchlist"]


def test_screener_get_endpoint_mocked(client: TestClient, session: Session):
    mock_eval = {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "price": 120.0,
        "sector": "Technology",
        "is_etf": False,
        "margin_of_safety_pct": 25.0,
        "valuation_verdict": "undervalued",
        "valuation_label": "Infravalorada",
        "fair_value": 150.0,
        "rsi": 28.0,
        "rsi_status": "oversold",
        "rsi_label": "Sobrevendida",
        "trend": "bullish",
        "golden_cross": True,
        "confluence_verdict": "strong_buy_confluence",
        "confluence_label": "Oportunidad Fuerte",
        "confluence_color": "emerald",
        "confluence_action": "Compra",
        "dividend_yield_pct": 0.1,
        "pe_ratio": 45.0,
        "market_cap": 2800000000000,
        "in_portfolio": False,
        "in_watchlist": True,
        "portfolio_shares": None,
        "portfolio_avg_price": None,
        "unrealized_profit_usd": None,
        "unrealized_profit_pct": None,
        "portfolio_weight_pct": None
    }

    with patch.object(ScreenerService, "get_screener_data", return_value=[mock_eval]):
        res = client.get("/api/screener?scope=all")
        assert res.status_code == 200
        data = res.json()
        assert data["total_items"] == 1
        assert data["items"][0]["ticker"] == "NVDA"
        assert data["items"][0]["margin_of_safety_pct"] == 25.0
