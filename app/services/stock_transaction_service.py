from datetime import date

from sqlalchemy.orm import Session

from app.repositories.stock_transaction_repository import StockTransactionRepository
from app.utils.enums import StockTransactionType
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams


class StockTransactionService:
    """Read-only access to the immutable stock ledger (writes happen in ResourceService.apply_movement)."""

    def __init__(self, db: Session):
        self.repo = StockTransactionRepository(db)

    def list_transactions(
        self, params: PaginationParams, sort: SortParams, *, resource_id: int | None, project_id: int | None,
        transaction_type: StockTransactionType | None, date_from: date | None, date_to: date | None,
    ):
        return self.repo.list_transactions(
            params, sort, resource_id=resource_id, project_id=project_id, transaction_type=transaction_type,
            date_from=date_from, date_to=date_to,
        )
