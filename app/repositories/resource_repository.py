from sqlalchemy import select

from app.models.resource import Resource
from app.repositories import BaseRepository
from app.utils.enums import ResourceCategory
from app.utils.filtering import apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class ResourceRepository(BaseRepository[Resource]):
    model = Resource

    def get_by_name(self, name: str) -> Resource | None:
        return self.db.scalar(select(Resource).where(Resource.name == name))

    def list_resources(
        self, params: PaginationParams, sort: SortParams, *, category: ResourceCategory | None = None,
        search: str | None = None, low_stock_only: bool = False,
    ):
        stmt = apply_equals(select(Resource), Resource, category=category)
        stmt = apply_search(stmt, [Resource.name, Resource.description], search)
        if low_stock_only:
            stmt = stmt.where(Resource.quantity <= Resource.low_stock_threshold)
        stmt = apply_sorting(stmt, Resource, sort, {"id", "name", "quantity", "category", "created_at"})
        return paginate(self.db, stmt, params)

    def low_stock(self) -> list[Resource]:
        return list(self.db.scalars(select(Resource).where(Resource.quantity <= Resource.low_stock_threshold)).all())
