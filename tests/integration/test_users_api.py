from app.utils.enums import Role


def test_only_super_admin_manages_users(api, auth):
    for role in (Role.NGO_MANAGER, Role.FINANCE_OFFICER, Role.VOLUNTEER_COORDINATOR, Role.VOLUNTEER, Role.DONOR):
        assert api.get("/users", auth(role)).status_code == 403, role
        assert api.post("/users", auth(role), {"email": "x@example.org", "full_name": "X Y", "password": "Passw0rd1", "role": "donor"}).status_code == 403


def test_admin_creates_staff_accounts_and_lists_with_filters(api, admin):
    r = api.post("/users", admin, {"email": "fin@example.org", "full_name": "Fin Officer", "password": "Passw0rd1", "role": "finance_officer"}, 201).json()
    assert r["role"] == "finance_officer" and r["is_active"]
    api.post("/users", admin, {"email": "vol@example.org", "full_name": "Vol", "password": "Passw0rd1", "role": "volunteer"}, 201)
    page = api.get("/users", admin, 200, role="finance_officer").json()
    assert page["total"] == 1 and page["items"][0]["email"] == "fin@example.org"
    assert api.get("/users", admin, 200, search="vol").json()["total"] == 1
    assert api.post("/users", admin, {"email": "fin@example.org", "full_name": "Dup", "password": "Passw0rd1", "role": "donor"}).status_code == 409


def test_deactivation_blocks_login_and_existing_tokens(api, admin, make_user, login):
    user = make_user(Role.NGO_MANAGER, "mgr@example.org")
    h = login(user.email)
    assert api.get("/auth/me", h).status_code == 200
    api.post(f"/users/{user.id}/deactivate", admin, expect=200)
    assert api.get("/auth/me", h).status_code == 403  # existing access token no longer works
    assert api.post("/auth/login", None, {"email": user.email, "password": "Passw0rd!"}).status_code == 403
    api.post(f"/users/{user.id}/activate", admin, expect=200)
    assert api.get("/auth/me", h).status_code == 200
    assert api.post(f"/users/{user.id}/activate", admin).status_code == 422  # already active


def test_deactivation_revokes_refresh_tokens(api, admin, make_user):
    user = make_user(Role.NGO_MANAGER, "mgr2@example.org")
    tokens = api.post("/auth/login", None, {"email": user.email, "password": "Passw0rd!"}, 200).json()
    api.post(f"/users/{user.id}/deactivate", admin, expect=200)
    api.post(f"/users/{user.id}/activate", admin, expect=200)
    assert api.post("/auth/refresh", None, {"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_admin_cannot_lock_themselves_out(api, make_user, login):
    only = make_user(Role.SUPER_ADMIN, "root@example.org")
    h = login(only.email)
    assert api.post(f"/users/{only.id}/deactivate", h).status_code == 422
    assert api.patch(f"/users/{only.id}", h, {"role": "donor"}).status_code == 422


def test_last_super_admin_is_protected(api, make_user, login):
    a, b = make_user(Role.SUPER_ADMIN, "a@example.org"), make_user(Role.SUPER_ADMIN, "b@example.org")
    ha = login(a.email)
    api.post(f"/users/{b.id}/deactivate", ha, expect=200)
    hb_target = make_user(Role.SUPER_ADMIN, "c@example.org")
    api.post(f"/users/{hb_target.id}/deactivate", ha, expect=200)
    # only `a` is left active; a second admin trying to demote it is impossible, and a cannot demote itself
    assert api.patch(f"/users/{a.id}", ha, {"role": "ngo_manager"}).status_code == 422


def test_update_role_and_name(api, admin, make_user):
    u = make_user(Role.VOLUNTEER, "up@example.org")
    r = api.patch(f"/users/{u.id}", admin, {"full_name": "Renamed User", "role": "volunteer_coordinator"}, 200).json()
    assert r["full_name"] == "Renamed User" and r["role"] == "volunteer_coordinator"
    assert api.get("/users/9999", admin).status_code == 404
