from datetime import timedelta

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.schemas.beneficiary import BeneficiaryCreate
from app.schemas.beneficiary_assistance import AssistanceCreate
from app.schemas.resource_allocation import AllocationCreate
from app.services.assistance_service import AssistanceService
from app.services.beneficiary_service import BeneficiaryService
from app.services.resource_allocation_service import ResourceAllocationService
from app.utils.enums import BeneficiaryCategory, ProjectStatus, Role
from tests.unit.factories import TODAY, mk_beneficiary, mk_project, mk_resource


def test_sensitive_fields_redacted_for_unprivileged_roles(db, make_user):
    b = mk_beneficiary(db)
    svc = BeneficiaryService(db)
    full = svc.serialize(make_user(Role.NGO_MANAGER), b)
    redacted = svc.serialize(make_user(Role.VOLUNTEER_COORDINATOR), b)
    assert (full.phone, full.address, full.national_id) == ("9999999999", "Secret street 1", "ID-123")
    assert (redacted.phone, redacted.address, redacted.national_id, redacted.notes) == (None, None, None, None)
    assert redacted.full_name == b.full_name  # non-sensitive data still visible


def test_registration_maps_projects_and_audit_omits_sensitive_values(db, make_user):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    admin, p = make_user(Role.SUPER_ADMIN), mk_project(db)
    svc = BeneficiaryService(db)
    b = svc.create(admin, BeneficiaryCreate(full_name="Meera", category=BeneficiaryCategory.WOMAN, national_id="SECRET-ID", project_ids=[p.id, p.id]))
    assert svc.repo.project_ids(b.id) == [p.id]
    log = db.scalar(select(AuditLog).where(AuditLog.action == "beneficiary.registered"))
    assert "SECRET-ID" not in str(log.details)


def test_unknown_project_rejected_on_registration(db, make_user):
    with pytest.raises(NotFoundError):
        BeneficiaryService(db).create(make_user(Role.SUPER_ADMIN), BeneficiaryCreate(full_name="Meera", category=BeneficiaryCategory.WOMAN, project_ids=[404]))


def test_map_and_unmap(db, make_user):
    admin, p, b = make_user(Role.SUPER_ADMIN), mk_project(db), mk_beneficiary(db)
    svc = BeneficiaryService(db)
    svc.map_project(admin, b.id, p.id)
    with pytest.raises(ConflictError):
        svc.map_project(admin, b.id, p.id)
    svc.unmap_project(admin, b.id, p.id)
    with pytest.raises(NotFoundError):
        svc.unmap_project(admin, b.id, p.id)


def assist(b, p, r=None, qty=0, **kw):
    return AssistanceCreate(beneficiary_id=b.id, project_id=p.id, resource_id=r.id if r else None, assistance_type="food", quantity=qty, distribution_date=TODAY - timedelta(days=1), **kw)


def test_assistance_requires_project_mapping(db, make_user):
    admin, p, b = make_user(Role.SUPER_ADMIN), mk_project(db), mk_beneficiary(db)
    with pytest.raises(BusinessRuleError):
        AssistanceService(db).record(admin, assist(b, p))
    BeneficiaryService(db).map_project(admin, b.id, p.id)
    assert AssistanceService(db).record(admin, assist(b, p)).id


def test_distribution_cannot_exceed_allocation(db, make_user):
    admin, p, b, r = make_user(Role.SUPER_ADMIN), mk_project(db), mk_beneficiary(db), mk_resource(db, qty=100)
    BeneficiaryService(db).map_project(admin, b.id, p.id)
    ResourceAllocationService(db).allocate(admin, AllocationCreate(resource_id=r.id, project_id=p.id, quantity=10))
    svc = AssistanceService(db)
    svc.record(admin, assist(b, p, r, 6))
    with pytest.raises(BusinessRuleError) as exc:
        svc.record(admin, assist(b, p, r, 5))
    assert exc.value.extra["allocated"] == 10 and exc.value.extra["already_distributed"] == 6
    svc.record(admin, assist(b, p, r, 4))  # exactly the remainder is fine


def test_assistance_validation_rules(db, make_user):
    admin, p, b, r = make_user(Role.SUPER_ADMIN), mk_project(db), mk_beneficiary(db), mk_resource(db)
    BeneficiaryService(db).map_project(admin, b.id, p.id)
    svc = AssistanceService(db)
    with pytest.raises(BusinessRuleError):
        svc.record(admin, assist(b, p, r, 0))  # resource needs a quantity
    with pytest.raises(BusinessRuleError):
        svc.record(admin, assist(b, p, None, 3))  # quantity needs a resource
    future = assist(b, p).model_copy(update={"distribution_date": TODAY + timedelta(days=1)})
    with pytest.raises(BusinessRuleError):
        svc.record(admin, future)
    planning = mk_project(db, name="Plan", status=ProjectStatus.PLANNING)
    BeneficiaryService(db).map_project(admin, b.id, planning.id)
    with pytest.raises(BusinessRuleError):
        svc.record(admin, assist(b, planning))
