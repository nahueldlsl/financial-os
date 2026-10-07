import pytest
from services.fundamental_service import FundamentalService

def test_calculate_dcf():
    # Supongamos una empresa con FCF = $10B, 1B acciones => FCF/share = $10
    # Crecimiento = 10%, Beta = 1.0, Total Cash = $5B, Total Debt = $3B, Precio = $150
    model = FundamentalService._calculate_dcf(
        fcf=10e9,
        shares=1e9,
        growth_rate=0.10,
        beta=1.0,
        total_cash=5e9,
        total_debt=3e9,
        current_price=150.0
    )
    assert model is not None
    assert model["id"] == "dcf"
    assert model["value"] > 0
    assert "diff_pct" in model
    assert model["weight"] == 1.25
    assert "tasa_descuento_wacc" in model["assumptions"]

def test_calculate_peter_lynch():
    # EPS = 5.0, Crecimiento = 15%, DivYield = 2.0%, Precio = $80
    model = FundamentalService._calculate_peter_lynch(
        eps=5.0,
        growth_rate=0.15,
        dividend_yield_pct=2.0,
        current_price=80.0
    )
    assert model is not None
    assert model["id"] == "peter_lynch"
    # Fair PE = 15 + 2 = 17 => Fair Value = 5 * 17 = 85.0
    assert model["value"] == 85.0
    assert model["diff_pct"] == round(((85.0 - 80.0) / 80.0) * 100, 1)

def test_calculate_graham_number():
    # EPS = 4.0, BVPS = 25.0 => sqrt(22.5 * 4 * 25) = sqrt(2250) = 47.43
    model = FundamentalService._calculate_graham_number(
        eps=4.0,
        bvps=25.0,
        current_price=50.0
    )
    assert model is not None
    assert model["id"] == "graham"
    assert round(model["value"], 2) == 47.43
    assert model["diff_pct"] == round(((47.43 - 50.0) / 50.0) * 100, 1)

def test_calculate_pe_multiple():
    # Forward EPS = 6.0, Growth = 10%, Current Price = 100
    model = FundamentalService._calculate_pe_multiple(
        forward_eps=6.0,
        growth_rate=0.10,
        current_price=100.0
    )
    assert model is not None
    assert model["id"] == "pe_multiple"
    assert model["value"] > 0

def test_calculate_ev_ebitda():
    # EBITDA = 10B, Debt = 2B, Cash = 4B, Shares = 1B, Price = 120
    # Implied EV = 10 * 13 = 130B. Equity = 130 - 2 + 4 = 132B => Per share = 132.0
    model = FundamentalService._calculate_ev_ebitda(
        ebitda=10e9,
        total_debt=2e9,
        total_cash=4e9,
        shares=1e9,
        current_price=120.0
    )
    assert model is not None
    assert model["id"] == "ev_ebitda"
    assert model["value"] == 132.0

def test_calculate_gordon_ddm():
    # DivRate = 3.0, Growth = 3%, Beta = 0.8, Price = 60
    model = FundamentalService._calculate_gordon_ddm(
        dividend_rate=3.0,
        growth_rate=0.03,
        beta=0.8,
        current_price=60.0
    )
    assert model is not None
    assert model["id"] == "ddm"
    assert model["value"] > 0

def test_synthesize_valuation_verdicts():
    # Test Deeply Undervalued (> 25% discount)
    models_cheap = [
        {"id": "dcf", "name": "DCF", "value": 140.0, "weight": 1.0, "diff_pct": 40.0},
        {"id": "lynch", "name": "Lynch", "value": 150.0, "weight": 1.0, "diff_pct": 50.0}
    ]
    summary_cheap = FundamentalService._synthesize_valuation(models_cheap, current_price=100.0)
    assert summary_cheap["verdict"] == "deeply_undervalued"
    assert summary_cheap["average_fair_value"] == 145.0
    assert summary_cheap["discount_pct"] == 45.0

    # Test Fair Value (-8% to +8%)
    models_fair = [
        {"id": "dcf", "name": "DCF", "value": 102.0, "weight": 1.0, "diff_pct": 2.0},
        {"id": "lynch", "name": "Lynch", "value": 98.0, "weight": 1.0, "diff_pct": -2.0}
    ]
    summary_fair = FundamentalService._synthesize_valuation(models_fair, current_price=100.0)
    assert summary_fair["verdict"] == "fair_value"

    # Test Deeply Overvalued (< -25%)
    models_expensive = [
        {"id": "dcf", "name": "DCF", "value": 60.0, "weight": 1.0, "diff_pct": -40.0},
        {"id": "lynch", "name": "Lynch", "value": 70.0, "weight": 1.0, "diff_pct": -30.0}
    ]
    summary_expensive = FundamentalService._synthesize_valuation(models_expensive, current_price=100.0)
    assert summary_expensive["verdict"] == "deeply_overvalued"

