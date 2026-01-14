import json
import os
from sqlmodel import Session, select
from datetime import datetime
from database import engine, create_db_and_tables
from models.models import Transaction, Asset

def migrar():
    print("Iniciando migración a SQLite...")
    
    # Borramos la DB anterior si existe para empezar limpio
    if os.path.exists("financial.db"):
        try:
            os.remove("financial.db")
            print("Base de datos anterior eliminada.")
        except:
            pass

    create_db_and_tables()
    
    with Session(engine) as session:
        # --- 2. MIGRAR ACTIVOS ---
        if os.path.exists("mis_activos.json"):
            with open("mis_activos.json", "r") as f:
                data = json.load(f)
                count = 0
                for item in data:
                    # Verificar si ya existe para no duplicar
                    existe = session.exec(select(Asset).where(Asset.ticker == item["Ticker"])).first()
                    if not existe:
                        asset = Asset(
                            ticker=item["Ticker"],
                            cantidad_total=float(item["Cantidad_Total"]),
                            precio_promedio=float(item["Precio_Promedio"]),
                            drip_enabled=item.get("DRIP", False),
                            # Estos campos son String en el modelo Asset, así que no necesitan conversión
                            fecha_inicio_drip=item.get("Fecha_Inicio_DRIP"),
                            ultima_revision_div=item.get("Ultima_Revision_Div")
                        )
                        session.add(asset)
                        count += 1
                print(f"-> {count} activos migrados correctamente.")
        
        session.commit()
        print("¡Migración Completada! Base de datos 'financial.db' lista.")

if __name__ == "__main__":
    migrar()