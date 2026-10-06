"""Opt-in, passwordless shared demonstration account; never an administrator."""

import os

from app.gateway.auth.models import User


def demo_user_id() -> str:
    return os.getenv("DEER_FLOW_DEMO_USER_ID", "").strip()


def demo_login_enabled() -> bool:
    return os.getenv("DEER_FLOW_DEMO_LOGIN_ENABLED", "").lower() == "true" and bool(demo_user_id())


def valid_demo_user(user: User | None) -> bool:
    return bool(user and str(user.id) == demo_user_id() and user.system_role == "user" and user.password_hash is None and not user.needs_setup)


def demo_request_allowed(user: User, path: str, method: str) -> bool:
    if not demo_user_id() or str(user.id) != demo_user_id():
        return True
    if not demo_login_enabled() or not valid_demo_user(user):
        return False
    # Shared visitors must not claim the account or mint long-lived credentials.
    if path.rstrip("/").startswith("/api/v1/auth"):
        return path.rstrip("/") == "/api/v1/auth/me" and method == "GET"
    return True
