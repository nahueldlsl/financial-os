# routers/transactions.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List
from database import get_session
from models.models import Transaction
from models.schemas import TransactionCreate
from datetime import datetime

router = APIRouter(prefix="/api/movimientos", tags=["movimientos"])

# Helper para convertir Transaction (cents) a Dict (dollars) 
def transaction_to_dict(t: Transaction):
    return {
        "id": t.id,
        "tipo": t.tipo,
        "monto": t.monto / 100.0, # Convert back to Float Dollars
        "moneda": t.moneda,
        "categoria": t.categoria,
        "fecha": t.fecha.isoformat() if t.fecha else None
    }

@router.get("/")
def leer_movimientos(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    # SELECT * FROM transaction LIMIT limit OFFSET skip
    movimientos = session.exec(select(Transaction).order_by(Transaction.fecha.desc()).offset(skip).limit(limit)).all()
    # Convertimos los montos (cents) a dolares (float) para el frontend
    return [transaction_to_dict(m) for m in movimientos]

@router.post("/")
def agregar_movimiento(movimiento_in: TransactionCreate, session: Session = Depends(get_session)):
    # Convert float dollars -> int cents
    monto_cents = int(round(movimiento_in.monto * 100))
    
    nuevo_movimiento = Transaction(
        tipo=movimiento_in.tipo,
        monto=monto_cents,
        moneda=movimiento_in.moneda,
        categoria=movimiento_in.categoria,
        fecha=movimiento_in.fecha or datetime.now()
    )
    
    session.add(nuevo_movimiento)
    session.commit()
    session.refresh(nuevo_movimiento)
    return transaction_to_dict(nuevo_movimiento)