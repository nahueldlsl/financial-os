# database.py
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

# Esto creará un archivo 'financial.db' que es tu base de datos real
SQLITE_FILE_NAME = "financial.db"
sqlite_url = f"sqlite:///{SQLITE_FILE_NAME}"

# connect_args es necesario solo para SQLite
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Dependencia para usar en tus endpoints
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session