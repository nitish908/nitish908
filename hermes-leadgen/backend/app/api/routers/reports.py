from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.services.reports import compute_daily_summary, compute_overview

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return compute_overview(db)


@router.get("/daily-summary")
def daily_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return compute_daily_summary(db)
