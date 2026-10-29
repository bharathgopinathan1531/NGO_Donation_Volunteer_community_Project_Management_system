from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.db.session import transaction
from app.models.resource import Resource
from app.models.stock_transaction import StockTransaction
from app.models.user import User
from app.repositories.resource_repository import ResourceRepository
from app.repositories.stock_transaction_repository import StockTransactionRepository
from app.schemas.resource import ResourceCreate, ResourceOut, ResourceUpdate
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.utils.date_utils import today
from app.utils.enums import NotificationType, ResourceCategory, StockTransactionType
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams


def serialize(r: Resource) -> ResourceOut:
    out = ResourceOut.model_validate(r)
    out.is_low_stock = r.quantity <= r.low_stock_threshold
    return out


class ResourceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ResourceRepository(db)
        self.ledger = StockTransactionRepository(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    def get(self, resource_id: int) -> Resource:
        r = self.repo.get(resource_id)
        if not r:
            raise NotFoundError("Resource not found")
        return r

    # ------------------------------------------------------------------ the single place stock changes
    def apply_movement(
        self, actor: User | None, resource_id: int, kind: StockTransactionType, quantity: int, *, project_id: int | None = None,
        reason: str | None = None, reference: str | None = None,
    ) -> StockTransaction:
        """Lock the resource row, refuse negative inventory, write the ledger entry. Runs in the caller's transaction."""
        if quantity <= 0:
            raise BusinessRuleError("Quantity must be positive")
        r = self.repo.get(resource_id, for_update=True)
        if not r:
            raise NotFoundError("Resource not found")
        delta = quantity if kind == StockTransactionType.STOCK_IN else -quantity
        new_balance = r.quantity + delta
        if new_balance < 0:
            raise BusinessRuleError(
                f"Insufficient stock for '{r.name}': {r.quantity} {r.unit} available, {quantity} requested",
                extra={"available": r.quantity, "requested": quantity},
            )
        r.quantity = new_balance
        tx = self.ledger.add(
            StockTransaction(
                resource_id=r.id, transaction_type=kind, quantity=quantity, balance_after=new_balance, project_id=project_id,
                reason=reason, reference=reference, created_by=actor.id if actor else None,
            )
        )
        self.audit.log(
            actor, f"resource.{kind.value}", "resource", r.id,
            {"quantity": quantity, "balance_after": new_balance, "project_id": project_id, "reason": reason, "reference": reference},
        )
        if new_balance <= r.low_stock_threshold:
            self.notifications.notify(
                self.notifications.privileged_ids(), NotificationType.LOW_STOCK, "Low stock",
                f"'{r.name}' is low: {new_balance} {r.unit} left (threshold {r.low_stock_threshold}).",
                entity="resource", entity_id=r.id, dedupe_key=f"low_stock:{r.id}:{today().isoformat()}",
            )
        return tx

    # ------------------------------------------------------------------ commands
    def create(self, actor: User, data: ResourceCreate) -> Resource:
        if self.repo.get_by_name(data.name.strip()):
            raise ConflictError("A resource with this name already exists")
        with transaction(self.db):
            r = self.repo.add(
                Resource(
                    name=data.name.strip(), category=data.category, description=data.description, unit=data.unit,
                    quantity=0, low_stock_threshold=data.low_stock_threshold,
                )
            )
            self.audit.log(actor, "resource.created", "resource", r.id, {"name": r.name, "category": r.category})
            if data.initial_quantity > 0:
                self.apply_movement(actor, r.id, StockTransactionType.STOCK_IN, data.initial_quantity, reason="Opening balance")
        return r

    def update(self, actor: User, resource_id: int, data: ResourceUpdate) -> Resource:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k == "description"}
        with transaction(self.db):
            r = self.get(resource_id)
            if "name" in changes:
                changes["name"] = changes["name"].strip()
                other = self.repo.get_by_name(changes["name"])
                if other and other.id != r.id:
                    raise ConflictError("A resource with this name already exists")
            for k, v in changes.items():
                setattr(r, k, v)
            self.audit.log(actor, "resource.updated", "resource", r.id, {"changes": changes})
        return r

    def stock_in(self, actor: User, resource_id: int, quantity: int, reason: str | None, reference: str | None) -> StockTransaction:
        with transaction(self.db):
            return self.apply_movement(actor, resource_id, StockTransactionType.STOCK_IN, quantity, reason=reason, reference=reference)

    def stock_out(self, actor: User, resource_id: int, quantity: int, reason: str, reference: str | None) -> StockTransaction:
        with transaction(self.db):
            return self.apply_movement(actor, resource_id, StockTransactionType.STOCK_OUT, quantity, reason=reason, reference=reference)

    # ------------------------------------------------------------------ queries
    def list_resources(self, params: PaginationParams, sort: SortParams, *, category: ResourceCategory | None, search: str | None, low_stock_only: bool):
        return self.repo.list_resources(params, sort, category=category, search=search, low_stock_only=low_stock_only)

    def low_stock(self) -> list[Resource]:
        return self.repo.low_stock()
