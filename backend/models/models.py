# backend/models/models.py
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

# --- CASH FLOW (Tus gastos personales diarios) ---
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: str       # "ingreso" | "gasto"
    monto: int      # CENTS: 10050 = $100.50
    moneda: str     # "USD" | "UYU"
    categoria: str
    fecha: datetime = Field(default_factory=datetime.now)

# --- PORTAFOLIO (Tus Activos Actuales) ---
class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True, unique=True)
    cantidad_total: float      # FLOAT: Cantidad de acciones (puede ser fraccional)
    precio_promedio: int       # CENTS: Precio promedio de compra
    
    # Caching para Performance
    cached_price: Optional[int] = Field(default=None) # CENTS: Precio actual de mercado
    last_updated: Optional[datetime] = Field(default=None)

# --- CONFIGURACIÓN DE BROKER (Singleton) ---
class BrokerSettings(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    default_fee_integer: int = Field(default=0)    # CENTS: Costo por acción entera
    default_fee_fractional: int = Field(default=0) # CENTS: Costo por fracción

# --- CAJA DEL BROKER (Dinero listo para invertir) ---
class BrokerCash(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    saldo_usd: int = Field(default=0) # CENTS

# --- HISTORIAL DE TRADING (Compras y Ventas) ---
class TradeHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str
    tipo: str       # "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAW"
    cantidad: float # Positivo
    precio: int     # CENTS: Precio al que se ejecutó
    total: int      # CENTS: cantidad * precio
    fecha: datetime = Field(default_factory=datetime.now)
    
    # Solo para ventas: Cuánto ganaste/perdiste en esta operación específica
    ganancia_realizada: Optional[int] = None # CENTS
    
    # Costo de la operación
    commission: int = Field(default=0) # CENTS