from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.resource_allocation import AllocationCreate, AllocationOut
from app.services.resource_allocation_service import ResourceAllocationService
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/resource-allocations", tags=["Resource Allocations"])


@router.post("", response_model=AllocationOut, status_code=status.HTTP_201_CREATED, summary="Allocate stock to a project")
def allocate(payload: AllocationCreate, actor: User = Depends(require_permissions(Permission.RESOURCES_WRITE)), db: Session = Depends(get_db)):
    svc = ResourceAllocationService(db)
    return svc.serialize(svc.allocate(actor, payload))


@router.get("", response_model=Page[AllocationOut], summary="Allocation / distribution history")
def list_allocations(
    resource_id: int | None = None, project_id: int | None = None, date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(require_permissions(Permission.RESOURCES_READ)), db: Session = Depends(get_db),
):
    svc = ResourceAllocationService(db)
    items, total = svc.list_allocations(params, sort, resource_id=resource_id, project_id=project_id, date_from=date_from, date_to=date_to)
    return build_page([svc.serialize(i) for i in items], total, params)
