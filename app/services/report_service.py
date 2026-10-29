import math
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportPage
from app.services.budget_service import BudgetService
from app.utils.date_utils import today
from app.utils.enums import (
    BeneficiaryCategory, BudgetScope, CampaignStatus, DonationStatus, ExpenseCategory, ExpenseStatus, ProjectStatus,
    ResourceCategory, VolunteerStatus,
)
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

EXPORT_ROW_CAP = 100_000


def normalize(value: Any) -> Any:
    """Make a DB value JSON/CSV friendly."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return float(round(value, 2))
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, date):
        return value.isoformat()
    return value


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReportRepository(db)

    # ------------------------------------------------------------------ runner
    def _execute(self, name: str, stmt: Select, params: PaginationParams | None, sort: SortParams, default_sort: str, default_order: str = "asc") -> ReportPage:
        sub = stmt.subquery()
        columns = list(sub.c.keys())
        field = sort.sort_by or default_sort
        if field not in columns:
            raise BadRequestError(f"Cannot sort by '{field}'. Available: {', '.join(columns)}")
        direction = sort.order if sort.sort_by else default_order
        order = desc(sub.c[field]) if direction == "desc" else asc(sub.c[field])
        query = select(sub).order_by(order)
        total = self.db.scalar(select(func.count()).select_from(sub)) or 0
        if params is None:  # export: everything (capped)
            query = query.limit(EXPORT_ROW_CAP)
            page, page_size, pages = 1, total, 1
        else:
            query = query.limit(params.page_size).offset(params.offset)
            page, page_size, pages = params.page, params.page_size, math.ceil(total / params.page_size)
        rows = [{k: normalize(v) for k, v in row.items()} for row in self.db.execute(query).mappings().all()]
        return ReportPage(report=name, columns=columns, rows=rows, total=total, page=page, page_size=page_size, pages=pages)

    # ------------------------------------------------------------------ finance reports
    def donation_summary(self, params, sort, *, group_by: str, campaign_id: int | None, status: DonationStatus | None, date_from: date | None, date_to: date | None):
        stmt = self.repo.donation_summary(group_by, campaign_id=campaign_id, status=status, date_from=date_from, date_to=date_to)
        return self._execute("donation_summary", stmt, params, sort, "total_amount", "desc")

    def campaign_performance(self, params, sort, *, campaign_id: int | None, status: CampaignStatus | None, date_from: date | None, date_to: date | None):
        stmt = self.repo.campaign_performance(campaign_id=campaign_id, status=status, date_from=date_from, date_to=date_to)
        return self._execute("campaign_performance", stmt, params, sort, "campaign_id")

    def expense_report(
        self, params, sort, *, project_id: int | None, campaign_id: int | None, status: ExpenseStatus | None,
        category: ExpenseCategory | None, date_from: date | None, date_to: date | None,
    ):
        stmt = self.repo.expense_report(
            project_id=project_id, campaign_id=campaign_id, status=status, category=category, date_from=date_from, date_to=date_to
        )
        return self._execute("expenses", stmt, params, sort, "expense_date", "desc")

    def budget_utilization(self, params: PaginationParams | None, sort: SortParams, *, scope: BudgetScope | None, only_overruns: bool) -> ReportPage:
        rows = [
            {k: normalize(v) for k, v in u.model_dump().items()}
            for u in BudgetService(self.db).list_utilization(scope=scope, only_overruns=only_overruns)
        ]
        columns = list(rows[0].keys()) if rows else [
            "scope", "entity_id", "entity_name", "budget", "spent", "pending", "remaining", "utilization_pct", "is_overrun", "overrun_amount"
        ]
        field = sort.sort_by or "utilization_pct"
        if field not in columns:
            raise BadRequestError(f"Cannot sort by '{field}'. Available: {', '.join(columns)}")
        reverse = (sort.order == "desc") if sort.sort_by else True
        rows.sort(key=lambda r: (r[field] is None, r[field]), reverse=reverse)
        total = len(rows)
        if params is not None:
            rows = rows[params.offset: params.offset + params.page_size]
            page, size, pages = params.page, params.page_size, math.ceil(total / params.page_size)
        else:
            page, size, pages = 1, total, 1
        return ReportPage(report="budget_utilization", columns=columns, rows=rows, total=total, page=page, page_size=size, pages=pages)

    # ------------------------------------------------------------------ operations reports
    def volunteer_contribution(self, params, sort, *, project_id: int | None, status: VolunteerStatus | None, date_from: date | None, date_to: date | None):
        stmt = self.repo.volunteer_contribution(project_id=project_id, status=status, date_from=date_from, date_to=date_to)
        return self._execute("volunteer_contribution", stmt, params, sort, "total_hours", "desc")

    def project_progress(
        self, params, sort, *, project_id: int | None, status: ProjectStatus | None, campaign_id: int | None,
        date_from: date | None, date_to: date | None,
    ):
        stmt = self.repo.project_progress(
            today(), project_id=project_id, status=status, campaign_id=campaign_id, date_from=date_from, date_to=date_to
        )
        return self._execute("project_progress", stmt, params, sort, "project_id")

    def resource_distribution(
        self, params, sort, *, project_id: int | None, resource_id: int | None, category: ResourceCategory | None,
        date_from: date | None, date_to: date | None,
    ):
        stmt = self.repo.resource_distribution(
            project_id=project_id, resource_id=resource_id, category=category, date_from=date_from, date_to=date_to
        )
        return self._execute("resource_distribution", stmt, params, sort, "resource_id")

    def beneficiary_impact(
        self, params, sort, *, group_by: str, project_id: int | None, category: BeneficiaryCategory | None,
        date_from: date | None, date_to: date | None,
    ):
        stmt = self.repo.beneficiary_impact(group_by, project_id=project_id, category=category, date_from=date_from, date_to=date_to)
        return self._execute("beneficiary_impact", stmt, params, sort, "beneficiaries_served", "desc")
