from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.beneficiary import BeneficiaryCreate, BeneficiaryOut, BeneficiaryUpdate
from app.schemas.common import Page
from app.services.beneficiary_service import BeneficiaryService
from app.utils.enums import BeneficiaryCategory
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/beneficiaries", tags=["Beneficiaries"])
reader = require_permissions(Permission.BENEFICIARIES_READ)
writer = require_permissions(Permission.BENEFICIARIES_WRITE)


@router.post("", response_model=BeneficiaryOut, status_code=status.HTTP_201_CREATED, summary="Register a beneficiary")
def register(payload: BeneficiaryCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    svc = BeneficiaryService(db)
    return svc.serialize(actor, svc.create(actor, payload))


@router.get("", response_model=Page[BeneficiaryOut], summary="List beneficiaries (sensitive fields redacted for unprivileged roles)")
def list_beneficiaries(
    search: str | None = None, category: BeneficiaryCategory | None = None, project_id: int | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(reader), db: Session = Depends(get_db),
):
    svc = BeneficiaryService(db)
    items, total = svc.list_beneficiaries(params, sort, search=search, category=category, project_id=project_id)
    return build_page([svc.serialize(actor, i) for i in items], total, params)


@router.get("/{beneficiary_id}", response_model=BeneficiaryOut)
def get_beneficiary(beneficiary_id: int, actor: User = Depends(reader), db: Session = Depends(get_db)):
    svc = BeneficiaryService(db)
    return svc.serialize(actor, svc.get(beneficiary_id))


@router.patch("/{beneficiary_id}", response_model=BeneficiaryOut)
def update_beneficiary(beneficiary_id: int, payload: BeneficiaryUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    svc = BeneficiaryService(db)
    return svc.serialize(actor, svc.update(actor, beneficiary_id, payload))


@router.post("/{beneficiary_id}/projects/{project_id}", response_model=BeneficiaryOut, summary="Map a beneficiary to a project")
def map_project(beneficiary_id: int, project_id: int, actor: User = Depends(writer), db: Session = Depends(get_db)):
    svc = BeneficiaryService(db)
    return svc.serialize(actor, svc.map_project(actor, beneficiary_id, project_id))


@router.delete("/{beneficiary_id}/projects/{project_id}", response_model=BeneficiaryOut, summary="Remove a beneficiary from a project")
def unmap_project(beneficiary_id: int, project_id: int, actor: User = Depends(writer), db: Session = Depends(get_db)):
    svc = BeneficiaryService(db)
    return svc.serialize(actor, svc.unmap_project(actor, beneficiary_id, project_id))
