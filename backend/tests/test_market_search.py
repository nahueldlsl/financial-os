from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_search_empty_query():
    response = client.get("/api/market/search?q=")
    assert response.status_code == 200
    data = response.json()
    assert data == {"results": []}

def test_search_valid_ticker():
    response = client.get("/api/market/search?q=TSLA")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0
    symbols = [r["symbol"] for r in data["results"]]
    assert any("TSLA" in s for s in symbols)
    first = data["results"][0]
    assert "symbol" in first
    assert "name" in first
    assert "exchange" in first
    assert "type" in first

def test_search_company_name():
    response = client.get("/api/market/search?q=Microsoft")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0
    symbols = [r["symbol"] for r in data["results"]]
    assert any("MSFT" in s for s in symbols)