def test_etf_response_structure():
    mock_info = {
        "longName": "SPDR S&P 500 ETF Trust",
        "trailingPE": 25.4,
        "navPrice": 500.0,
        "yield": 0.012,
        "totalAssets": 500000000000,
        "category": "Large Blend",
        "fiftyTwoWeekLow": 450.0,
        "fiftyTwoWeekHigh": 550.0
    }
    res = FundamentalService._build_etf_response("SPY", 510.0, mock_info)
    assert res["is_etf"] is True
    assert res["summary"]["verdict"] == "etf_index"
    assert res["metrics"]["valuation"]["nav_price"] == 500.0
    assert "etf_note" in res["summary"]

def test_outlier_detection_trimming():
    # Modelos donde uno es un valor atípico absurdo ($21,622) frente a los otros (~$500)
    models = [
        {"id": "pe", "name": "P/E", "value": 520.0, "weight": 1.0, "diff_pct": 4.0},
        {"id": "lynch", "name": "Lynch", "value": 540.0, "weight": 1.0, "diff_pct": 8.0},
        {"id": "graham", "name": "Graham Outlier", "value": 21622.0, "weight": 1.0, "diff_pct": 4200.0},
        {"id": "wallst", "name": "Wall St", "value": 550.0, "weight": 1.0, "diff_pct": 10.0}
    ]
    summary = FundamentalService._synthesize_valuation(models, current_price=500.0)
    
    # El outlier debe quedar marcado
    graham_m = next(m for m in models if m["id"] == "graham")
    assert graham_m["is_outlier"] is True
    assert "outlier_reason" in graham_m
    
    # El promedio ponderado NO debe estar contaminado por 21,622
    # El promedio de 520, 540 y 550 es 536.67
    assert summary["average_fair_value"] == pytest.approx(536.67, rel=1e-2)
    assert summary["outliers_count"] == 1
    assert summary["verdict"] == "fair_value"

def test_calculate_justified_pb():
    # BVPS = $348.15, ROE = 12%, Beta = 1.0, Price = 500.0
    # Ke = 0.042 + 1.0 * 0.05 = 0.092. g = 0.025
    # Justified PB = (0.12 - 0.025) / (0.092 - 0.025) = 0.095 / 0.067 = 1.418x
    # Fair Value = 348.15 * 1.418 = 493.68
    model = FundamentalService._calculate_justified_pb(
        bvps=348.15,
        roe=0.12,
        beta=1.0,
        current_price=500.0
    )
    assert model is not None
    assert model["id"] == "justified_pb"
    assert model["value"] > 400.0
    assert model["value"] < 600.0
    assert "multiplo_pb_justificado" in model["assumptions"]

def test_dual_class_shares_brk_b_normalization():
    # Mock data para BRK-B con bookValue en Clase A ($522,225)
    from unittest.mock import patch
    mock_info = {
        "currentPrice": 500.0,
        "trailingEps": 39.79,
        "forwardEps": 21.64,
        "bookValue": 522225.9, # Class A book value
        "priceToBook": 0.000955,
        "sharesOutstanding": 1408000000,
        "marketCap": 1067000000000,
        "sector": "Financial Services",
        "returnOnEquity": 0.12,
        "targetMeanPrice": 550.0,
        "beta": 0.9
    }
    
    with patch("yfinance.Ticker") as mock_ticker:
        mock_instance = mock_ticker.return_value
        mock_instance.info = mock_info
        
        res = FundamentalService.get_fundamentals("BRK-B", force_refresh=True)
        assert res["current_price"] == 500.0
        
        # Graham no debe ser $21,622, sino calibrado a Class B (~$411 - $560)
        graham = next(m for m in res["models"] if m["id"] == "graham")
        assert graham["value"] < 700.0
        assert graham["value"] > 350.0
        
        # EV/EBITDA debe omitirse por ser sector financiero
        assert not any(m["id"] == "ev_ebitda" for m in res["models"])
        
        # Justified P/B debe estar presente
        assert any(m["id"] == "justified_pb" for m in res["models"])
        
        # El promedio no debe superar $700 (lejos de los $4000 anteriores)
        assert res["summary"]["average_fair_value"] < 700.0
        assert res["summary"]["average_fair_value"] > 350.0

def test_outlier_dual_anchor_preserves_wallst_consensus():
    """Wall Street Consensus nunca debe ser descartado como outlier aun si la mediana es baja."""
    models = [
        {"id": "dcf", "name": "DCF", "value": 15.0, "weight": 1.25, "diff_pct": -85.0},
        {"id": "graham", "name": "Graham", "value": 20.0, "weight": 0.85, "diff_pct": -80.0},
        {"id": "pe_multiple", "name": "P/E", "value": 95.0, "weight": 0.9, "diff_pct": -5.0},
        {"id": "wallst_consensus", "name": "Wall St", "value": 125.0, "weight": 1.1, "diff_pct": 25.0}
    ]
    # Mediana es (20 + 95) / 2 = 57.5.
    # 125 > 57.5 * 2.17, pero Wall St nunca se descarta
    summary = FundamentalService._synthesize_valuation(models, current_price=100.0)
    
    wallst_m = next(m for m in models if m["id"] == "wallst_consensus")
    assert wallst_m["is_outlier"] is False
    assert summary["average_fair_value"] > 50.0

