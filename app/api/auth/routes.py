from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest, ForgotPasswordRequest, ForgotPasswordResponse, LoginRequest, RefreshRequest, RegisterRequest,
    ResetPasswordRequest, TokenResponse,
)
from app.schemas.common import Message
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Self-register (volunteer or donor)")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse, summary="Login and receive access + refresh tokens")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse, summary="Exchange a refresh token for a new token pair (rotation)")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService(db).refresh(payload.refresh_token)


@router.post("/logout", response_model=Message, summary="Revoke a refresh token")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    AuthService(db).logout(payload.refresh_token)
    return Message(message="Logged out")


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password", response_model=ForgotPasswordResponse, summary="Start the password reset workflow")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    message, token = AuthService(db).forgot_password(payload.email)
    return ForgotPasswordResponse(message=message, reset_token=token)


@router.post("/reset-password", response_model=Message, summary="Complete the password reset with the emailed token")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    AuthService(db).reset_password(payload.token, payload.new_password)
    return Message(message="Password has been reset. Please log in again.")


@router.post("/change-password", response_model=Message, summary="Change own password")
def change_password(payload: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    AuthService(db).change_password(user, payload.current_password, payload.new_password)
    return Message(message="Password changed. Please log in again.")
