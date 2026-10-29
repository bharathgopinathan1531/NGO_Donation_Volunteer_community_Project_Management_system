from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.resource import ResourceCreate, ResourceOut, ResourceUpdate
from app.schemas.stock_transaction import StockMovement, StockOutMovement, StockTransactionOut
from app.services.resource_service import ResourceService, serialize
from app.services.stock_transaction_service import StockTransactionService
from app.utils.enums import ResourceCategory, StockTransactionType
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/resources", tags=["Resources & Inventory"])
reader = require_permissions(Permission.RESOURCES_READ)
writer = require_permissions(Permission.RESOURCES_WRITE)


@router.post("", response_model=ResourceOut, status_code=status.HTTP_201_CREATED, summary="Register a resource (optional opening stock)")
def create_resource(payload: ResourceCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return serialize(ResourceService(db).create(actor, payload))


@router.get("", response_model=Page[ResourceOut])
def list_resources(
    category: ResourceCategory | None = None, search: str | None = None, low_stock_only: bool = False,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(reader), db: Session = Depends(get_db),
):
    items, total = ResourceService(db).list_resources(params, sort, category=category, search=search, low_stock_only=low_stock_only)
    return build_page([serialize(i) for i in items], total, params)


@router.get("/low-stock", response_model=list[ResourceOut], summary="Low-stock alerts")
def low_stock(_: User = Depends(reader), db: Session = Depends(get_db)):
    return [serialize(r) for r in ResourceService(db).low_stock()]


@router.get("/transactions", response_model=Page[StockTransactionOut], summary="Stock movement ledger / distribution history")
def transactions(
    resource_id: int | None = None, project_id: int | None = None, transaction_type: StockTransactionType | None = None,
    date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(reader), db: Session = Depends(get_db),
):
    items, total = StockTransactionService(db).list_transactions(
        params, sort, resource_id=resource_id, project_id=project_id, transaction_type=transaction_type, date_from=date_from, date_to=date_to
    )
    return build_page([StockTransactionOut.model_validate(i) for i in items], total, params)


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(resource_id: int, _: User = Depends(reader), db: Session = Depends(get_db)):
    return serialize(ResourceService(db).get(resource_id))


@router.patch("/{resource_id}", response_model=ResourceOut)
def update_resource(resource_id: int, payload: ResourceUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return serialize(ResourceService(db).update(actor, resource_id, payload))


@router.post("/{resource_id}/stock-in", response_model=StockTransactionOut, status_code=status.HTTP_201_CREATED)
def stock_in(resource_id: int, payload: StockMovement, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return ResourceService(db).stock_in(actor, resource_id, payload.quantity, payload.reason, payload.reference)


@router.post("/{resource_id}/stock-out", response_model=StockTransactionOut, status_code=status.HTTP_201_CREATED, summary="Stock out (never below zero)")
def stock_out(resource_id: int, payload: StockOutMovement, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return ResourceService(db).stock_out(actor, resource_id, payload.quantity, payload.reason, payload.reference)
