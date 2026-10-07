from abc import ABC, abstractmethod
from sqlmodel import Session, select
from datetime import datetime
from models.models import Asset, Transaction, TradeHistory, BrokerCash, BrokerSettings
from typing import Dict, List, Any

class ImportStrategy(ABC):
    """Abstract Base Class for Import Strategies (Open/Closed Principle)"""
    @abstractmethod
    def execute(self, session: Session, data: Dict[str, Any]):
        pass

class SmartMergeStrategy(ImportStrategy):
    """
    Strategy: Smart Merge
    - Assets: Update if exists (ticker), Create if not.
    - Transactions: Add new ones (avoid duplicates by ID if provided, smart check otherwise).
    """
    def execute(self, session: Session, data: Dict[str, Any]):
        # 1. Process Assets
        assets_data = data.get("assets", [])
        for asset_dict in assets_data:
            ticker = asset_dict.get("ticker")
            if not ticker:
                continue

            # Check existence
            statement = select(Asset).where(Asset.ticker == ticker)
            existing_asset = session.exec(statement).first()

            if existing_asset:
                # Update logic: We trust the backup is newer/correct, or we merge?
                # User request: "Si el ticker existe, actualiza cantidad/precio."
                existing_asset.cantidad_total = asset_dict.get("cantidad_total", 0.0)
                existing_asset.precio_promedio = asset_dict.get("precio_promedio", 0)
                existing_asset.cached_price = asset_dict.get("cached_price")
                
                # Handle dates safely
                if asset_dict.get("last_updated"):
                    try:
                        existing_asset.last_updated = datetime.fromisoformat(asset_dict["last_updated"])
                    except (ValueError, TypeError):
                        pass # Keep existing or None
                
                session.add(existing_asset)
            else:
                # Create new
                # Ensure we don't pass 'id' if we want the DB to auto-generate, 
                # OR we keep 'id' to maintain strict backup restoration.
                # Usually for merge, keeping ID might cause conflicts if DBs are different.
                # Safest for "Smart Merge" is to ignore ID for creation unless we are doing full restore.
                # Let's remove ID to let DB handle primary keys for new entries to avoid conflicts.
                if "id" in asset_dict:
                    del asset_dict["id"]
                
                # Convert date string to object if needed before creating model
                if asset_dict.get("last_updated"):
                    try:
                        asset_dict["last_updated"] = datetime.fromisoformat(asset_dict["last_updated"])
                    except (ValueError, TypeError):
                        del asset_dict["last_updated"]

                new_asset = Asset(**asset_dict)
                session.add(new_asset)

        # 2. Process Transactions
        transactions_data = data.get("transactions", [])
        for tx_dict in transactions_data:
            # Check duplicates. 
            # If the backup has IDs, we can check by ID.
            # But if we are merging into a different DB, IDs might clash.
            # Best "Smart Merge" check: duplicate if same (ticker, type, date, amount) ? 
            # Simplified: If ID exists in input, check if exists in DB.
            
            tx_id = tx_dict.get("id")
            if tx_id:
                existing_tx = session.get(Transaction, tx_id)
                if existing_tx:
                    # Decide: Update or Skip? 
                    # Usually "Merge" implies "Add missing". 
                    # If it exists, let's assume it's the same. Skip to save time/risk.
                    continue
            
            # If no ID or not found, we create.
            # Ideally, we should remove ID to let DB generate a new unique one 
            # unless we specifically want to force that ID (and we know it's free).
            # For a "Merge", generating new IDs is safer to avoid PK violations.
            if "id" in tx_dict:
                del tx_dict["id"]

            # Convert date
            if tx_dict.get("fecha"):
                try:
                    tx_dict["fecha"] = datetime.fromisoformat(tx_dict["fecha"])
                except (ValueError, TypeError):
                    tx_dict["fecha"] = datetime.now()

            new_tx = Transaction(**tx_dict)
            session.add(new_tx)

        # 3. Process TradeHistory
        trades_data = data.get("trades", [])
        for trade_dict in trades_data:
            trade_id = trade_dict.get("id")
            if trade_id:
                existing_trade = session.get(TradeHistory, trade_id)
                if existing_trade:
                    continue
            if "id" in trade_dict:
                del trade_dict["id"]
            if trade_dict.get("fecha"):
                try:
                    trade_dict["fecha"] = datetime.fromisoformat(trade_dict["fecha"])
                except (ValueError, TypeError):
                    trade_dict["fecha"] = datetime.now()
            new_trade = TradeHistory(**trade_dict)
            session.add(new_trade)

        # 4. Process BrokerCash
        cash_data = data.get("broker_cash")
        if cash_data and isinstance(cash_data, dict):
            cash_obj = session.get(BrokerCash, 1)
            if not cash_obj:
                cash_obj = BrokerCash(id=1, saldo_usd=cash_data.get("saldo_usd", 0))
            else:
                cash_obj.saldo_usd = cash_data.get("saldo_usd", cash_obj.saldo_usd)
            session.add(cash_obj)

        # 5. Process BrokerSettings
        settings_data = data.get("broker_settings")
        if settings_data and isinstance(settings_data, dict):
            settings_obj = session.get(BrokerSettings, 1)
            if not settings_obj:
                settings_obj = BrokerSettings(
                    id=1,
                    default_fee_integer=settings_data.get("default_fee_integer", 0),
                    default_fee_fractional=settings_data.get("default_fee_fractional", 0)
                )
            else:
                settings_obj.default_fee_integer = settings_data.get("default_fee_integer", settings_obj.default_fee_integer)
                settings_obj.default_fee_fractional = settings_data.get("default_fee_fractional", settings_obj.default_fee_fractional)
            session.add(settings_obj)
        # The user instructions said: "Commit: Realiza un solo session.commit() al final"
        # Since this is the strategy executing the logic, it puts things in session.
        # The caller (Router) should likely commit to ensure atomicity across the whole operation,
        # OR the strategy does it. 
        # Plan says: "Single session.commit()". 
        # Use case: What if I chain strategies? 
        # Better: Strategy does `session.add`, Router calls `session.commit()`.
        # BUT User instruction for "Smart Merge" specifically listed "Commit" as a step.
        # Let's let the Router do the final commit to handle errors/rollback globally.
        pass

class ImportContext:
    def __init__(self, strategy: ImportStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: ImportStrategy):
        self._strategy = strategy

    def execute_import(self, session: Session, data: Dict[str, Any]):
        return self._strategy.execute(session, data)
