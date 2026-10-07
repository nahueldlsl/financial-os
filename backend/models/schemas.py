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

class TradeSchema(BaseModel):
    ticker: str
    type: str # "BUY" or "SELL"
    quantity: Optional[float] = None
    cantidad: Optional[float] = None
    price: Optional[float] = None
    precio: Optional[float] = None
    date: Optional[datetime] = None
    fecha: Optional[datetime] = None
    applied_fee: float = 0.0
    usar_caja_broker: bool = True

    def get_quantity(self) -> float:
        val = self.quantity if self.quantity is not None else self.cantidad
        if val is None or val <= 0:
            raise ValueError("Se requiere una cantidad mayor a 0")
        return float(val)

    def get_price(self) -> float:
        val = self.price if self.price is not None else self.precio
        if val is None or val < 0:
            raise ValueError("Se requiere un precio válido")
        return float(val)

    def get_date(self) -> datetime:
        return self.date or self.fecha or datetime.utcnow()

class TradeAction(BaseModel):
    ticker: str
    cantidad: float
    precio: float
    fecha: Optional[datetime] = None
    applied_fee: float = 0.0
    usar_caja_broker: bool = True

class BrokerFund(BaseModel):
    monto_enviado: float
    monto_recibido: float
    tipo: str # "DEPOSIT" | "WITHDRAW"

class ImportRequest(BaseModel):
    content: str

class TransactionDateUpdate(BaseModel):
    date: datetime
