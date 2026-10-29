from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.impact import ImpactSummary, ImpactUpdateCreate, ImpactUpdateOut
from app.services.impact_service import ImpactService
from app.utils.pagination import PaginationParams, build_page, pagination_params

router = APIRouter(prefix="/impact", tags=["Impact Tracking"])
reader = require_permissions(Permission.IMPACT_READ)


@router.post("/updates", response_model=ImpactUpdateOut, status_code=status.HTTP_201_CREATED, summary="Submit a project impact update")
def submit_update(payload: ImpactUpdateCreate, actor: User = Depends(require_permissions(Permission.IMPACT_WRITE)), db: Session = Depends(get_db)):
    return ImpactService(db).submit(actor, payload)


@router.get("/updates", response_model=Page[ImpactUpdateOut], summary="Impact update history")
def history(
    project_id: int | None = None, params: PaginationParams = Depends(pagination_params),
    _: User = Depends(reader), db: Session = Depends(get_db),
):
    items, total = ImpactService(db).history(params, project_id)
    return build_page([ImpactUpdateOut.model_validate(i) for i in items], total, params)


@router.get("/summary", response_model=ImpactSummary, summary="Live impact metrics (organisation-wide or per project)")
def summary(project_id: int | None = None, _: User = Depends(reader), db: Session = Depends(get_db)):
    return ImpactService(db).live_summary(project_id)
