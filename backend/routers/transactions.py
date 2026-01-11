# routers/transactions.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List
from database import get_session
from models.models import Transaction

router = APIRouter(prefix="/api/movimientos", tags=["movimientos"])

@router.get("/", response_model=List[Transaction])
def leer_movimientos(session: Session = Depends(get_session)):
    # SELECT * FROM transaction
    movimientos = session.exec(select(Transaction)).all()
    return movimientos

@router.post("/", response_model=Transaction)
def agregar_movimiento(movimiento: Transaction, session: Session = Depends(get_session)):
    session.add(movimiento)
    session.commit()
    session.refresh(movimiento) # Actualiza el ID generado
    return movimiento