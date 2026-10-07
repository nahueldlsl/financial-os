import pytest
from services.technical_service import TechnicalService

def test_evaluate_timing_oversold():
    # RSI = 28 (Sobrevendido)
    verdict, label, color, score = TechnicalService._evaluate_timing(
        current_rsi=28.0,
        pct_b=0.05,
        dist_sma_200=-15.0,
        current_price=80.0,
        sma_50=85.0,
        sma_200=95.0,
        macd_hist=-0.5
    )
    assert verdict == "oversold"
    assert color == "emerald"
    assert score == 28

def test_evaluate_timing_overbought():
    # RSI = 78 (Sobrecomprado)
    verdict, label, color, score = TechnicalService._evaluate_timing(
        current_rsi=78.0,
        pct_b=0.95,
        dist_sma_200=32.0,
        current_price=200.0,
        sma_50=180.0,
        sma_200=150.0,
        macd_hist=1.2
    )
    assert verdict == "overbought"
    assert color == "red"
    assert score == 78

def test_evaluate_timing_bullish():
    # RSI = 58, precio > SMA 50 > SMA 200, MACD positivo
    verdict, label, color, score = TechnicalService._evaluate_timing(
        current_rsi=58.0,
        pct_b=0.60,
        dist_sma_200=12.0,
        current_price=160.0,
        sma_50=150.0,
        sma_200=140.0,
        macd_hist=0.8
    )
    assert verdict == "bullish_trend"
    assert color == "green"

def test_confluence_strong_buy():
    # Fundamental: 25% descuento + Técnico: Sobrevendido
    v_id, title, color, advice = TechnicalService._synthesize_confluence(
        fund_verdict="deeply_undervalued",
        fund_discount=25.0,
        tech_verdict="oversold",
        is_etf=False
    )
    assert v_id == "strong_buy_confluence"
    assert color == "emerald"
    assert "Compra Óptima" in title

def test_confluence_value_trap():
    # Fundamental: 20% descuento + Técnico: Tendencia bajista activa
    v_id, title, color, advice = TechnicalService._synthesize_confluence(
        fund_verdict="undervalued",
        fund_discount=20.0,
        tech_verdict="bearish_trend",
        is_etf=False
    )
    assert v_id == "value_trap_alert"
    assert color == "amber"
    assert "Trampa de Valor" in title

def test_confluence_correction_risk():
    # Fundamental: Sobrevalorada (-25%) + Técnico: Sobrecomprada
    v_id, title, color, advice = TechnicalService._synthesize_confluence(
        fund_verdict="deeply_overvalued",
        fund_discount=-30.0,
        tech_verdict="overbought",
        is_etf=False
    )
    assert v_id == "correction_danger"
    assert color == "red"
    assert "Riesgo Alto de Corrección" in title

def test_confluence_momentum_trade():
    # Fundamental: Sobrevalorada (-18%) + Técnico: Muy alcista
    v_id, title, color, advice = TechnicalService._synthesize_confluence(
        fund_verdict="overvalued",
        fund_discount=-18.0,
        tech_verdict="bullish_trend",
        is_etf=False
    )
    assert v_id == "momentum_ride"
    assert color == "orange"
    assert "Momentum" in title

def test_confluence_etf():
    v_id, title, color, advice = TechnicalService._synthesize_confluence(
        fund_verdict="etf_index",
        fund_discount=0.0,
        tech_verdict="neutral",
        is_etf=True
    )
    assert v_id == "etf_index"
    assert color == "blue"
