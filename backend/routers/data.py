from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlmodel import Session, select
from database import get_session
from models.models import Asset, Transaction, TradeHistory, BrokerCash, BrokerSettings
from services.import_strategies import ImportContext, SmartMergeStrategy
from services.broker_import_service import BrokerImportService
import json
from typing import Dict, List, Any

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("/export")
def export_data(session: Session = Depends(get_session)):
    """
    Exporta todo el contenido de Assets, Transactions, TradeHistory, BrokerCash y BrokerSettings.
    """
    assets = session.exec(select(Asset)).all()
    transactions = session.exec(select(Transaction)).all()
    trades = session.exec(select(TradeHistory)).all()
    broker_cash = session.get(BrokerCash, 1)
    broker_settings = session.get(BrokerSettings, 1)

    return {
        "assets": [asset.model_dump() for asset in assets],
        "transactions": [tx.model_dump() for tx in transactions],
        "trades": [trade.model_dump() for trade in trades],
        "broker_cash": broker_cash.model_dump() if broker_cash else None,
        "broker_settings": broker_settings.model_dump() if broker_settings else None,
    }

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

async def read_json_upload(file: UploadFile, max_bytes: int = MAX_UPLOAD_SIZE) -> Any:
    filename = (file.filename or "").lower()
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="El archivo debe tener formato .json")
    
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Archivo demasiado grande (máximo {max_bytes // (1024 * 1024)} MB)")
    
    try:
        return json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="El archivo no contiene un JSON válido")

@router.post("/import")
async def import_data(
    file: UploadFile = File(...),
    strategy: str = Query("merge", description="Estrategia de importación: 'merge' (default)"),
    session: Session = Depends(get_session)
):
    """
    Importa datos desde un archivo JSON usando una estrategia definida.
    Default: 'merge' (Smart Merge).
    """
    data = await read_json_upload(file)

    # Selección de Estrategia
    if strategy == "merge":
        import_strategy = SmartMergeStrategy()
    else:
        raise HTTPException(status_code=400, detail=f"Estrategia '{strategy}' no soportada")

    # Ejecución
    context = ImportContext(import_strategy)
    try:
        context.execute_import(session, data)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la importación: {str(e)}")

    return {"message": "Datos importados exitosamente", "strategy": strategy}

@router.post("/import-broker")
async def import_broker_data(
    historial_file: UploadFile = File(..., description="Archivo historial_transacciones.json"),
    posiciones_file: UploadFile = File(..., description="Archivo posiciones_actuales.json"),
    session: Session = Depends(get_session)
):
    """
    Importa datos directos del Broker cruzando Historial + Posiciones.
    Crea o actualiza los Assets (Acciones) con Costo Base exacto.
    """
    historial_json = await read_json_upload(historial_file)
    posiciones_json = await read_json_upload(posiciones_file)
    
    if not isinstance(historial_json, list) or not isinstance(posiciones_json, list):
        raise HTTPException(status_code=400, detail="Los archivos de broker deben contener listas JSON")
        
    try:
        BrokerImportService.process_broker_data(session, historial_json, posiciones_json)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error cruzando los datos: {str(e)}")
        
    return {"message": "Tus acciones fueron actualizadas correctamente en base a los 2 JSONs"}
