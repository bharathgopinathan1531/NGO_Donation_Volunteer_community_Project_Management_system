from datetime import date

from sqlalchemy import select

from app.models.stock_transaction import StockTransaction
from app.repositories import BaseRepository
from app.utils.enums import StockTransactionType
from app.utils.filtering import apply_date_range, apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class StockTransactionRepository(BaseRepository[StockTransaction]):
    model = StockTransaction

    def list_transactions(
        self, params: PaginationParams, sort: SortParams, *, resource_id: int | None = None, project_id: int | None = None,
        transaction_type: StockTransactionType | None = None, date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(StockTransaction), StockTransaction, resource_id=resource_id, project_id=project_id, transaction_type=transaction_type)
        stmt = apply_date_range(stmt, StockTransaction.created_at, date_from, date_to)
        stmt = apply_sorting(stmt, StockTransaction, sort, {"id", "created_at", "quantity", "transaction_type"}, default="id", default_order="desc")
        return paginate(self.db, stmt, params)
