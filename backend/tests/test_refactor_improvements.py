import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from datetime import datetime
import json

from main import app
from database import get_session
from models.models import Asset, Transaction, TradeHistory, BrokerCash, BrokerSettings
from services.oracle_service import OracleService, OracleRule
from utils.money import to_cents, to_dollars, safe_float

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

def test_transactions_crud(client, session):
    # 1. Create Transaction
    res_create = client.post("/api/movimientos/", json={
        "tipo": "gasto",
        "monto": 45.50,
        "moneda": "USD",
        "categoria": "Supermercado"
    })
    assert res_create.status_code == 200
    created = res_create.json()
    tx_id = created["id"]
    assert created["monto"] == 45.50

    # 2. Update Transaction (PUT)
    res_update = client.put(f"/api/movimientos/{tx_id}", json={
        "monto": 50.00,
        "categoria": "Supermercado Mayorista"
    })
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["monto"] == 50.00
    assert updated["categoria"] == "Supermercado Mayorista"

    # 3. Delete Transaction (DELETE)
    res_delete = client.delete(f"/api/movimientos/{tx_id}")
    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "success"

    # Verify not found
    res_get_deleted = client.delete(f"/api/movimientos/{tx_id}")
    assert res_get_deleted.status_code == 404

def test_complete_backup_export_and_import(client, session):
    # Setup initial state
    session.add(BrokerCash(id=1, saldo_usd=50000))
    session.add(BrokerSettings(id=1, default_fee_integer=100, default_fee_fractional=50))
    session.add(TradeHistory(
        ticker="NVDA",
        tipo="BUY",
        cantidad=5.0,
        precio=12000,
        total=60000,
        commission=100,
        fecha=datetime(2025, 5, 10, 12, 0)
    ))
    session.commit()

    # 1. Export Data
    res_export = client.get("/api/data/export")
    assert res_export.status_code == 200
    backup_data = res_export.json()

    assert "trades" in backup_data
    assert "broker_cash" in backup_data
    assert "broker_settings" in backup_data
    assert len(backup_data["trades"]) == 1
    assert backup_data["broker_cash"]["saldo_usd"] == 50000
    assert backup_data["broker_settings"]["default_fee_integer"] == 100

    # 2. Clear & Import in fresh DB session
    file_bytes = json.dumps(backup_data).encode("utf-8")
    files = {"file": ("backup.json", file_bytes, "application/json")}
    res_import = client.post("/api/data/import?strategy=merge", files=files)
    assert res_import.status_code == 200

    trades = session.exec(select(TradeHistory)).all()
    assert len(trades) >= 1

def test_oracle_custom_rule():
    class CustomCryptoRule(OracleRule):
        def evaluate(self, risk_metrics, valuation_data, net_worth, cash_balance):
            return [{
                "type": "info",
                "title": "Crypto Opportunity",
                "message": "Testing custom rule extension",
                "action_suggested": "HODL"
            }]

    OracleService.register_rule(CustomCryptoRule())
    insights = OracleService.generate_insights(
        risk_metrics={"sharpe_ratio": 1.0, "beta": 1.0, "max_drawdown_pct": 0},
        valuation_data=[],
        net_worth=5000,
        cash_balance=500
    )
    titles = [i["title"] for i in insights]
    assert "Crypto Opportunity" in titles

def test_money_utils():
    assert to_cents(10.55) == 1055
    assert to_cents(0) == 0
    assert to_dollars(1055) == 10.55
    assert safe_float(None) == 0.0
    assert safe_float("invalid") == 0.0
