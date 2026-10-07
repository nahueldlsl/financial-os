import math
from typing import Any

def safe_float(val: Any) -> float:
    """Convierte de forma segura cualquier valor a float, retornando 0.0 si es None, NaN o Inf."""
    try:
        if val is None:
            return 0.0
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except Exception:
        return 0.0

def to_cents(val_float: float) -> int:
    """Convierte monto en DÓLARES (float) a CENTAVOS (int)."""
    return int(round(safe_float(val_float) * 100))

def to_dollars(val_cents: Any) -> float:
    """Convierte CENTAVOS (int) a DÓLARES (float) para UI/APIs."""
    return safe_float(val_cents) / 100.0
