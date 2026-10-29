"""Direct-to-database object factories for service-level (unit) tests."""
from datetime import date, timedelta
from decimal import Decimal

from app.models.beneficiary import Beneficiary
from app.models.campaign import Campaign
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.resource import Resource
from app.models.task import Task
from app.models.volunteer import Volunteer
from app.utils.enums import (
    BeneficiaryCategory, CampaignStatus, DonationMethod, DonationStatus, MilestoneStatus, ProjectStatus, ResourceCategory,
    TaskStatus,
)

TODAY = date.today()


def _save(db, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def mk_donor(db, name="Donor One", email="donor1@example.org", **kw) -> Donor:
    return _save(db, Donor(name=name, email=email, **kw))


def mk_campaign(db, status=CampaignStatus.ACTIVE, goal="10000.00", **kw) -> Campaign:
    return _save(
        db,
        Campaign(
            title=kw.pop("title", "Campaign"), goal_amount=Decimal(goal), raised_amount=Decimal(kw.pop("raised", "0")), status=status,
            start_date=kw.pop("start_date", TODAY - timedelta(days=30)), end_date=kw.pop("end_date", TODAY + timedelta(days=60)), **kw,
        ),
    )


def mk_project(db, status=ProjectStatus.ACTIVE, budget="5000.00", **kw) -> Project:
    return _save(
        db,
        Project(
            name=kw.pop("name", "Project"), status=status, budget=Decimal(budget),
            start_date=kw.pop("start_date", TODAY - timedelta(days=30)), end_date=kw.pop("end_date", TODAY + timedelta(days=90)), **kw,
        ),
    )


def mk_volunteer(db, email="vol1@example.org", name="Volunteer One", **kw) -> Volunteer:
    return _save(db, Volunteer(full_name=name, email=email, **kw))


def mk_resource(db, name="Blankets", qty=50, threshold=10) -> Resource:
    return _save(db, Resource(name=name, category=ResourceCategory.CLOTHING, quantity=qty, low_stock_threshold=threshold, unit="pcs"))


def mk_beneficiary(db, name="Beneficiary", **kw) -> Beneficiary:
    kw.setdefault("phone", "9999999999")
    kw.setdefault("address", "Secret street 1")
    kw.setdefault("national_id", "ID-123")
    return _save(db, Beneficiary(full_name=name, category=BeneficiaryCategory.FAMILY, **kw))


def mk_donation(db, donor, campaign, amount="100.00", status=DonationStatus.CONFIRMED, ref="D-1") -> Donation:
    d = _save(
        db,
        Donation(
            donor_id=donor.id, campaign_id=campaign.id, amount=Decimal(amount), donation_date=TODAY - timedelta(days=1),
            method=DonationMethod.CASH, reference_number=ref, status=status,
        ),
    )
    if status == DonationStatus.CONFIRMED:
        campaign.raised_amount = Decimal(campaign.raised_amount) + Decimal(amount)
        db.commit()
    return d


def mk_milestone(db, project, title="M1", due=None, status=MilestoneStatus.PENDING) -> Milestone:
    return _save(db, Milestone(project_id=project.id, title=title, due_date=due or TODAY + timedelta(days=10), status=status))


def mk_task(db, milestone, title="T1", deadline=None, status=TaskStatus.TODO, progress=0, assignee_id=None) -> Task:
    return _save(
        db, Task(milestone_id=milestone.id, title=title, deadline=deadline or TODAY + timedelta(days=5), status=status, progress=progress, assignee_id=assignee_id)
    )
