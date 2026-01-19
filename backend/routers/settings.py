from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from database import get_session
from models.models import BrokerSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    default_fee_integer: float
    default_fee_fractional: float

def get_or_create_settings(session: Session) -> BrokerSettings:
    settings = session.get(BrokerSettings, 1)
    if not settings:
        settings = BrokerSettings(id=1, default_fee_integer=0, default_fee_fractional=0)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings

@router.get("/")
def get_settings(session: Session = Depends(get_session)):
    s = get_or_create_settings(session)
    return {
        "id": s.id,
        "default_fee_integer": s.default_fee_integer / 100.0,
        "default_fee_fractional": s.default_fee_fractional / 100.0
    }

@router.post("/")
def update_settings(update: SettingsUpdate, session: Session = Depends(get_session)):
    settings = get_or_create_settings(session)
    settings.default_fee_integer = int(round(update.default_fee_integer * 100))
    settings.default_fee_fractional = int(round(update.default_fee_fractional * 100))
    session.add(settings)
    session.commit()
    session.refresh(settings)
    
    return {
        "id": settings.id,
        "default_fee_integer": settings.default_fee_integer / 100.0,
        "default_fee_fractional": settings.default_fee_fractional / 100.0
    }
