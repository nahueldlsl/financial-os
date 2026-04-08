import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from main import app
from database import get_session
from models.models import Asset, Transaction
from datetime import datetime
import json

# Setup in-memory DB for testing
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_export_empty(client):
    response = client.get("/api/data/export")
    assert response.status_code == 200
    data = response.json()
    assert data["assets"] == []
    assert data["transactions"] == []

def test_import_and_export(client):
    # 1. Create Data to Import
    import_data = {
        "assets": [
            {"ticker": "TEST", "cantidad_total": 10.0, "precio_promedio": 1000}
        ],
        "transactions": [
            {
                "tipo": "BUY",
                "monto": 10000,
                "moneda": "USD",
                "categoria": "Invest",
                "fecha": datetime.now().isoformat()
            }
        ]
    }
    
    # 2. Upload JSON
    import json
    file_content = json.dumps(import_data).encode('utf-8')
    files = {'file': ('backup.json', file_content, 'application/json')}
    
    response = client.post("/api/data/import?strategy=merge", files=files)
    assert response.status_code == 200
    assert response.json()["message"] == "Datos importados exitosamente"

    # 3. Verify Export contains data
    response = client.get("/api/data/export")
    assert response.status_code == 200
    data = response.json()
    assert len(data["assets"]) == 1
    assert data["assets"][0]["ticker"] == "TEST"
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["monto"] == 10000

def test_smart_merge_update(client):
    # 1. Setup Initial State
    import_data_1 = {
        "assets": [{"ticker": "AAPL", "cantidad_total": 5.0, "precio_promedio": 15000}]
    }
    files1 = {'file': ('backup1.json', json.dumps(import_data_1).encode('utf-8'), 'application/json')}
    client.post("/api/data/import", files=files1)

    # 2. Upload "Newer" Data (Merge)
    import_data_2 = {
        "assets": [{"ticker": "AAPL", "cantidad_total": 10.0, "precio_promedio": 15500}] 
    }
    files2 = {'file': ('backup2.json', json.dumps(import_data_2).encode('utf-8'), 'application/json')}
    client.post("/api/data/import", files=files2)

    # 3. Verify Update
    response = client.get("/api/data/export")
    data = response.json()
    asset = data["assets"][0]
    assert asset["ticker"] == "AAPL"
    assert asset["cantidad_total"] == 10.0
    assert asset["precio_promedio"] == 15500
