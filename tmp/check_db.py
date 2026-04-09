import sys
import os
sys.path.append(r"c:\Users\nahue\OneDrive\Escritorio\UCU\Proyectos\Visualizacion de inversion\backend")

from sqlmodel import Session, create_engine, select
from models.models import TradeHistory

db_path = r"c:\Users\nahue\OneDrive\Escritorio\UCU\Proyectos\Visualizacion de inversion\backend\database.db"
engine = create_engine(f"sqlite:///{db_path}")

with Session(engine) as session:
    trades = session.exec(select(TradeHistory)).all()
    types = {}
    for t in trades:
        types[t.tipo] = types.get(t.tipo, 0) + 1
    print(f"Trade types: {types}")
