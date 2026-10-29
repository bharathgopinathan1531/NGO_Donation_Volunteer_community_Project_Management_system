from tests.conftest import PASSWORD


def test_register_login_me(api, client):
    h = api.signup("new@example.org", "volunteer")
    me = api.get("/auth/me", h, 200).json()
    assert me["email"] == "new@example.org" and me["role"] == "volunteer" and "hashed_password" not in me


def test_privileged_self_registration_forbidden(api):
    r = api.post("/auth/register", None, {"email": "evil@example.org", "full_name": "Evil", "password": "Passw0rd1", "role": "super_admin"})
    assert r.status_code == 403


def test_duplicate_registration_conflicts_and_weak_password_422(api):
    api.signup("dup@example.org")
    assert api.post("/auth/register", None, {"email": "dup@example.org", "full_name": "Dup", "password": "Passw0rd1"}).status_code == 409
    r = api.post("/auth/register", None, {"email": "weak@example.org", "full_name": "Weak", "password": "password"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_wrong_password_and_unknown_user_look_identical(api):
    api.signup("real@example.org")
    a = api.post("/auth/login", None, {"email": "real@example.org", "password": "Wrong1234"})
    b = api.post("/auth/login", None, {"email": "ghost@example.org", "password": "Wrong1234"})
    assert a.status_code == b.status_code == 401 and a.json()["error"]["detail"] == b.json()["error"]["detail"]


def test_protected_endpoints_require_a_valid_token(api, client):
    assert api.get("/auth/me", None).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/api/v1/donors").status_code == 401


def test_refresh_rotation_and_logout(api):
    api.signup("tok@example.org")
    tokens = api.post("/auth/login", None, {"email": "tok@example.org", "password": "Passw0rd1"}, 200).json()
    new = api.post("/auth/refresh", None, {"refresh_token": tokens["refresh_token"]}, 200).json()
    assert api.post("/auth/refresh", None, {"refresh_token": tokens["refresh_token"]}).status_code == 401  # rotated away
    assert api.post("/auth/logout", None, {"refresh_token": new["refresh_token"]}).status_code == 200
    assert api.post("/auth/refresh", None, {"refresh_token": new["refresh_token"]}).status_code == 401


def test_access_token_rejected_where_refresh_expected(api):
    api.signup("mix@example.org")
    tokens = api.post("/auth/login", None, {"email": "mix@example.org", "password": "Passw0rd1"}, 200).json()
    assert api.post("/auth/refresh", None, {"refresh_token": tokens["access_token"]}).status_code == 401
    r = api.c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.status_code == 401  # refresh token is not an access token


def test_password_reset_workflow(api):
    api.signup("reset@example.org")
    r = api.post("/auth/forgot-password", None, {"email": "reset@example.org"}, 200).json()
    token = r["reset_token"]  # exposed only because EXPOSE_RESET_TOKEN=true in tests
    assert api.post("/auth/reset-password", None, {"token": token, "new_password": "Fresh1234"}, 200)
    assert api.post("/auth/reset-password", None, {"token": token, "new_password": "Other1234"}).status_code == 401
    assert api.post("/auth/login", None, {"email": "reset@example.org", "password": "Passw0rd1"}).status_code == 401
    assert api.post("/auth/login", None, {"email": "reset@example.org", "password": "Fresh1234"}).status_code == 200
    unknown = api.post("/auth/forgot-password", None, {"email": "ghost@example.org"}, 200).json()
    assert unknown["reset_token"] is None and unknown["message"] == r["message"]


def test_change_password(api):
    h = api.signup("chg@example.org")
    assert api.post("/auth/change-password", h, {"current_password": "bad", "new_password": "Newer1234"}).status_code == 401
    assert api.post("/auth/change-password", h, {"current_password": "Passw0rd1", "new_password": "Newer1234"}).status_code == 200
    assert api.post("/auth/login", None, {"email": "chg@example.org", "password": "Newer1234"}).status_code == 200


def test_validation_errors_use_the_central_error_format(api):
    r = api.post("/auth/login", None, {"email": "not-an-email"})
    body = r.json()["error"]
    assert r.status_code == 422 and body["code"] == "validation_error" and body["request_id"] and body["errors"]
    assert r.headers["x-request-id"] == body["request_id"]
