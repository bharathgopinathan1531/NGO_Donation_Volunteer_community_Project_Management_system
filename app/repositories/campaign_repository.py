from datetime import date, timedelta

from sqlalchemy import func, select

from app.models.campaign import Campaign
from app.repositories import BaseRepository
from app.utils.enums import CampaignCategory, CampaignStatus
from app.utils.filtering import apply_date_range, apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class CampaignRepository(BaseRepository[Campaign]):
    model = Campaign

    def list_campaigns(
        self, params: PaginationParams, sort: SortParams, *, search: str | None, status: CampaignStatus | None,
        category: CampaignCategory | None, manager_id: int | None, date_from: date | None, date_to: date | None,
    ):
        stmt = apply_equals(select(Campaign), Campaign, status=status, category=category, manager_id=manager_id)
        stmt = apply_search(stmt, [Campaign.title, Campaign.description], search)
        stmt = apply_date_range(stmt, Campaign.start_date, date_from, date_to)
        stmt = apply_sorting(
            stmt, Campaign, sort, {"id", "title", "goal_amount", "raised_amount", "start_date", "end_date", "status", "created_at"}
        )
        return paginate(self.db, stmt, params)

    def closing_soon(self, today: date, days: int) -> list[Campaign]:
        stmt = select(Campaign).where(
            Campaign.status == CampaignStatus.ACTIVE, Campaign.end_date >= today, Campaign.end_date <= today + timedelta(days=days)
        )
        return list(self.db.scalars(stmt).all())

    def count_by_status(self, status: CampaignStatus) -> int:
        return self.db.scalar(select(func.count()).select_from(Campaign).where(Campaign.status == status)) or 0
