from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.expense import ExpenseApprove, ExpenseCreate, ExpenseOut, ExpenseReject, ExpenseUpdate
from app.services.expense_service import ExpenseService
from app.utils.enums import ExpenseCategory, ExpenseStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/expenses", tags=["Expenses"])
approver = require_permissions(Permission.EXPENSES_APPROVE)


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED, summary="Submit a project expense")
def submit_expense(payload: ExpenseCreate, actor: User = Depends(require_permissions(Permission.EXPENSES_SUBMIT)), db: Session = Depends(get_db)):
    return ExpenseService(db).submit(actor, payload)


@router.get("", response_model=Page[ExpenseOut], summary="List expenses (users without finance access see their own)")
def list_expenses(
    project_id: int | None = None, status: ExpenseStatus | None = None, category: ExpenseCategory | None = None,
    search: str | None = Query(None), date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = ExpenseService(db).list_expenses(
        actor, params, sort, project_id=project_id, status=status, category=category, search=search, date_from=date_from, date_to=date_to
    )
    return build_page([ExpenseOut.model_validate(i) for i in items], total, params)


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ExpenseService(db).get(actor, expense_id)


@router.patch("/{expense_id}", response_model=ExpenseOut, summary="Edit a not-yet-reviewed expense")
def update_expense(expense_id: int, payload: ExpenseUpdate, actor: User = Depends(require_permissions(Permission.EXPENSES_SUBMIT)), db: Session = Depends(get_db)):
    return ExpenseService(db).update(actor, expense_id, payload)


@router.post("/{expense_id}/approve", response_model=ExpenseOut, summary="Approve an expense (finance only, budget-checked)")
def approve_expense(expense_id: int, payload: ExpenseApprove | None = None, actor: User = Depends(approver), db: Session = Depends(get_db)):
    return ExpenseService(db).approve(actor, expense_id, payload or ExpenseApprove())


@router.post("/{expense_id}/reject", response_model=ExpenseOut, summary="Reject an expense (comment required)")
def reject_expense(expense_id: int, payload: ExpenseReject, actor: User = Depends(approver), db: Session = Depends(get_db)):
    return ExpenseService(db).reject(actor, expense_id, payload.comment)


@router.post("/{expense_id}/reimburse", response_model=ExpenseOut, summary="Mark an approved expense as reimbursed")
def reimburse_expense(expense_id: int, actor: User = Depends(approver), db: Session = Depends(get_db)):
    return ExpenseService(db).reimburse(actor, expense_id)
