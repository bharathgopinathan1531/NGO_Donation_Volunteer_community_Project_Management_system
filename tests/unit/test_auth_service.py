import pytest

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService
from app.utils.enums import Role


def reg(email="new@example.org", role=Role.VOLUNTEER, pw="Passw0rd1"):
    return RegisterRequest(email=email, full_name="New User", password=pw, role=role)


def test_register_hashes_password_and_normalises_email(db):
    user = AuthService(db).register(reg("MiXeD@Example.org"))
    assert user.email == "mixed@example.org"
    assert user.hashed_password != "Passw0rd1" and user.hashed_password.startswith("$2")


def test_register_privileged_role_is_refused(db):
    with pytest.raises(ForbiddenError):
        AuthService(db).register(reg(role=Role.SUPER_ADMIN))


def test_donor_registration_creates_linked_donor_profile(db):
    from app.repositories.donor_repository import DonorRepository

    user = AuthService(db).register(reg("donor@example.org", Role.DONOR))
    assert DonorRepository(db).get_by_user_id(user.id) is not None


def test_duplicate_email_conflicts(db):
    AuthService(db).register(reg())
    with pytest.raises(ConflictError):
        AuthService(db).register(reg())


def test_weak_passwords_are_rejected_by_schema():
    with pytest.raises(ValueError):
        reg(pw="alllowercase")
    with pytest.raises(ValueError):
        reg(pw="short1")


def test_login_success_and_failures(db):
    svc = AuthService(db)
    svc.register(reg())
    tokens = svc.login("new@example.org", "Passw0rd1")
    assert tokens.access_token and tokens.refresh_token
    with pytest.raises(UnauthorizedError):
        svc.login("new@example.org", "wrong-password1")
    with pytest.raises(UnauthorizedError):
        svc.login("nobody@example.org", "Passw0rd1")


def test_deactivated_account_cannot_login(db):
    user = AuthService(db).register(reg())
    user.is_active = False
    db.commit()
    with pytest.raises(ForbiddenError):
        AuthService(db).login("new@example.org", "Passw0rd1")


def test_refresh_token_rotation_makes_old_token_unusable(db):
    svc = AuthService(db)
    svc.register(reg())
    first = svc.login("new@example.org", "Passw0rd1")
    second = svc.refresh(first.refresh_token)
    assert second.refresh_token != first.refresh_token
    with pytest.raises(UnauthorizedError):
        svc.refresh(first.refresh_token)


def test_access_token_cannot_be_used_as_refresh_token(db):
    svc = AuthService(db)
    svc.register(reg())
    tokens = svc.login("new@example.org", "Passw0rd1")
    with pytest.raises(UnauthorizedError):
        svc.refresh(tokens.access_token)


def test_password_reset_token_is_single_use_and_revokes_sessions(db):
    svc = AuthService(db)
    svc.register(reg())
    old = svc.login("new@example.org", "Passw0rd1")
    _, token = svc.forgot_password("new@example.org")
    assert token
    svc.reset_password(token, "BrandNew123")
    assert svc.login("new@example.org", "BrandNew123")
    with pytest.raises(UnauthorizedError):
        svc.reset_password(token, "AnotherOne123")
    with pytest.raises(UnauthorizedError):
        svc.refresh(old.refresh_token)


def test_forgot_password_does_not_reveal_unknown_accounts(db):
    message, token = AuthService(db).forgot_password("ghost@example.org")
    assert token is None and "If an account" in message
