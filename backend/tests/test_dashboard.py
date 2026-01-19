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
    
    # Activo: 10 acciones de AAPL 
    # Precio Promedio en CENTAVOS: 150.00 -> 15000
    asset = Asset(ticker="AAPL", cantidad_total=10.0, precio_promedio=15000)
    session.add(asset)
    
    # Transacción (Cash Flow): Ingreso de 1000 USD (banco)
    # Monto en CENTAVOS: 1000.00 -> 100000
    tx = Transaction(tipo="ingreso", monto=100000, moneda="USD", categoria="Sueldo")
    session.add(tx)
    
    # Saldo Broker: 500 USD sin invertir
    # Saldo en CENTAVOS: 500.00 -> 50000
    broker = BrokerCash(id=1, saldo_usd=50000)
    session.add(broker)
    
    session.commit()

    # 2. Mocking Market Data
    # Simulamos que AAPL vale $200 hoy.
    # El servicio espera enteros (centavos): 200.00 -> 20000
    with patch("services.portfolio_service.MarketDataService.get_market_prices") as mock_prices:
        mock_prices.return_value = {"AAPL": 20000}
        
        # 3. Execution
        response = client.get("/api/dashboard")
        
    # 4. Assertions
    assert response.status_code == 200
    data = response.json()
    
    # Cálculo Esperado (API devuelve Floats):
    # Portafolio: 10 * 200.00 = 2000.00
    # Cash Flow: 1000.00
    # Broker Cash: 500.00
    # Total = 3500.00
    
    assert data["net_worth"] == 3500.0
    
    # Verificar desglose si tu API lo devuelve (opcional, ajusta según tu respuesta real)
    # Por ejemplo si devuelve 'portfolio_value'
    if "portfolio_value" in data:
        assert data["portfolio_value"] == 2000.0
