from sqlalchemy import insert, select

from app.models.beneficiary import Beneficiary, beneficiary_projects
from app.repositories import BaseRepository
from app.utils.enums import BeneficiaryCategory
from app.utils.filtering import apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class BeneficiaryRepository(BaseRepository[Beneficiary]):
    model = Beneficiary

    def project_ids(self, beneficiary_id: int) -> list[int]:
        rows = self.db.scalars(select(beneficiary_projects.c.project_id).where(beneficiary_projects.c.beneficiary_id == beneficiary_id))
        return sorted(rows.all())

    def is_mapped(self, beneficiary_id: int, project_id: int) -> bool:
        stmt = select(beneficiary_projects.c.project_id).where(
            beneficiary_projects.c.beneficiary_id == beneficiary_id, beneficiary_projects.c.project_id == project_id
        )
        return self.db.scalar(stmt) is not None

    def map_to_project(self, beneficiary_id: int, project_id: int) -> None:
        if not self.is_mapped(beneficiary_id, project_id):
            self.db.execute(insert(beneficiary_projects).values(beneficiary_id=beneficiary_id, project_id=project_id))

    def unmap_from_project(self, beneficiary_id: int, project_id: int) -> None:
        self.db.execute(
            beneficiary_projects.delete().where(
                beneficiary_projects.c.beneficiary_id == beneficiary_id, beneficiary_projects.c.project_id == project_id
            )
        )

    def list_beneficiaries(
        self, params: PaginationParams, sort: SortParams, *, search: str | None = None, category: BeneficiaryCategory | None = None,
        project_id: int | None = None,
    ):
        stmt = apply_equals(select(Beneficiary), Beneficiary, category=category)
        stmt = apply_search(stmt, [Beneficiary.full_name], search)
        if project_id is not None:
            stmt = stmt.where(Beneficiary.id.in_(select(beneficiary_projects.c.beneficiary_id).where(beneficiary_projects.c.project_id == project_id)))
        stmt = apply_sorting(stmt, Beneficiary, sort, {"id", "full_name", "category", "created_at"})
        return paginate(self.db, stmt, params)
