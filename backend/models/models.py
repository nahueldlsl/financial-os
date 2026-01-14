# backend/models/models.py
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

# --- CASH FLOW (Tus gastos personales diarios) ---
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: str       # "ingreso" | "gasto"
    monto: float
    moneda: str     # "USD" | "UYU"
    categoria: str
    fecha: datetime = Field(default_factory=datetime.now)

# --- PORTAFOLIO (Tus Activos Actuales) ---
class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True, unique=True)
    cantidad_total: float
    precio_promedio: float
    
    # Configuración DRIP
    drip_enabled: bool = Field(default=False)
    fecha_inicio_drip: Optional[str] = None
    ultima_revision_div: Optional[str] = None
    
    # Caching para Performance
    cached_price: Optional[float] = Field(default=None)
    last_updated: Optional[datetime] = Field(default=None)

# --- CAJA DEL BROKER (Dinero listo para invertir) ---
class BrokerCash(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    saldo_usd: float = Field(default=0.0)

# --- HISTORIAL DE TRADING (Compras y Ventas) ---
class TradeHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str
    tipo: str       # "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAW"
    cantidad: float # Positivo
    precio: float   # Precio al que se ejecutó
    total: float    # cantidad * precio
    fecha: datetime = Field(default_factory=datetime.now)
    
    # Solo para ventas: Cuánto ganaste/perdiste en esta operación específica
    ganancia_realizada: Optional[float] = None