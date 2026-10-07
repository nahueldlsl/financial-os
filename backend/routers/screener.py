from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from database import get_session
from services.screener_service import ScreenerService
from services.watchlist_service import WatchlistService

router = APIRouter(prefix="/api", tags=["screener"])


@router.get("/screener")
def get_screener(
    scope: str = Query("all", description="all | portfolio | watchlist | market"),
    refresh: bool = Query(False, description="Forzar actualización de datos de mercado"),
    session: Session = Depends(get_session)
):
    """
    Retorna la lista de activos evaluados para screening y filtrado profesional.
    """
    try:
        items = ScreenerService.get_screener_data(
            session=session,
            scope=scope,
            force_refresh=refresh
        )
        return {
            "scope": scope,
            "total_items": len(items),
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo screener: {str(e)}")


@router.get("/watchlist")
def get_watchlist(session: Session = Depends(get_session)):
    """
    Retorna los items de la watchlist del usuario.
    """
    items = WatchlistService.get_watchlist(session)
    tickers = WatchlistService.get_watchlist_tickers(session)
    return {
        "watchlist": tickers,
        "items": items
    }


@router.post("/watchlist/{ticker}")
def add_to_watchlist(
    ticker: str,
    notes: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Añade un ticker a la watchlist del usuario.
    """
    try:
        res = WatchlistService.add_to_watchlist(session, ticker, notes)
        return {
            "status": "success",
            "message": f"Ticker {ticker.upper()} añadido a la watchlist",
            "data": res
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar ticker: {str(e)}")


@router.delete("/watchlist/{ticker}")
def remove_from_watchlist(
    ticker: str,
    session: Session = Depends(get_session)
):
    """
    Elimina un ticker de la watchlist.
    """
    try:
        deleted = WatchlistService.remove_from_watchlist(session, ticker)
        if not deleted:
            return {"status": "not_found", "message": f"Ticker {ticker.upper()} no estaba en la watchlist"}
        return {"status": "success", "message": f"Ticker {ticker.upper()} eliminado de la watchlist"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar ticker: {str(e)}")


@router.get("/screener/presets")
def get_screener_presets():
    """
    Retorna las estrategias cuantitativas predefinidas con 1 clic.
    """
    return {
        "presets": [
            {
                "id": "deep_value",
                "label": "Gemas Infravaloradas",
                "icon": "💎",
                "description": "Acciones con margen de seguridad >= 20% y cotizando bajo su valor intrínseco.",
                "filters": {
                    "valuationStatus": "undervalued",
                    "minMarginOfSafety": 20
                }
            },
            {
                "id": "strong_confluence",
                "label": "Confluencia Fuerte",
                "icon": "🎯",
                "description": "Señal óptima: Infravalorada fundamentalmente y con timing técnico favorable.",
                "filters": {
                    "confluenceVerdict": "strong_buy_confluence"
                }
            },
            {
                "id": "oversold_dip",
                "label": "Rebotes Sobrevendidos",
                "icon": "⚡",
                "description": "RSI < 35 en zona de sobreventa, ideales para compras en retroceso.",
                "filters": {
                    "rsiStatus": "oversold"
                }
            },
            {
                "id": "dividend_champions",
                "label": "Altos Dividendos",
                "icon": "👑",
                "description": "Rendimiento por dividendo >= 2.5% para flujo de caja pasivo.",
                "filters": {
                    "minDividendYield": 2.5
                }
            },
            {
                "id": "golden_cross",
                "label": "Líderes de Tendencia",
                "icon": "🚀",
                "description": "Cruce Dorado activo (SMA 50 > SMA 200) y precio en tendencia alcista.",
                "filters": {
                    "onlyGoldenCross": True
                }
            }
        ]
    }
