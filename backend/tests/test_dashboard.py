from unittest.mock import patch
from models.models import Asset, Transaction, BrokerCash

def test_dashboard_smoke(client):
    """
    Verifica que el endpoint responde 200 y tiene la estructura correcta
    incluso si la base de datos está vacía.
    """
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "net_worth" in data
    assert "assets" in data
    assert data["net_worth"] == 0

def test_dashboard_net_worth_calculation(client, session):
    """
    Verifica el cálculo matemático exacto del Net Worth:
    (Cantidad Acciones * Precio Mock) + (Ingresos - Gastos) + Saldo Broker
    """
    # 1. Seeding (Datos de Prueba)
    
    # Activo: 10 acciones de AAPL (Precio promedio irrelevante para valor actual, pero seteamos 150)
    asset = Asset(ticker="AAPL", cantidad_total=10.0, precio_promedio=150.0)
    session.add(asset)
    
    # Transacción (Cash Flow): Ingreso de 1000 USD (banco)
    tx = Transaction(tipo="ingreso", monto=1000.0, moneda="USD", categoria="Sueldo")
    session.add(tx)
    
    # Saldo Broker: 500 USD sin invertir
    broker = BrokerCash(id=1, saldo_usd=500.0)
    session.add(broker)
    
    session.commit()

    # 2. Mocking Market Data
    # Simulamos que AAPL vale $200 hoy.
    # El path debe ser donde se IMPORTA MarketDataService en el router, o la clase misma.
    # Dado que el router usa dashboard.MarketDataService (importado), mockeamos la clase.
    with patch("services.portfolio_service.MarketDataService.get_market_prices") as mock_prices:
        mock_prices.return_value = {"AAPL": 200.0}
        
        # 3. Execution
        response = client.get("/api/dashboard")
        
    # 4. Assertions
    assert response.status_code == 200
    data = response.json()
    
    # Cálculo Esperado:
    # Portafolio: 10 * 200 = 2000
    # Cash Flow: 1000
    # Broker Cash: 500
    # Total = 3500
    
    assert data["net_worth"] == 3500.0
    
    # Verificar desglose si tu API lo devuelve (opcional, ajusta según tu respuesta real)
    # Por ejemplo si devuelve 'portfolio_value'
    if "portfolio_value" in data:
        assert data["portfolio_value"] == 2000.0
