from sqlmodel import SQLModel, create_engine, Session
import os # <--- Importante

# 1. Buscamos la URL en las variables de entorno (Configuración de Docker)
# Si no existe, usamos SQLite (Configuración local de respaldo)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///financial.db")

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