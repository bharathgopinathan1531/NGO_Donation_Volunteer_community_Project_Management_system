from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.project_approval import ApprovalDecision, ApprovalOut, RejectDecision, SubmitForApproval
from app.services.approval_service import ApprovalService
from app.utils.pagination import PaginationParams, build_page, pagination_params

router = APIRouter(tags=["Project Approvals"])


@router.post("/projects/{project_id}/submit", response_model=ApprovalOut, status_code=status.HTTP_201_CREATED, summary="Submit a project for approval")
def submit(project_id: int, payload: SubmitForApproval | None = None, actor: User = Depends(require_permissions(Permission.PROJECTS_SUBMIT)), db: Session = Depends(get_db)):
    return ApprovalService(db).submit(actor, project_id, payload.comments if payload else None)


@router.post("/projects/{project_id}/approve", response_model=ApprovalOut, summary="Approve a submitted project")
def approve(project_id: int, payload: ApprovalDecision | None = None, actor: User = Depends(require_permissions(Permission.PROJECTS_APPROVE)), db: Session = Depends(get_db)):
    return ApprovalService(db).approve(actor, project_id, payload.comments if payload else None)


@router.post("/projects/{project_id}/reject", response_model=ApprovalOut, summary="Reject a submitted project (comment required)")
def reject(project_id: int, payload: RejectDecision, actor: User = Depends(require_permissions(Permission.PROJECTS_APPROVE)), db: Session = Depends(get_db)):
    return ApprovalService(db).reject(actor, project_id, payload.comments)


@router.get("/projects/{project_id}/approvals", response_model=list[ApprovalOut], summary="Approval history of a project")
def history(project_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ApprovalService(db).history(actor, project_id)


@router.get("/approvals/pending", response_model=Page[ApprovalOut], summary="Projects waiting for an approval decision")
def pending(
    params: PaginationParams = Depends(pagination_params),
    _: User = Depends(require_permissions(Permission.PROJECTS_APPROVE)), db: Session = Depends(get_db),
):
    items, total = ApprovalService(db).pending(params)
    return build_page([ApprovalOut.model_validate(i) for i in items], total, params)
