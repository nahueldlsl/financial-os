from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models.models import TradeHistory
from models.schemas import TradeHistoryUpdate
from services.portfolio_service import PortfolioService, to_cents, to_dollars
from typing import List

router = APIRouter(prefix="/api/trading", tags=["trading"])

@router.get("/history/{ticker}")
def get_history(ticker: str, session: Session = Depends(get_session)):
    history = session.exec(
        select(TradeHistory)
        .where(TradeHistory.ticker == ticker)
        .order_by(TradeHistory.fecha.desc())
    ).all()
    
    # Convert cents to dollars for UI
    return [
        {
            **h.dict(),
            "precio": to_dollars(h.precio),
            "total": to_dollars(h.total),
            "commission": to_dollars(h.commission),
            "ganancia_realizada": to_dollars(h.ganancia_realizada) if h.ganancia_realizada else 0
        }
        for h in history
    ]

@router.put("/history/{id}")
def update_trade(id: int, trade_in: TradeHistoryUpdate, session: Session = Depends(get_session)):
    trade = session.get(TradeHistory, id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    # Update fields if provided
    # Input is Dollar Float -> Store as Cents
    if trade_in.precio is not None:
        trade.precio = to_cents(trade_in.precio)
    
    if trade_in.commission is not None:
        trade.commission = to_cents(trade_in.commission)
        
    if trade_in.cantidad is not None:
        trade.cantidad = trade_in.cantidad
        
    if trade_in.fecha is not None:
        trade.fecha = trade_in.fecha
        
    if trade_in.tipo is not None:
        trade.tipo = trade_in.tipo

    # Re-calculate 'total' field for this specific trade
    # Recalculate based on BUY or SELL logic
    cost_gross = trade.cantidad * trade.precio
    
    if trade.tipo == "BUY":
        trade.total = int(round(cost_gross + trade.commission))
    elif trade.tipo == "SELL":
        trade.total = int(round(cost_gross - trade.commission))
    # DEPOSIT/DIVIDEND logic could be added here if needed
    
    session.add(trade)
    session.commit()
    
    # TRIGGER REPLAY
    PortfolioService.recalculate_asset_from_history(session, trade.ticker)
    
    return {"message": "Trade updated and asset recalculated"}

@router.delete("/history/{id}")
def delete_trade(id: int, session: Session = Depends(get_session)):
    trade = session.get(TradeHistory, id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    ticker = trade.ticker
    session.delete(trade)
    session.commit()
    
    # TRIGGER REPLAY
    PortfolioService.recalculate_asset_from_history(session, ticker)
    
    return {"message": "Trade deleted and asset recalculated"}
