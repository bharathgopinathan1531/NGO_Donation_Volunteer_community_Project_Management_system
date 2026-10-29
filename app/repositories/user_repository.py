from sqlalchemy import select

from app.models.user import User
from app.repositories import BaseRepository
from app.utils.enums import Role
from app.utils.filtering import apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def list_users(self, params: PaginationParams, sort: SortParams, *, role: Role | None, is_active: bool | None, search: str | None):
        stmt = apply_equals(select(User), User, role=role, is_active=is_active)
        stmt = apply_search(stmt, [User.email, User.full_name], search)
        stmt = apply_sorting(stmt, User, sort, {"id", "email", "full_name", "role", "created_at"})
        return paginate(self.db, stmt, params)

    def active_by_roles(self, roles: set[Role]) -> list[User]:
        return list(self.db.scalars(select(User).where(User.role.in_(roles), User.is_active.is_(True))).all())
