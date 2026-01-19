from models.models import BrokerCash, Asset, TradeHistory, BrokerSettings

def test_settings_defaults(client, session):
    """
    Verifica que se puedan leer y escribir los settings de comisiones.
    """
    # 1. Leer default (debe crearse solo)
    response = client.get("/api/settings/")
    assert response.status_code == 200
    data = response.json()
    assert data["default_fee_integer"] == 0.0
    assert data["default_fee_fractional"] == 0.0

    # 2. Actualizar defaults
    payload = {
        "default_fee_integer": 1.5,
        "default_fee_fractional": 0.5
    }
    response = client.post("/api/settings/", json=payload)
    assert response.status_code == 200
    
    # 3. Verificar persistencia (Stored as CENTS or Floats?)
    # BrokerSettings default_fee_integer is INT in DB (cents) or still float?
    # Let's check models.py... default_fee_integer: int.
    # So 1.5 -> 150 cents.
    settings = session.get(BrokerSettings, 1)
    assert settings.default_fee_integer == 150
    assert settings.default_fee_fractional == 50

def test_buy_with_fee(client, session):
    """
    Verifica COMPRA con comisión aplicada manualmente.
    Costo Total = (Qty * Price) + Fee
    """
    # Setup: Fondear Broker con 2000 USD -> 200000 cents
    session.add(BrokerCash(id=1, saldo_usd=200000))
    session.commit()

    payload = {
        "ticker": "AAPL",
        "cantidad": 10.0,
        "precio": 150.0, # 1500 USD
        "applied_fee": 2.5, # Comision manual
        "usar_caja_broker": True
    }

    # Ejecutar Compra
    response = client.post("/api/trade/buy", json=payload)
    assert response.status_code == 200

    # Verificaciones
    # 1. Saldo Broker: 2000 - (1500 + 2.5) = 497.5 -> 49750 cents
    
    broker = session.get(BrokerCash, 1)
    assert broker.saldo_usd == 49750

    # 2. Historial Guardado con Comisión (CENTS)
    trade = session.query(TradeHistory).order_by(TradeHistory.id.desc()).first()
    assert trade.commission == 250
    assert trade.total == 150250

def test_sell_with_fee(client, session):
    """
    Verifica VENTA con comisión.
    Neto Recibido = (Qty * Price) - Fee
    """
    # Setup: Tener Activos y algo de saldo
    session.add(BrokerCash(id=1, saldo_usd=0))
    # Precio Promedio en Cents: 100.0 -> 10000
    session.add(Asset(ticker="GOOGL", cantidad_total=5.0, precio_promedio=10000))
    session.commit()

    payload = {
        "ticker": "GOOGL",
        "cantidad": 5.0, 
        "precio": 200.0, # Bruto: 1000
        "applied_fee": 5.0, # Neto: 995
        "usar_caja_broker": True
    }

    response = client.post("/api/trade/sell", json=payload)
    assert response.status_code == 200

    # 1. Saldo Broker debe haber subido 995 -> 99500 cents
    broker = session.get(BrokerCash, 1)
    assert broker.saldo_usd == 99500

    # 2. Historial
    trade = session.query(TradeHistory).first()
    assert trade.commission == 500
    assert trade.total == 99500 # Total registrado es el neto
    # Ganancia: (Precio Venta * Cantidad - Comision) - (Precio Compra * Cantidad)
    # (20000 * 5) - 500 - (10000 * 5) = 100000 - 500 - 50000 = 49500
    assert trade.ganancia_realizada == 49500
