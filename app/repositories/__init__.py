from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Thin data-access layer. Repositories never commit - transactions belong to services."""

    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: int, *, for_update: bool = False) -> ModelT | None:
        if for_update:
            return self.db.scalar(select(self.model).where(self.model.id == entity_id).with_for_update())
        return self.db.get(self.model, entity_id)

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()
