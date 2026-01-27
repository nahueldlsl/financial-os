from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Input Schema para Creación (Recibe FLOATs de la UI)
class TransactionCreate(BaseModel):
    tipo: str       # "ingreso" | "gasto"
    monto: float    # USD (Entero o Decimal)
    moneda: str     # "USD" | "UYU"
    categoria: str
    fecha: Optional[datetime] = None

# Input Schema para Updates (Opcional)
class TransactionUpdate(BaseModel):
    tipo: Optional[str] = None
    monto: Optional[float] = None
    moneda: Optional[str] = None
    categoria: Optional[str] = None
    fecha: Optional[datetime] = None

# --- TRADING SCHEMAS ---
class TradeHistoryUpdate(BaseModel):
    cantidad: Optional[float] = None
    precio: Optional[float] = None     # Dólares
    commission: Optional[float] = None # Dólares
    fecha: Optional[datetime] = None
    tipo: Optional[str] = None
