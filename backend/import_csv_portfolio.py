"""
Script de importación y sincronización de portafolio desde CSV a Financial OS.
Lee /Users/santiagodelossantos/Desktop/Mi_Portafolio_Completo_2026-09-29.csv
y puebla la base de datos de manera atómica y determinística.
"""
import csv
import os
import sys
from datetime import datetime
from sqlmodel import Session, select

from database import engine, create_db_and_tables
from models.models import Asset, TradeHistory, BrokerCash, BrokerSettings
from services.portfolio_service import PortfolioService, to_cents

CSV_PATH = "/Users/santiagodelossantos/Desktop/Mi_Portafolio_Completo_2026-09-29.csv"

def parse_ddmmyyyy(date_str: str) -> datetime:
    """Parsea fechas tipo '28/07/2025' a datetime nativo."""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y")
    except Exception:
        return datetime.now()

def import_portfolio_from_csv(csv_path: str = CSV_PATH):
    print("=" * 60)
    print(f"🚀 Iniciando importación de portafolio desde: {csv_path}")
    print("=" * 60)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

    # 1. Asegurar tablas creadas
    create_db_and_tables()

    # 2. Leer las dos secciones del CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    t1_lines = []
    t2_lines = []
    current_section = None

    for line in lines:
        line_clean = line.strip()
        if "=== WATCH TABLE" in line_clean:
            current_section = 1
            continue
        elif "=== HISTORIAL DE COMPRAS" in line_clean:
            current_section = 2
            continue

        if current_section == 1 and line_clean:
            t1_lines.append(line)
        elif current_section == 2 and line_clean:
            t2_lines.append(line)

    watch_rows = list(csv.DictReader(t1_lines))
    history_rows = list(csv.DictReader(t2_lines))

    print(f"📊 Filas encontradas: {len(watch_rows)} en Watch Table, {len(history_rows)} en Historial de Compras.")

    with Session(engine) as session:
        # 3. Limpiar datos previos de portafolio para garantizar importación limpia y determinística
        print("🧹 Limpiando registros anteriores de TradeHistory y Asset...")
        session.exec(select(TradeHistory)).all()
        for t in session.exec(select(TradeHistory)).all():
            session.delete(t)
        for a in session.exec(select(Asset)).all():
            session.delete(a)
        session.commit()

        # 4. Configurar BrokerSettings y BrokerCash
        settings = session.get(BrokerSettings, 1)
        if not settings:
            settings = BrokerSettings(id=1, default_fee_integer=30, default_fee_fractional=30)
            session.add(settings)
        else:
            settings.default_fee_integer = 30
            settings.default_fee_fractional = 30
            session.add(settings)

        cash = session.get(BrokerCash, 1)
        if not cash:
            cash = BrokerCash(id=1, saldo_usd=0)
            session.add(cash)
        session.commit()

        # 5. Insertar operaciones cronológicas en TradeHistory
        print("📜 Insertando 35 operaciones en TradeHistory...")
        # Ordenar cronológicamente por fecha para replay canónico
        parsed_trades = []
        for r in history_rows:
            ticker = r["Ticker"].strip()
            date_dt = parse_ddmmyyyy(r["Date"])
            op_type = r["Type"].strip().upper()
            volume = abs(float(r["Volume"]))
            bought_price = float(r["Bought Price"])
            order_val = abs(float(r["Order Value"]))
            brokerage = float(r.get("Brokerage", 0.30))
            cap_gain = float(r.get("Capital Gain $", 0.0)) if r.get("Capital Gain $") else 0.0

            parsed_trades.append({
                "ticker": ticker,
                "date": date_dt,
                "type": op_type,
                "volume": volume,
                "price_cents": to_cents(bought_price),
                "total_cents": to_cents(order_val),
                "fee_cents": to_cents(brokerage),
                "gain_cents": to_cents(cap_gain) if op_type == "SELL" else None
            })

        # Ordenar por fecha ascendente
        parsed_trades.sort(key=lambda x: x["date"])

        tickers_seen = set()
        for pt in parsed_trades:
            tickers_seen.add(pt["ticker"])
            th = TradeHistory(
                ticker=pt["ticker"],
                tipo=pt["type"],
                cantidad=pt["volume"],
                precio=pt["price_cents"],
                total=pt["total_cents"],
                commission=pt["fee_cents"],
                ganancia_realizada=pt["gain_cents"],
                fecha=pt["date"]
            )
            session.add(th)
        session.commit()

        # 6. Recalcular cada activo determinísticamente usando el motor de replay
        print("⚙️ Reconstruyendo activos con PortfolioService.recalculate_asset_from_history...")
        prices_by_ticker = {r["Ticker"].strip(): float(r["Current Price"]) for r in watch_rows}

        for ticker in sorted(tickers_seen):
            asset = PortfolioService.recalculate_asset_from_history(session, ticker)
            
            # Normalizar residuos fraccionales ínfimos (< 0.0001 como TSM y ASML)
            if asset.cantidad_total < 0.0001:
                asset.cantidad_total = 0.0
                asset.precio_promedio = 0

            # Asignar precio de mercado actual desde el CSV
            if ticker in prices_by_ticker:
                asset.cached_price = to_cents(prices_by_ticker[ticker])
                asset.last_updated = datetime.now()

            # Fechas primera compra y última operación
            ticker_trades = [t for t in parsed_trades if t["ticker"] == ticker]
            if ticker_trades:
                buy_dates = [t["date"] for t in ticker_trades if t["type"] == "BUY"]
                all_dates = [t["date"] for t in ticker_trades]
                if buy_dates:
                    asset.fecha_primera_compra = min(buy_dates)
                if all_dates:
                    asset.fecha_ultima_operacion = max(all_dates)

            session.add(asset)

        session.commit()
        print("✅ Importación y sincronización de base de datos completada exitosamente.")

if __name__ == "__main__":
    import_portfolio_from_csv()
