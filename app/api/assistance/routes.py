from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.beneficiary_assistance import AssistanceCreate, AssistanceOut
from app.schemas.common import Page
from app.services.assistance_service import AssistanceService
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/assistance", tags=["Beneficiary Assistance"])


@router.post("", response_model=AssistanceOut, status_code=status.HTTP_201_CREATED, summary="Record assistance given to a beneficiary")
def record(payload: AssistanceCreate, actor: User = Depends(require_permissions(Permission.BENEFICIARIES_WRITE)), db: Session = Depends(get_db)):
    return AssistanceService(db).record(actor, payload)


@router.get("", response_model=Page[AssistanceOut], summary="Assistance history")
def history(
    beneficiary_id: int | None = None, project_id: int | None = None, resource_id: int | None = None,
    date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(require_permissions(Permission.BENEFICIARIES_READ)), db: Session = Depends(get_db),
):
    items, total = AssistanceService(db).list_assistance(
        params, sort, beneficiary_id=beneficiary_id, project_id=project_id, resource_id=resource_id, date_from=date_from, date_to=date_to
    )
    return build_page([AssistanceOut.model_validate(i) for i in items], total, params)
