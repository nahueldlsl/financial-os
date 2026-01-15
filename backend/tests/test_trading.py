from models.models import Asset, BrokerCash, Transaction

def test_trade_buy_execution(client, session):
    """
    Verifica el ciclo completo de COMPRA:
    - Descuenta saldo del broker
    - Aumenta cantidad de activo
    - Crea, historial
    """
    # Setup: Fondear Broker con 1000 USD
    session.add(BrokerCash(id=1, saldo_usd=1000.0))
    session.commit()

    payload = {
        "ticker": "TSLA",
        "cantidad": 2.0,
        "precio": 200.0, # Costo total 400
        "usar_caja_broker": True
    }

    response = client.post("/api/trade/buy", json=payload)
    
    assert response.status_code == 200
    
    # Verificar Saldo Broker (1000 - 400 = 600)
    broker = session.get(BrokerCash, 1)
    assert broker.saldo_usd == 600.0
    
    # Verificar Activo Creado
    assets = session.query(Asset).all()
    assert len(assets) == 1
    assert assets[0].ticker == "TSLA"
    assert assets[0].cantidad_total == 2.0

def test_fund_validation_insufficient_funds(client, session):
    """
    Verifica que NO se permita retirar más dinero del disponible.
    """
    # Setup: Broker con 100 USD
    session.add(BrokerCash(id=1, saldo_usd=100.0))
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
    assert broker.saldo_usd == 1000.0
    
    # 2. Verificar efecto secundario: Transacción creada
    txs = session.query(Transaction).all()
    assert len(txs) == 1
    assert txs[0].tipo == "gasto"
    assert txs[0].monto == 1000.0
    assert txs[0].categoria == "Transferencia a Broker"
