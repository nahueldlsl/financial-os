# models/models.py
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

# Tabla para tus Movimientos (CashFlow)
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: str       # "ingreso" | "gasto"
    monto: float
    moneda: str     # "USD" | "UYU"
    categoria: str
    fecha: datetime = Field(default_factory=datetime.now)

# Tabla para tus Activos (Portfolio)
class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True, unique=True) # Indexado para busquedas rapidas
    cantidad_total: float
    precio_promedio: float
    # Campos opcionales para DRIP
    drip_enabled: bool = Field(default=False)
    fecha_inicio_drip: Optional[str] = None
    ultima_revision_div: Optional[str] = None