from sqlmodel import SQLModel, create_engine, Session
import os # <--- Importante

# 1. Buscamos la URL en las variables de entorno (Configuración de Docker)
# Si no existe, usamos SQLite con ruta absoluta determinista al archivo financial.db en la raíz del proyecto
env_db_url = os.environ.get("DATABASE_URL")
if not env_db_url:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_db = os.path.abspath(os.path.join(base_dir, "..", "financial.db"))
    if os.path.exists(root_db):
        DATABASE_URL = f"sqlite:///{root_db}"
    else:
        DATABASE_URL = f"sqlite:///{os.path.abspath(os.path.join(base_dir, 'financial.db'))}"
else:
    DATABASE_URL = env_db_url

# 2. Configuración del Engine
if "sqlite" in DATABASE_URL:
    # Configuración específica para SQLite
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    # Configuración para PostgreSQL
    engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
    # Migración en caliente para compatibilidad con bases de datos pre-existentes (PostgreSQL/SQLite)
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    
    with engine.begin() as conn:
        try:
            columns = [col['name'] for col in inspector.get_columns('asset')]
            if "fecha_primera_compra" not in columns:
                conn.execute(text("ALTER TABLE asset ADD COLUMN fecha_primera_compra TIMESTAMP"))
            if "fecha_ultima_operacion" not in columns:
                conn.execute(text("ALTER TABLE asset ADD COLUMN fecha_ultima_operacion TIMESTAMP"))
        except Exception as e:
            # Table might not exist yet or other error
            pass