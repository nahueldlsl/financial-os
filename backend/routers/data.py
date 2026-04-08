from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlmodel import Session, select
from database import get_session
from models.models import Asset, Transaction
from services.import_strategies import ImportContext, SmartMergeStrategy
from services.broker_import_service import BrokerImportService
import json
from typing import Dict, List, Any

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("/export")
def export_data(session: Session = Depends(get_session)):
    """
    Exporta todo el contenido de Assets y Transactions.
    """
    assets = session.exec(select(Asset)).all()
    transactions = session.exec(select(Transaction)).all()

    return {
        "assets": [asset.model_dump() for asset in assets],
        "transactions": [tx.model_dump() for tx in transactions]
    }

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
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="El archivo debe ser JSON")

    try:
        content = await file.read()
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Selección de Estrategia (OCP: Se pueden agregar más aquí sin romper lo demás)
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
    if not historial_file.filename.endswith('.json') or not posiciones_file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Los archivos deben ser formato .json")

    try:
        historial_content = await historial_file.read()
        posiciones_content = await posiciones_file.read()
        
        historial_json = json.loads(historial_content)
        posiciones_json = json.loads(posiciones_content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido proporcionado en los archivos")
        
    try:
        BrokerImportService.process_broker_data(session, historial_json, posiciones_json)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error cruzando los datos: {str(e)}")
        
    return {"message": "Tus acciones fueron actualizadas correctamente en base a los 2 JSONs"}
