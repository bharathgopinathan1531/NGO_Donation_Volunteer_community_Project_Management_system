from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignOut, CampaignUpdate
from app.schemas.common import Page
from app.services.campaign_service import CampaignService
from app.utils.enums import CampaignCategory, CampaignStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
reader = require_permissions(Permission.CAMPAIGNS_READ)
writer = require_permissions(Permission.CAMPAIGNS_WRITE)


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED, summary="Create a fundraising campaign (starts as draft)")
def create_campaign(payload: CampaignCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return CampaignService.serialize(CampaignService(db).create(actor, payload))


@router.get("", response_model=Page[CampaignOut])
def list_campaigns(
    search: str | None = None, status: CampaignStatus | None = None, category: CampaignCategory | None = None,
    manager_id: int | None = None, date_from: date | None = Query(None, description="Campaign start on/after"),
    date_to: date | None = Query(None, description="Campaign start on/before"),
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(reader), db: Session = Depends(get_db),
):
    items, total = CampaignService(db).list_campaigns(
        actor, params, sort, search=search, status=status, category=category, manager_id=manager_id, date_from=date_from, date_to=date_to
    )
    return build_page([CampaignService.serialize(i) for i in items], total, params)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, actor: User = Depends(reader), db: Session = Depends(get_db)):
    return CampaignService.serialize(CampaignService(db).get_for_actor(actor, campaign_id))


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, payload: CampaignUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return CampaignService.serialize(CampaignService(db).update(actor, campaign_id, payload))


def _transition(target: CampaignStatus, summary: str):
    def endpoint(campaign_id: int, actor: User = Depends(writer), db: Session = Depends(get_db)):
        return CampaignService.serialize(CampaignService(db).change_status(actor, campaign_id, target))

    router.add_api_route(f"/{{campaign_id}}/{summary_path[target]}", endpoint, methods=["POST"], response_model=CampaignOut, summary=summary)


summary_path = {
    CampaignStatus.ACTIVE: "activate", CampaignStatus.PAUSED: "pause",
    CampaignStatus.COMPLETED: "close", CampaignStatus.CANCELLED: "cancel",
}
_transition(CampaignStatus.ACTIVE, "Activate (or resume) a campaign")
_transition(CampaignStatus.PAUSED, "Pause an active campaign")
_transition(CampaignStatus.COMPLETED, "Close a campaign as completed")
_transition(CampaignStatus.CANCELLED, "Cancel a campaign")
