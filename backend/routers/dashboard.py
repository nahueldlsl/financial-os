from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from database import get_session
from services.portfolio_service import PortfolioService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("")
def obtener_dashboard(session: Session = Depends(get_session)):
    try:
        # Delegamos toda la lógica al servicio
        return PortfolioService.get_dashboard_summary(session)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
