from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Session, select
from models.models import WatchlistItem


class WatchlistService:
    """
    Servicio con responsabilidad única (SRP):
    Gestionar la persistencia y consulta de tickers en la Watchlist del usuario.
    """

    @staticmethod
    def get_watchlist(session: Session) -> List[dict]:
        """Retorna todos los items en la watchlist ordenados por fecha agregada desc."""
        statement = select(WatchlistItem).order_by(WatchlistItem.added_at.desc())
        items = session.exec(statement).all()
        return [
            {
                "id": item.id,
                "ticker": item.ticker,
                "added_at": item.added_at.isoformat() if item.added_at else None,
                "notes": item.notes,
            }
            for item in items
        ]

    @staticmethod
    def get_watchlist_tickers(session: Session) -> List[str]:
        """Retorna únicamente la lista de tickers limpios en mayúsculas."""
        statement = select(WatchlistItem.ticker)
        return [t.upper() for t in session.exec(statement).all()]

    @staticmethod
    def is_in_watchlist(session: Session, ticker: str) -> bool:
        """Verifica si un ticker ya se encuentra en la watchlist."""
        clean_ticker = ticker.strip().upper()
        item = session.exec(
            select(WatchlistItem).where(WatchlistItem.ticker == clean_ticker)
        ).first()
        return item is not None

    @staticmethod
    def add_to_watchlist(session: Session, ticker: str, notes: Optional[str] = None) -> dict:
        """Añade un nuevo ticker a la watchlist de manera idempotente."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            raise ValueError("El ticker no puede estar vacío")

        existing = session.exec(
            select(WatchlistItem).where(WatchlistItem.ticker == clean_ticker)
        ).first()

        if existing:
            if notes is not None:
                existing.notes = notes
                session.add(existing)
                session.commit()
                session.refresh(existing)
            return {
                "id": existing.id,
                "ticker": existing.ticker,
                "added_at": existing.added_at.isoformat() if existing.added_at else None,
                "notes": existing.notes,
                "created": False,
            }

        new_item = WatchlistItem(
            ticker=clean_ticker,
            notes=notes,
            added_at=datetime.now(timezone.utc)
        )
        session.add(new_item)
        session.commit()
        session.refresh(new_item)
        return {
            "id": new_item.id,
            "ticker": new_item.ticker,
            "added_at": new_item.added_at.isoformat() if new_item.added_at else None,
            "notes": new_item.notes,
            "created": True,
        }

    @staticmethod
    def remove_from_watchlist(session: Session, ticker: str) -> bool:
        """Elimina un ticker de la watchlist. Retorna True si existía y se eliminó."""
        clean_ticker = ticker.strip().upper()
        item = session.exec(
            select(WatchlistItem).where(WatchlistItem.ticker == clean_ticker)
        ).first()
        if not item:
            return False

        session.delete(item)
        session.commit()
        return True
