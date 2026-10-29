from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    BeneficiaryMetrics, CampaignMetrics, DashboardOverview, DonationMetrics, ExpenseMetrics, ProjectMetrics, ResourceMetrics,
    VolunteerMetrics,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
reader = require_permissions(Permission.DASHBOARD_READ)


@router.get("", response_model=DashboardOverview, summary="All dashboard metrics (computed from database records)")
def overview(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).overview()


@router.get("/donations", response_model=DonationMetrics, summary="Total and confirmed donations")
def donations(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).donations()


@router.get("/campaigns", response_model=CampaignMetrics, summary="Active campaigns and goal achievement")
def campaigns(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).campaigns()


@router.get("/volunteers", response_model=VolunteerMetrics, summary="Volunteers and hours")
def volunteers(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).volunteers()


@router.get("/projects", response_model=ProjectMetrics, summary="Active projects, pending approvals, budget utilization")
def projects(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).projects()


@router.get("/expenses", response_model=ExpenseMetrics, summary="Pending expense approvals")
def expenses(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).expenses()


@router.get("/resources", response_model=ResourceMetrics, summary="Resource stock levels")
def resources(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).resources()


@router.get("/beneficiaries", response_model=BeneficiaryMetrics, summary="Beneficiaries registered and served")
def beneficiaries(_: User = Depends(reader), db: Session = Depends(get_db)):
    return DashboardService(db).beneficiaries()
