from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import ReportPage
from app.services.report_service import ReportService
from app.utils.csv_export import rows_to_csv_response
from app.utils.enums import (
    BeneficiaryCategory, BudgetScope, CampaignStatus, DonationStatus, ExpenseCategory, ExpenseStatus, ProjectStatus,
    ResourceCategory, VolunteerStatus,
)
from app.utils.pagination import PaginationParams, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/reports", tags=["Reports"])
finance = require_permissions(Permission.REPORTS_FINANCE)
operations = require_permissions(Permission.REPORTS_OPERATIONS)

EXPORT = Query(False, description="true = download the full result set as CSV (ignores pagination)")


def _out(report: ReportPage, export: bool, filename: str):
    if export:
        return rows_to_csv_response(f"{filename}.csv", report.rows, report.columns)
    return report


@router.get("/donation-summary", response_model=ReportPage, summary="Donation summary grouped by campaign / donor / method / status / month")
def donation_summary(
    group_by: Literal["campaign", "donor", "method", "status", "month"] = "campaign",
    campaign_id: int | None = None, status: DonationStatus | None = None, date_from: date | None = None, date_to: date | None = None,
    export: bool = EXPORT, params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(finance), db: Session = Depends(get_db),
):
    rep = ReportService(db).donation_summary(
        None if export else params, sort, group_by=group_by, campaign_id=campaign_id, status=status, date_from=date_from, date_to=date_to
    )
    return _out(rep, export, "donation_summary")


@router.get("/campaign-performance", response_model=ReportPage)
def campaign_performance(
    campaign_id: int | None = None, status: CampaignStatus | None = None, date_from: date | None = None, date_to: date | None = None,
    export: bool = EXPORT, params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(finance), db: Session = Depends(get_db),
):
    rep = ReportService(db).campaign_performance(
        None if export else params, sort, campaign_id=campaign_id, status=status, date_from=date_from, date_to=date_to
    )
    return _out(rep, export, "campaign_performance")


@router.get("/expenses", response_model=ReportPage)
def expense_report(
    project_id: int | None = None, campaign_id: int | None = None, status: ExpenseStatus | None = None,
    category: ExpenseCategory | None = None, date_from: date | None = None, date_to: date | None = None,
    export: bool = EXPORT, params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(finance), db: Session = Depends(get_db),
):
    rep = ReportService(db).expense_report(
        None if export else params, sort, project_id=project_id, campaign_id=campaign_id, status=status, category=category,
        date_from=date_from, date_to=date_to,
    )
    return _out(rep, export, "expenses")


@router.get("/budget-utilization", response_model=ReportPage)
def budget_utilization(
    scope: BudgetScope | None = None, only_overruns: bool = False, export: bool = EXPORT,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(finance), db: Session = Depends(get_db),
):
    rep = ReportService(db).budget_utilization(None if export else params, sort, scope=scope, only_overruns=only_overruns)
    return _out(rep, export, "budget_utilization")


@router.get("/volunteer-contribution", response_model=ReportPage)
def volunteer_contribution(
    project_id: int | None = None, status: VolunteerStatus | None = None, date_from: date | None = None, date_to: date | None = None,
    export: bool = EXPORT, params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(operations), db: Session = Depends(get_db),
):
    rep = ReportService(db).volunteer_contribution(
        None if export else params, sort, project_id=project_id, status=status, date_from=date_from, date_to=date_to
    )
    return _out(rep, export, "volunteer_contribution")


@router.get("/project-progress", response_model=ReportPage)
def project_progress(
    project_id: int | None = None, status: ProjectStatus | None = None, campaign_id: int | None = None,
    date_from: date | None = None, date_to: date | None = None,
    export: bool = EXPORT, params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(operations), db: Session = Depends(get_db),
):
    rep = ReportService(db).project_progress(
        None if export else params, sort, project_id=project_id, status=status, campaign_id=campaign_id, date_from=date_from, date_to=date_to
    )
    return _out(rep, export, "project_progress")


@router.get("/resource-distribution", response_model=ReportPage)
def resource_distribution(
    project_id: int | None = None, resource_id: int | None = None, category: ResourceCategory | None = None,
    date_from: date | None = None, date_to: date | None = None,
    export: bool = EXPORT, params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(operations), db: Session = Depends(get_db),
):
    rep = ReportService(db).resource_distribution(
        None if export else params, sort, project_id=project_id, resource_id=resource_id, category=category,
        date_from=date_from, date_to=date_to,
    )
    return _out(rep, export, "resource_distribution")


@router.get("/beneficiary-impact", response_model=ReportPage)
def beneficiary_impact(
    group_by: Literal["project", "category"] = "project", project_id: int | None = None, category: BeneficiaryCategory | None = None,
    date_from: date | None = None, date_to: date | None = None,
    export: bool = EXPORT, params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(operations), db: Session = Depends(get_db),
):
    rep = ReportService(db).beneficiary_impact(
        None if export else params, sort, group_by=group_by, project_id=project_id, category=category, date_from=date_from, date_to=date_to
    )
    return _out(rep, export, "beneficiary_impact")
