import os

# Must be set before the app (and its settings object) is imported.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-test-secret-key"
os.environ["EXPOSE_RESET_TOKEN"] = "true"
os.environ["DEBUG"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.enums import Role  # noqa: E402

PASSWORD = "Passw0rd!"


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from sqlalchemy import event

    @event.listens_for(eng, "connect")
    def _fk(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = session_factory
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(session_factory):
    def _make(role: Role, email: str | None = None, name: str | None = None, active: bool = True) -> User:
        with session_factory() as s:
            user = User(
                email=(email or f"{role.value}@ngo-demo.org").lower(), full_name=name or role.value.replace("_", " ").title(),
                hashed_password=hash_password(PASSWORD), role=role, is_active=active,
            )
            s.add(user)
            s.commit()
            s.refresh(user)
            return user

    return _make


@pytest.fixture()
def login(client):
    def _login(email: str, password: str = PASSWORD) -> dict:
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login


@pytest.fixture()
def auth(make_user, login):
    """auth(Role.FINANCE_OFFICER) -> headers (creates the user on first use)."""
    cache: dict[Role, dict] = {}

    def _auth(role: Role) -> dict:
        if role not in cache:
            user = make_user(role)
            cache[role] = login(user.email)
        return cache[role]

    return _auth


@pytest.fixture()
def admin(auth):
    return auth(Role.SUPER_ADMIN)


@pytest.fixture()
def api(client):
    from tests.helpers import Api

    return Api(client)
