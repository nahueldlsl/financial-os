# backend/migrate_to_postgres.py
import os
from sqlmodel import SQLModel, create_engine, Session, select, text
from models.models import Asset, Transaction, BrokerCash, TradeHistory

# 1. Configuración
SQLITE_FILE = "financial.db"
sqlite_url = f"sqlite:///{SQLITE_FILE}"
engine_sqlite = create_engine(sqlite_url)

postgres_url = os.environ.get("DATABASE_URL")
if not postgres_url:
    raise ValueError("❌ No se encontró DATABASE_URL.")

engine_postgres = create_engine(postgres_url)

def migrate():
    print("🚀 Iniciando migración de datos: SQLite -> PostgreSQL")
    
    if not os.path.exists(SQLITE_FILE):
        print(f"❌ Error: No encuentro '{SQLITE_FILE}' dentro del contenedor.")
        return

    # Crear tablas limpias en Postgres
    print("🔧 Creando tablas en Postgres...")
    SQLModel.metadata.create_all(engine_postgres)

    with Session(engine_sqlite) as src, Session(engine_postgres) as dest:
        
        # --- 1. MIGRAR CASH FLOW (TRANSACTIONS) ---
        print("\n💸 Migrando Transacciones (Cash Flow)...")
        try:
            txs = src.exec(select(Transaction)).all()
            print(f"   -> Encontradas {len(txs)} transacciones.")
            for t in txs:
                new_tx = Transaction(
                    tipo=t.tipo,
                    monto=t.monto,
                    moneda=t.moneda,
                    categoria=t.categoria,
                    fecha=t.fecha
                )
                dest.add(new_tx)
        except Exception as e:
            print(f"   ⚠️ No se pudieron migrar transacciones (quizás la tabla no existía): {e}")
        
        # --- 2. MIGRAR PORTAFOLIO (ASSETS) - CORREGIDO CON SQL PURO ---
        print("\n📈 Migrando Portafolio (Assets)...")
        try:
            # USAMOS SQL PURO PARA LEER SOLO LAS COLUMNAS QUE EXISTEN
            # Esto evita el error "no such column: cached_price"
            query = text("SELECT ticker, cantidad_total, precio_promedio FROM asset")
            results = src.connection().execute(query)
            
            count = 0
            for row in results:
                new_asset = Asset(
                    ticker=row.ticker,
                    cantidad_total=row.cantidad_total,
                    precio_promedio=row.precio_promedio,

                    # Los campos nuevos los ponemos vacíos para Postgres
                    cached_price=None,
                    last_updated=None
                )
                dest.add(new_asset)
                count += 1
            print(f"   -> Encontrados {count} activos.")
            
        except Exception as e:
            print(f"   ⚠️ Error migrando Assets: {e}")

        # --- 3. MIGRAR CAJA BROKER ---
        print("\n💰 Migrando Caja del Broker...")
        try:
            # Intentamos leer con ORM, si falla (porque no existe tabla), ignoramos
            cash_query = text("SELECT id, saldo_usd FROM brokercash WHERE id = 1")
            cash_res = src.connection().execute(cash_query).first()
            
            if cash_res:
                print(f"   -> Saldo encontrado: ${cash_res.saldo_usd}")
                existing_cash = dest.get(BrokerCash, 1)
                if existing_cash:
                    existing_cash.saldo_usd = cash_res.saldo_usd
                    dest.add(existing_cash)
                else:
                    new_cash = BrokerCash(id=1, saldo_usd=cash_res.saldo_usd)
                    dest.add(new_cash)
            else:
                print("   -> No se encontró saldo previo, se usará $0.0 por defecto.")
        except Exception:
            print("   -> Tabla BrokerCash no existía en la versión vieja. Se creará nueva.")

        # --- 4. MIGRAR HISTORIAL ---
        print("\n📜 Migrando Historial de Trading...")
        try:
            # Igual que assets, usamos SQL puro por seguridad
            hist_query = text("SELECT ticker, tipo, cantidad, precio, total, fecha, ganancia_realizada FROM tradehistory")
            hist_results = src.connection().execute(hist_query)
            
            h_count = 0
            for th in hist_results:
                new_th = TradeHistory(
                    ticker=th.ticker,
                    tipo=th.tipo,
                    cantidad=th.cantidad,
                    precio=th.precio,
                    total=th.total,
                    fecha=datetime.fromisoformat(str(th.fecha)) if isinstance(th.fecha, str) else th.fecha,
                    ganancia_realizada=th.ganancia_realizada
                )
                dest.add(new_th)
                h_count += 1
            print(f"   -> Encontradas {h_count} operaciones históricas.")
        except Exception:
             print("   -> Tabla TradeHistory no existía en la versión vieja. Se creará vacía.")

        print("\n💾 Guardando cambios en PostgreSQL...")
        dest.commit()
        print("✅ ¡MIGRACIÓN COMPLETADA! 🎉")

if __name__ == "__main__":
    from datetime import datetime # Import local para evitar conflictos arriba
    migrate()