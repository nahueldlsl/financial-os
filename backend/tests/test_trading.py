from models.models import Asset, BrokerCash, Transaction

def test_trade_buy_execution(client, session):
    """
    Verifica el ciclo completo de COMPRA:
    - Descuenta saldo del broker
    - Aumenta cantidad de activo
    - Crea, historial
    """
    # Setup: Fondear Broker con 1000 USD -> 100000 cents
    session.add(BrokerCash(id=1, saldo_usd=100000))
    session.commit()

    payload = {
        "ticker": "TSLA",
        "cantidad": 2.0,
        "precio": 200.0, # Costo total 400.0 USD
        "usar_caja_broker": True
    }

    response = client.post("/api/trade/buy", json=payload)
    
    assert response.status_code == 200
    
    # Verificar Saldo Broker (1000 - 400 = 600) -> 60000 cents
    broker = session.get(BrokerCash, 1)
    assert broker.saldo_usd == 60000
    
    # Verificar Activo Creado
    assets = session.query(Asset).all()
    assert len(assets) == 1
    assert assets[0].ticker == "TSLA"
    assert assets[0].cantidad_total == 2.0

def test_fund_validation_insufficient_funds(client, session):
    """
    Verifica que NO se permita retirar más dinero del disponible.
    """
    # Setup: Broker con 100 USD -> 10000 cents
    session.add(BrokerCash(id=1, saldo_usd=10000))
    session.commit()

    payload = {
        "monto_enviado": 500.0, # Intentar sacar 500
        "monto_recibido": 500.0,
        "tipo": "WITHDRAW"
    }

    response = client.post("/api/broker/fund", json=payload)
    
    assert response.status_code == 400
    assert "saldo insuficiente" in response.json()["detail"].lower()

def test_fund_deposit_side_effect_transaction(client, session):
    """
    Verifica que al depositar en el broker, se cree automáticamente
    una transacción de 'GASTO' en la tabla Transaction (Cash Flow principal),
    reflejando la salida de dinero del 'bolsillo' del usuario hacia el broker.
    """
    # Setup: Broker vacío
    session.add(BrokerCash(id=1, saldo_usd=0.0))
    session.commit()

    payload = {
        "monto_enviado": 1000.0,
        "monto_recibido": 1000.0,
        "tipo": "DEPOSIT"
    }

    response = client.post("/api/broker/fund", json=payload)
    
    assert response.status_code == 200
    
    # 1. Verificar saldo broker creció
    broker = session.get(BrokerCash, 1)
    assert broker.saldo_usd == 100000 # Cents
    
    # 2. Verificar efecto secundario: Transacción creada
    txs = session.query(Transaction).all()
    assert len(txs) == 1
    assert txs[0].tipo == "gasto"
    assert txs[0].monto == 100000 # Cents
    assert txs[0].categoria == "Transferencia a Broker"

def test_portfolio_trade_bilingual_support(client, session):
    """
    Verifica que /api/portfolio/trade acepte tanto esquemas en español
    (cantidad, precio, fecha) como en inglés (quantity, price, date).
    """
    session.add(BrokerCash(id=1, saldo_usd=500000))
    session.commit()

    # 1. Compra con campos en español (enviados desde TradeModal / usePortfolio)
    res_es = client.post("/api/portfolio/trade", json={
        "ticker": "MSFT",
        "type": "BUY",
        "cantidad": 1.0,
        "precio": 300.0,
        "fecha": "2026-10-05T00:00:00Z",
        "usar_caja_broker": True,
        "applied_fee": 1.5
    })
    assert res_es.status_code == 200

    asset_msft = session.query(Asset).filter(Asset.ticker == "MSFT").first()
    assert asset_msft is not None
    assert asset_msft.cantidad_total == 1.0

    # 2. Compra con campos en inglés (esquema original)
    res_en = client.post("/api/portfolio/trade", json={
        "ticker": "GOOGL",
        "type": "BUY",
        "quantity": 2.0,
        "price": 150.0,
        "date": "2026-10-05T00:00:00Z",
        "usar_caja_broker": True,
        "applied_fee": 2.0
    })
    assert res_en.status_code == 200

    asset_googl = session.query(Asset).filter(Asset.ticker == "GOOGL").first()
    assert asset_googl is not None
    assert asset_googl.cantidad_total == 2.0

    # 3. Validación de campos obligatorios faltantes
    res_invalid = client.post("/api/portfolio/trade", json={
        "ticker": "AMZN",
        "type": "BUY",
        "usar_caja_broker": True
    })
    assert res_invalid.status_code == 400

