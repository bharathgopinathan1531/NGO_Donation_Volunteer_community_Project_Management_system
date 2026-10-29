from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.budget import BudgetOut, BudgetSet, BudgetUtilization
from app.schemas.common import Page
from app.services.budget_service import BudgetService
from app.utils.enums import BudgetScope
from app.utils.pagination import PaginationParams, build_page, pagination_params

router = APIRouter(prefix="/budgets", tags=["Budgets"])
reader = require_permissions(Permission.BUDGETS_READ)


@router.put("", response_model=BudgetOut, summary="Define (or replace) a campaign or project budget")
def set_budget(payload: BudgetSet, actor: User = Depends(require_permissions(Permission.BUDGETS_WRITE)), db: Session = Depends(get_db)):
    return BudgetService(db).set_budget(actor, payload)


@router.get("", response_model=Page[BudgetOut])
def list_budgets(
    scope: BudgetScope | None = None, params: PaginationParams = Depends(pagination_params),
    _: User = Depends(reader), db: Session = Depends(get_db),
):
    items, total = BudgetService(db).list_budgets(params, scope)
    return build_page([BudgetOut.model_validate(i) for i in items], total, params)


@router.get("/utilization", response_model=list[BudgetUtilization], summary="Budget utilization (remaining budget, overruns)")
def utilization(scope: BudgetScope | None = None, only_overruns: bool = False, _: User = Depends(reader), db: Session = Depends(get_db)):
    return BudgetService(db).list_utilization(scope, only_overruns)


@router.get("/projects/{project_id}/utilization", response_model=BudgetUtilization)
def project_utilization(project_id: int, _: User = Depends(reader), db: Session = Depends(get_db)):
    return BudgetService(db).project_utilization(project_id)


@router.get("/campaigns/{campaign_id}/utilization", response_model=BudgetUtilization)
def campaign_utilization(campaign_id: int, _: User = Depends(reader), db: Session = Depends(get_db)):
    return BudgetService(db).campaign_utilization(campaign_id)
