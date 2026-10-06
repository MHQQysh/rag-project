from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.auth.models import User
from app.gateway.csrf_middleware import CSRFMiddleware
from app.gateway.routers import auth


@pytest.fixture
def demo_client(monkeypatch):
    user = User(email="demo@example.com")
    provider = AsyncMock()
    provider.get_user.return_value = user
    monkeypatch.setattr(auth, "get_local_provider", lambda: provider)
    monkeypatch.setenv("DEER_FLOW_DEMO_USER_ID", str(user.id))
    monkeypatch.setenv("DEER_FLOW_DEMO_LOGIN_ENABLED", "true")
    app = FastAPI()
    app.include_router(auth.router)
    app.add_middleware(CSRFMiddleware)
    with TestClient(app, base_url="https://testserver") as client:
        yield client, user, provider


def test_demo_creates_secure_session_without_password(demo_client):
    client, user, _ = demo_client
    assert client.get("/api/v1/auth/demo-status").json() == {"enabled": True}
    response = client.post("/api/v1/auth/login/demo", headers={"Origin": "https://testserver"})
    assert response.status_code == 200
    assert response.json()["needs_setup"] is False
    assert "access_token" in client.cookies
    assert "csrf_token" in client.cookies
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    assert str(user.id) not in response.text


@pytest.mark.parametrize("state", ["disabled", "missing", "admin", "password", "setup"])
def test_demo_fails_closed(demo_client, monkeypatch, state):
    client, user, provider = demo_client
    if state == "disabled":
        monkeypatch.setenv("DEER_FLOW_DEMO_LOGIN_ENABLED", "false")
    if state == "missing":
        provider.get_user.return_value = None
    if state == "admin":
        user.system_role = "admin"
    if state == "password":
        user.password_hash = "hash"
    if state == "setup":
        user.needs_setup = True
    assert client.get("/api/v1/auth/demo-status").json() == {"enabled": False}
    response = client.post("/api/v1/auth/login/demo")
    assert response.status_code == 404
    assert "access_token" not in client.cookies


def test_demo_rejects_cross_site_login(demo_client):
    client, _, _ = demo_client
    assert client.post("/api/v1/auth/login/demo", headers={"Origin": "https://evil.example"}).status_code == 403
    assert "access_token" not in client.cookies


def test_demo_session_policy(monkeypatch):
    from app.gateway.auth.demo import demo_request_allowed

    user = User(email="demo@example.com")
    monkeypatch.setenv("DEER_FLOW_DEMO_USER_ID", str(user.id))
    monkeypatch.setenv("DEER_FLOW_DEMO_LOGIN_ENABLED", "true")
    assert demo_request_allowed(user, "/api/threads", "POST")
    assert demo_request_allowed(user, "/api/v1/auth/me", "GET")
    assert not demo_request_allowed(user, "/api/v1/auth/change-password", "POST")
    assert not demo_request_allowed(user, "/api/v1/auth/tokens", "POST")
    assert demo_request_allowed(User(email="admin@example.com", system_role="admin"), "/api/v1/auth/change-password", "POST")
    monkeypatch.setenv("DEER_FLOW_DEMO_LOGIN_ENABLED", "false")
    assert not demo_request_allowed(user, "/api/threads", "POST")


def test_demo_middleware_blocks_account_mutation(monkeypatch):
    from app.gateway.auth_middleware import AuthMiddleware
    from deerflow.config.authorization_config import AuthorizationConfig

    user = User(email="demo@example.com")
    monkeypatch.setenv("DEER_FLOW_DEMO_USER_ID", str(user.id))
    monkeypatch.setenv("DEER_FLOW_DEMO_LOGIN_ENABLED", "true")
    monkeypatch.setattr("app.gateway.deps.get_current_user_from_request", AsyncMock(return_value=user))
    monkeypatch.setattr("app.gateway.authz._get_route_authorization_config", lambda: AuthorizationConfig())
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.post("/api/v1/auth/change-password")
    async def change_password():
        return {"changed": True}

    @app.get("/api/v1/auth/me")
    async def me():
        return {"role": user.system_role}

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-session")
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.post("/api/v1/auth/change-password").status_code == 403
        monkeypatch.setenv("DEER_FLOW_DEMO_LOGIN_ENABLED", "false")
        assert client.get("/api/v1/auth/me").status_code == 403
        monkeypatch.setenv("DEER_FLOW_DEMO_USER_ID", "different-user")
        assert client.post("/api/v1/auth/change-password").status_code == 200
