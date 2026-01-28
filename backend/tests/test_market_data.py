import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from fastapi.testclient import TestClient
# Adjusting import based on project structure where tests are run from root or backend/
try:
    from backend.main import app
except ImportError:
    from main import app

client = TestClient(app)

# Mock Dataframe Helper
def create_mock_dataframe(rows=5):
    dates = pd.date_range(start="2023-01-01", periods=rows, freq="D")
    df = pd.DataFrame({'Close': [150.0 + i for i in range(rows)]}, index=dates)
    return df

@patch("backend.routers.market.yf.Ticker")
def test_history_1y_defaults_to_daily(mock_ticker):
    # Configurar el Mock
    mock_instance = MagicMock()
    mock_instance.history.return_value = create_mock_dataframe()
    mock_ticker.return_value = mock_instance

    response = client.get("/api/market/history/AAPL?range=1y")
    
    assert response.status_code == 200
    json_resp = response.json()
    assert "data" in json_resp
    data = json_resp["data"]
    assert len(data) == 5
    # Verificar que se llamó con interval='1d'
    mock_instance.history.assert_called_with(period="1y", interval="1d", auto_adjust=True)

@patch("backend.routers.market.yf.Ticker")
def test_history_1d_uses_hourly(mock_ticker):
    mock_instance = MagicMock()
    mock_instance.history.return_value = create_mock_dataframe()
    mock_ticker.return_value = mock_instance

    response = client.get("/api/market/history/AAPL?range=1d")
    
    # Verificar que se llamó con interval='1h'
    mock_instance.history.assert_called_with(period="1d", interval="1h", auto_adjust=True)

@patch("backend.routers.market.yf.Ticker")
def test_handle_empty_data(mock_ticker):
    mock_instance = MagicMock()
    # Simular DataFrame vacío
    mock_instance.history.return_value = pd.DataFrame()
    mock_ticker.return_value = mock_instance

    response = client.get("/api/market/history/UNKNOWN")
    assert response.status_code == 200
    assert response.json() == {"data": []}
