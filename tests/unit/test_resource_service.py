import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.stock_transaction import StockTransaction
from app.schemas.resource import ResourceCreate
from app.schemas.resource_allocation import AllocationCreate
from app.services.resource_allocation_service import ResourceAllocationService
from app.services.resource_service import ResourceService
from app.utils.enums import ProjectStatus, ResourceCategory, Role, StockTransactionType
from sqlalchemy import select
from tests.unit.factories import mk_project, mk_resource


def ledger(db, resource):
    return list(db.scalars(select(StockTransaction).where(StockTransaction.resource_id == resource.id).order_by(StockTransaction.id)))


def test_create_with_opening_balance_writes_ledger(db, make_user):
    admin = make_user(Role.NGO_MANAGER)
    r = ResourceService(db).create(admin, ResourceCreate(name="Kits", category=ResourceCategory.EMERGENCY_KIT, initial_quantity=25))
    rows = ledger(db, r)
    assert r.quantity == 25 and len(rows) == 1 and rows[0].balance_after == 25 and rows[0].transaction_type == StockTransactionType.STOCK_IN


def test_duplicate_resource_name(db, make_user):
    admin = make_user(Role.NGO_MANAGER)
    ResourceService(db).create(admin, ResourceCreate(name="Kits", category=ResourceCategory.EMERGENCY_KIT))
    with pytest.raises(ConflictError):
        ResourceService(db).create(admin, ResourceCreate(name="Kits", category=ResourceCategory.EMERGENCY_KIT))


def test_stock_in_and_out_keep_balance_and_ledger(db, make_user):
    admin, r = make_user(Role.NGO_MANAGER), mk_resource(db, qty=10)
    svc = ResourceService(db)
    svc.stock_in(admin, r.id, 15, "donation", "GRN-1")
    svc.stock_out(admin, r.id, 5, "damaged", None)
    assert r.quantity == 20
    assert [(t.transaction_type.value, t.quantity, t.balance_after) for t in ledger(db, r)] == [("stock_in", 15, 25), ("stock_out", 5, 20)]


def test_negative_inventory_is_impossible(db, make_user):
    admin, r = make_user(Role.NGO_MANAGER), mk_resource(db, qty=5)
    with pytest.raises(BusinessRuleError) as exc:
        ResourceService(db).stock_out(admin, r.id, 6, "too many", None)
    assert exc.value.extra == {"available": 5, "requested": 6}
    assert r.quantity == 5 and ledger(db, r) == []  # nothing was written


def test_zero_or_negative_quantities_rejected(db, make_user):
    admin, r = make_user(Role.NGO_MANAGER), mk_resource(db)
    with pytest.raises(BusinessRuleError):
        ResourceService(db).stock_in(admin, r.id, 0, None, None)
    with pytest.raises(BusinessRuleError):
        ResourceService(db).stock_out(admin, r.id, -3, "x", None)


def test_db_check_constraint_is_a_second_line_of_defence(db):
    from sqlalchemy.exc import IntegrityError

    r = mk_resource(db, qty=1)
    r.quantity = -1
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_low_stock_flag_and_alert(db, make_user):
    admin, r = make_user(Role.NGO_MANAGER), mk_resource(db, qty=12, threshold=10)
    svc = ResourceService(db)
    assert svc.low_stock() == []
    svc.stock_out(admin, r.id, 2, "distribution", None)  # exactly at threshold -> low
    assert [x.id for x in svc.low_stock()] == [r.id]
    from app.repositories.notification_repository import NotificationRepository
    from app.utils.pagination import PaginationParams

    notes, _ = NotificationRepository(db).list_for_user(admin.id, PaginationParams())
    assert [n.type.value for n in notes] == ["low_stock"]
    svc.stock_out(admin, r.id, 1, "distribution", None)  # second alert the same day is de-duplicated
    assert NotificationRepository(db).list_for_user(admin.id, PaginationParams())[1] == 1


def test_allocation_reduces_stock_and_links_ledger_to_project(db, make_user):
    admin, r, p = make_user(Role.NGO_MANAGER), mk_resource(db, qty=50), mk_project(db)
    alloc = ResourceAllocationService(db).allocate(admin, AllocationCreate(resource_id=r.id, project_id=p.id, quantity=20))
    assert r.quantity == 30 and alloc.quantity == 20
    tx = ledger(db, r)[-1]
    assert tx.transaction_type == StockTransactionType.ALLOCATION and tx.project_id == p.id and tx.balance_after == 30


def test_over_allocation_is_rejected_atomically(db, make_user):
    admin, r, p = make_user(Role.NGO_MANAGER), mk_resource(db, qty=10), mk_project(db)
    svc = ResourceAllocationService(db)
    with pytest.raises(BusinessRuleError):
        svc.allocate(admin, AllocationCreate(resource_id=r.id, project_id=p.id, quantity=11))
    assert r.quantity == 10 and svc.list_allocations(__import__("app.utils.pagination", fromlist=["x"]).PaginationParams(), __import__("app.utils.sorting", fromlist=["x"]).SortParams(), resource_id=None, project_id=None, date_from=None, date_to=None)[1] == 0


def test_cannot_allocate_to_planning_project_or_missing_resource(db, make_user):
    admin, r = make_user(Role.NGO_MANAGER), mk_resource(db)
    planning = mk_project(db, status=ProjectStatus.PLANNING)
    with pytest.raises(BusinessRuleError):
        ResourceAllocationService(db).allocate(admin, AllocationCreate(resource_id=r.id, project_id=planning.id, quantity=1))
    ok = mk_project(db, name="Active")
    with pytest.raises(NotFoundError):
        ResourceAllocationService(db).allocate(admin, AllocationCreate(resource_id=999, project_id=ok.id, quantity=1))
