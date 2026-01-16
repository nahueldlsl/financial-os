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
    
    # 3. Verificar persistencia
    settings = session.get(BrokerSettings, 1)
    assert settings.default_fee_integer == 1.5
    assert settings.default_fee_fractional == 0.5

def test_buy_with_fee(client, session):
    """
    Verifica COMPRA con comisión aplicada manualmente.
    Costo Total = (Qty * Price) + Fee
    """
    # Setup: Fondear Broker con 2000 USD
    session.add(BrokerCash(id=1, saldo_usd=2000.0))
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
    # 1. Saldo Broker: 2000 - (1500 + 2.5) = 497.5
    
    broker = session.get(BrokerCash, 1)
    assert broker.saldo_usd == 497.5

    # 2. Historial Guardado con Comisión
    trade = session.query(TradeHistory).order_by(TradeHistory.id.desc()).first()
    assert trade.commission == 2.5
    assert trade.total == 1502.5

def test_sell_with_fee(client, session):
    """
    Verifica VENTA con comisión.
    Neto Recibido = (Qty * Price) - Fee
    """
    # Setup: Tener Activos y algo de saldo
    session.add(BrokerCash(id=1, saldo_usd=0.0))
    session.add(Asset(ticker="GOOGL", cantidad_total=5.0, precio_promedio=100.0))
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

    # 1. Saldo Broker debe haber subido 995
    broker = session.get(BrokerCash, 1)
    assert broker.saldo_usd == 995.0

    # 2. Historial
    trade = session.query(TradeHistory).first()
    assert trade.commission == 5.0
    assert trade.total == 995.0 # Total registrado es el neto
    assert trade.ganancia_realizada == (995.0 - (5.0 * 100.0)) # 995 - 500 = 495