def test_outlier_dual_anchor_preserves_market_corridor():
    """Modelos dentro del 35% - 250% del precio de mercado deben conservarse."""
    models = [
        {"id": "dcf", "name": "DCF", "value": 10.0, "weight": 1.25, "diff_pct": -90.0},
        {"id": "graham", "name": "Graham", "value": 12.0, "weight": 0.85, "diff_pct": -88.0},
        {"id": "peter_lynch", "name": "Lynch", "value": 90.0, "weight": 1.0, "diff_pct": -10.0},
        {"id": "pe_multiple", "name": "P/E", "value": 105.0, "weight": 0.9, "diff_pct": 5.0}
    ]
    # Precio actual $100. Lynch ($90) y P/E ($105) están en el corredor [35, 250].
    # DCF ($10) y Graham ($12) están por debajo del 25% del precio ($25) y de la mediana.
    summary = FundamentalService._synthesize_valuation(models, current_price=100.0)
    
    lynch_m = next(m for m in models if m["id"] == "peter_lynch")
    pe_m = next(m for m in models if m["id"] == "pe_multiple")
    dcf_m = next(m for m in models if m["id"] == "dcf")
    graham_m = next(m for m in models if m["id"] == "graham")
    
    assert lynch_m["is_outlier"] is False
    assert pe_m["is_outlier"] is False
    assert dcf_m["is_outlier"] is True
    assert graham_m["is_outlier"] is True
    
    # El promedio debe calcularse sobre Lynch y PE (~97.1), no contaminado por $10
    assert summary["average_fair_value"] > 85.0
    assert summary["average_fair_value"] < 110.0
    assert summary["outliers_count"] == 2

def test_outlier_dual_anchor_trims_extreme_aberrations():
    """Aberraciones extremas (ej. Graham a $21,622 en acción de $500) son podadas limpiamente."""
    models = [
        {"id": "pe_multiple", "name": "P/E", "value": 520.0, "weight": 1.0, "diff_pct": 4.0},
        {"id": "wallst_consensus", "name": "Wall St", "value": 550.0, "weight": 1.0, "diff_pct": 10.0},
        {"id": "graham", "name": "Graham Aberration", "value": 21622.0, "weight": 1.0, "diff_pct": 4200.0}
    ]
    summary = FundamentalService._synthesize_valuation(models, current_price=500.0)
    
    graham_m = next(m for m in models if m["id"] == "graham")
    assert graham_m["is_outlier"] is True
    assert "superior" in graham_m["outlier_reason"].lower() or "supera" in graham_m["outlier_reason"].lower()
    assert summary["average_fair_value"] < 600.0
    assert summary["outliers_count"] == 1

def test_wmt_calibration_scenario():
    """Simulación precisa del escenario Walmart (WMT): CapEx alto temporal no distorsiona el valor intrínseco."""
    current_price = 104.30
    models = [
        {"id": "dcf", "name": "DCF", "value": 9.56, "weight": 1.25, "diff_pct": -90.8},
        {"id": "graham", "name": "Graham", "value": 13.91, "weight": 0.85, "diff_pct": -86.7},
        {"id": "peter_lynch", "name": "Peter Lynch", "value": 92.10, "weight": 1.0, "diff_pct": -11.7},
        {"id": "pe_multiple", "name": "P/E Normalizado", "value": 98.50, "weight": 0.9, "diff_pct": -5.6},
        {"id": "wallst_consensus", "name": "Wall Street", "value": 126.78, "weight": 1.1, "diff_pct": 21.6}
    ]
    summary = FundamentalService._synthesize_valuation(models, current_price=current_price)
    
    # DCF y Graham deben ser outliers
    assert next(m for m in models if m["id"] == "dcf")["is_outlier"] is True
    assert next(m for m in models if m["id"] == "graham")["is_outlier"] is True
    
    # Lynch, PE y Wall Street deben ser válidos
    assert next(m for m in models if m["id"] == "peter_lynch")["is_outlier"] is False
    assert next(m for m in models if m["id"] == "pe_multiple")["is_outlier"] is False
    assert next(m for m in models if m["id"] == "wallst_consensus")["is_outlier"] is False
    
    # Promedio esperado ponderado de 92.10, 98.50 y 126.78:
    # (92.1*1.0 + 98.5*0.9 + 126.78*1.1) / (1.0 + 0.9 + 1.1) = (92.1 + 88.65 + 139.458) / 3.0 = 320.208 / 3.0 = 106.74
    assert summary["average_fair_value"] == pytest.approx(106.74, rel=1e-2)
    assert summary["verdict"] == "fair_value"
    assert summary["outliers_count"] == 2


