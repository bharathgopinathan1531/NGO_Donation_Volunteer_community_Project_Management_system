from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService
from app.utils.enums import Role
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/users", tags=["Users"])
admin = require_permissions(Permission.USERS_MANAGE)


@router.get("", response_model=Page[UserOut], summary="List users")
def list_users(
    role: Role | None = None, is_active: bool | None = None, search: str | None = Query(None),
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(admin), db: Session = Depends(get_db),
):
    items, total = UserService(db).list_users(params, sort, role=role, is_active=is_active, search=search)
    return build_page([UserOut.model_validate(i) for i in items], total, params)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create a user with any role")
def create_user(payload: UserCreate, actor: User = Depends(admin), db: Session = Depends(get_db)):
    return UserService(db).create(actor, payload)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, _: User = Depends(admin), db: Session = Depends(get_db)):
    return UserService(db).get(user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, actor: User = Depends(admin), db: Session = Depends(get_db)):
    return UserService(db).update(actor, user_id, payload)


@router.post("/{user_id}/activate", response_model=UserOut, summary="Activate an account")
def activate(user_id: int, actor: User = Depends(admin), db: Session = Depends(get_db)):
    return UserService(db).set_active(actor, user_id, True)


@router.post("/{user_id}/deactivate", response_model=UserOut, summary="Deactivate an account (revokes refresh tokens)")
def deactivate(user_id: int, actor: User = Depends(admin), db: Session = Depends(get_db)):
    return UserService(db).set_active(actor, user_id, False)
