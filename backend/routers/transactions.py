# backend/routers/transactions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from database import get_session
from models.models import Transaction
from models.schemas import TransactionCreate, TransactionUpdate
from datetime import datetime
from utils.money import to_dollars, to_cents

router = APIRouter(prefix="/api/movimientos", tags=["movimientos"])

# Helper para convertir Transaction (cents) a Dict (dollars)
def transaction_to_dict(t: Transaction):
    return {
        "id": t.id,
        "tipo": t.tipo,
        "monto": to_dollars(t.monto),
        "moneda": t.moneda,
        "categoria": t.categoria,
        "fecha": t.fecha.isoformat() if t.fecha else None
    }

@router.get("", include_in_schema=False)
@router.get("/")
def leer_movimientos(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    movimientos = session.exec(select(Transaction).order_by(Transaction.fecha.desc()).offset(skip).limit(limit)).all()
    return [transaction_to_dict(m) for m in movimientos]

@router.post("", include_in_schema=False)
@router.post("/")
def agregar_movimiento(movimiento_in: TransactionCreate, session: Session = Depends(get_session)):
    monto_cents = to_cents(movimiento_in.monto)
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

@router.put("/{id}")
def actualizar_movimiento(id: int, update_in: TransactionUpdate, session: Session = Depends(get_session)):
    tx = session.get(Transaction, id)
    if not tx:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    if update_in.tipo is not None:
        tx.tipo = update_in.tipo
    if update_in.monto is not None:
        tx.monto = to_cents(update_in.monto)
    if update_in.moneda is not None:
        tx.moneda = update_in.moneda
    if update_in.categoria is not None:
        tx.categoria = update_in.categoria
    if update_in.fecha is not None:
        tx.fecha = update_in.fecha
        
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return transaction_to_dict(tx)

@router.delete("/{id}")
def eliminar_movimiento(id: int, session: Session = Depends(get_session)):
    tx = session.get(Transaction, id)
    if not tx:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    session.delete(tx)
    session.commit()
    return {"status": "success", "message": "Movimiento eliminado"}