import json
import sqlite3
import os
from datetime import datetime

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "..", "financial.db"))
POSITIONS_JSON = os.environ.get("POSITIONS_JSON", os.path.join(BASE_DIR, "posiciones_actuales.json"))
TRADES_JSON = os.environ.get("TRADES_JSON", os.path.join(BASE_DIR, "historial_transacciones.json"))

from utils.money import to_cents

def parse_date(date_str):
    months = {
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
    }
    try:
        parts = date_str.split(' ')
        day = parts[0].zfill(2)
        month = months.get(parts[1].lower(), '01')
        year = parts[2]
        time = parts[3]
        return f"{year}-{month}-{day} {time}:00"
    except:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def sync():
    print("--- INICIANDO SINCRONIZACIÓN DE DATOS VOURA ---")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. ACTUALIZAR ESQUEMAS (Forzar columnas del modelo de SQLModel)
    
    # TradeHistory
    cursor.execute("PRAGMA table_info(tradehistory)")
    th_cols = [col[1] for col in cursor.fetchall()]
    for col, ty in [("commission", "INTEGER DEFAULT 0"), ("ganancia_realizada", "INTEGER DEFAULT 0")]:
        if col not in th_cols:
            print(f"Añadiendo {col} a tradehistory...")
            cursor.execute(f"ALTER TABLE tradehistory ADD COLUMN {col} {ty}")

    # Asset
    cursor.execute("PRAGMA table_info(asset)")
    asset_cols = [col[1] for col in cursor.fetchall()]
    for col, ty in [
        ("cached_price", "INTEGER"), 
        ("last_updated", "TIMESTAMP"),
        ("fecha_primera_compra", "TIMESTAMP"),
        ("fecha_ultima_operacion", "TIMESTAMP"),
        ("drip_enabled", "BOOLEAN DEFAULT 0")
    ]:
        if col not in asset_cols:
            print(f"Añadiendo {col} a asset...")
            cursor.execute(f"ALTER TABLE asset ADD COLUMN {col} {ty}")

    # 2. LIMPIAR DATOS
    cursor.execute("DELETE FROM asset")
    cursor.execute("DELETE FROM tradehistory")
    
    # 3. IMPORTAR POSICIONES (COSTO BASE -> $925)
    with open(POSITIONS_JSON, 'r', encoding='utf-8') as f:
        positions = json.load(f)

    for pos in positions:
        ticker = pos['ticker']
        qty = float(pos['cantidad_acciones'])
        mkt_value = float(pos['valor_total_usd'])
        
        rend_str = pos.get('rendimiento_diario', '+$0.00 (+0.00%)')
        try:
            val_part = rend_str.split(' ')[0]
            val_clean = val_part.replace('$', '').replace('+', '')
            gain_val = float(val_clean)
        except:
            gain_val = 0.0
            
        cost_basis = mkt_value - gain_val
        avg_price_cents = to_cents(cost_basis / qty) if qty > 0 else 0
        
        cursor.execute("""
            INSERT INTO asset (ticker, cantidad_total, precio_promedio, cached_price, drip_enabled)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, qty, avg_price_cents, to_cents(mkt_value/qty), 0))

    # 4. IMPORTAR HISTORIAL
    with open(TRADES_JSON, 'r', encoding='utf-8') as f:
        trades = json.load(f)

    for op in trades:
        if op.get('estado') != 'Terminado': continue
        ticker = op['ticker']
        monto = float(op['monto'])
        fecha = parse_date(op['fecha'])
        tipo_op = op['operacion']
        
        if "Compra" in tipo_op: tipo, val_cents = "BUY", to_cents(abs(monto))
        elif "Venta" in tipo_op: tipo, val_cents = "SELL", to_cents(monto)
        elif "Dividendo" in tipo_op: tipo, val_cents = "DIVIDEND", to_cents(monto)
        else: tipo, val_cents = "OTHER", to_cents(abs(monto))

        cursor.execute("""
            INSERT INTO tradehistory (ticker, tipo, cantidad, precio, total, commission, fecha, ganancia_realizada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, tipo, 0.0, 0, val_cents, 0, fecha, 0))

    conn.commit()
    conn.close()
    print("--- SINCRONIZACIÓN EXITOSA VOURA ---")

if __name__ == "__main__":
    sync()
