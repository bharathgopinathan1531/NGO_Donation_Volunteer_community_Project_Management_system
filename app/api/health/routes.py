from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Liveness probe")
def liveness():
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}


@router.get("/ready", summary="Readiness probe (checks the database)")
def readiness(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "up"}
    except Exception:
        response.status_code = 503
        return {"status": "unavailable", "database": "down"}
