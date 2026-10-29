from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.utils.enums import ApprovalAction


class SubmitForApproval(BaseModel):
    comments: str | None = Field(default=None, max_length=2000)


class ApprovalDecision(BaseModel):
    comments: str | None = Field(default=None, max_length=2000)


class RejectDecision(BaseModel):
    comments: str = Field(min_length=3, max_length=2000)  # a reason is mandatory when rejecting


class ApprovalOut(ORMModel):
    id: int
    project_id: int
    action: ApprovalAction
    comments: str | None
    actor_id: int | None
    created_at: datetime
