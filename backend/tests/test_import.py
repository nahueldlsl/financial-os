from models.models import Asset
from services.import_service import ImportService
import json

def test_import_snapshot_create(session):
    # JSON user example
    json_content = json.dumps([
        { "Ticker": "ADBE", "Cantidad_Total": 0.03047, "Precio_Promedio": 370.8 }
    ])
    
    ImportService.import_snapshot(session, json_content)
    
    # Check creation
    asset = session.query(Asset).first()
    assert asset is not None
    assert asset.ticker == "ADBE" # Normalized
    assert asset.cantidad_total == 0.03047
    assert asset.precio_promedio == 37080 # 370.8 * 100

def test_import_snapshot_update(session):
    # Create initial asset (Lowercase ticker as consistent with normalization)
    session.add(Asset(ticker="AAPL", cantidad_total=1.0, precio_promedio=10000))
    session.commit()
    
    # Update via Import
    json_content = json.dumps([
        { "Ticker": "AAPL", "Cantidad_Total": 10.5, "Precio_Promedio": 150.0 }
    ])
    
    ImportService.import_snapshot(session, json_content)
    
    asset = session.query(Asset).filter(Asset.ticker == "AAPL").first()
    assert asset.cantidad_total == 10.5
    assert asset.precio_promedio == 15000

def test_import_snapshot_case_insensitive_lookup(session):
    # Setup asset with lowercase
    session.add(Asset(ticker="MSFT", cantidad_total=10, precio_promedio=20000))
    session.commit()

    # Import with uppercase Ticker
    json_content = json.dumps([
        { "Ticker": "MSFT", "Cantidad_Total": 20, "Precio_Promedio": 250.0 }
    ])
    
    ImportService.import_snapshot(session, json_content)
    
    # Should update existing, not create new
    # NOTE: Since we normalize to UPPER in code, the existing "msft" might be considered different if DB is case sensitive.
    # HOWEVER, the requirement is "Normaliza... Elimina espacios y fuerza MAYUSCULAS".
    # If DB has "msft", and we import "MSFT" -> "MSFT", select(Asset).where(ticker=="MSFT") will NOT find "msft" (unless collation is insensitive).
    # The previous test assumed we want to MATCH "msft".
    # But if we force Upper, "msft" (old) vs "MSFT" (new).
    # If we want to strictly enforce UPPER, the old "msft" is technically "wrong" data now or a different asset.
    # BUT, to be "tolerant", usually we want to migrate or match case-insensitively.
    # The user instruction was explicit: "ticker_limpio = ... .upper() ... Usa este ticker limpio para buscar en la DB".
    # So if DB has "msft", it won't be found. It will create "MSFT".
    # So "msft" and "MSFT" would duplicate.
    
    # Let's adjust the test to "Setup asset with UPPERCASE" to verify the main happy path of consistency.
    # Or if we want to verify case-insensitive matching failure behavior (it creates a new one).
    # Given the user instruction, correct behavior is to use UPPER.
    # I will change the setup to use "MSFT" to match the new strict world, OR check that it fixes it.
    
    # Actually, let's stick to the simplest verification: New logic produces UPPER.
    # So I will update the test to expect UPPER everywhere.
    
    pass 
    
    # START REPLACEMENT
    
    # Check creation
    asset = session.query(Asset).first()
    assert asset is not None
    assert asset.ticker == "ADBE" # Normalized
    assert asset.cantidad_total == 0.03047
    assert asset.precio_promedio == 37080 # 370.8 * 100

def test_import_snapshot_update(session):
    # Create initial asset (Upper ticker)
    session.add(Asset(ticker="AAPL", cantidad_total=1.0, precio_promedio=10000))
    session.commit()
    
    # Update via Import
    json_content = json.dumps([
        { "Ticker": "AAPL", "Cantidad_Total": 10.5, "Precio_Promedio": 150.0 }
    ])
    
    ImportService.import_snapshot(session, json_content)
    
    asset = session.query(Asset).filter(Asset.ticker == "AAPL").first()
    assert asset.cantidad_total == 10.5
    assert asset.precio_promedio == 15000

def test_import_snapshot_case_insensitive_lookup(session):
    # Setup asset with lowercase - THIS MIGHT BE DUPLICATED now if we don't migrate.
    # But for the purpose of the ImportService test, we want to see what happens.
    # If the logic is "Clean input -> Upper", then it looks for "MSFT".
    # If DB has "msft", it won't find it (in standard SQLModel/QA).
    # So it will create "MSFT".
    # I will simplify the test: Ensure we can handle mixed case INPUT and it becomes Upper.
    
    session.add(Asset(ticker="MSFT", cantidad_total=10, precio_promedio=20000))
    session.commit()

    # Import with lowercase Ticker (Reverse of previous test)
    json_content = json.dumps([
        { "Ticker": "msft", "Cantidad_Total": 20, "Precio_Promedio": 250.0 }
    ])
    
    ImportService.import_snapshot(session, json_content)
    
    # Should update existing "MSFT"
    assert session.query(Asset).count() == 1
    asset = session.query(Asset).first()
    asset_ticker = asset.ticker
    assert asset_ticker == "MSFT"
    assert asset.cantidad_total == 20
    assert asset.precio_promedio == 25000
