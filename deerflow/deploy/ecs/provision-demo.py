"""Run with the Gateway virtualenv on ECS; creates only a passwordless demo user."""
import asyncio
import os
from pathlib import Path

for name in ("runtime.env", "model.env"):
    for line in (Path("/etc/deerflow") / name).read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.startswith("#"):
            os.environ[key] = value

from app.gateway.auth.local_provider import LocalAuthProvider
from app.gateway.auth.repositories.sqlite import SQLiteUserRepository
from deerflow.config.app_config import get_app_config
from deerflow.persistence.engine import get_session_factory, init_engine_from_config


async def main():
    await init_engine_from_config(get_app_config().database)
    provider = LocalAuthProvider(SQLiteUserRepository(get_session_factory()))
    user = await provider.get_user_by_email("demo@shihongyuan.cn")
    if user is None:
        user = await provider.create_user("demo@shihongyuan.cn", password=None, system_role="user")
    if user.system_role != "user" or user.password_hash is not None or user.needs_setup:
        raise SystemExit("Existing demo identity is not a safe passwordless user; stopped")
    p = Path("/etc/deerflow/runtime.env")
    lines = [line for line in p.read_text().splitlines() if not line.startswith(("DEER_FLOW_DEMO_USER_ID=", "DEER_FLOW_DEMO_LOGIN_ENABLED="))]
    lines.extend(["DEER_FLOW_DEMO_USER_ID=" + str(user.id), "DEER_FLOW_DEMO_LOGIN_ENABLED=true"])
    p.write_text("\n".join(lines) + "\n")
    p.chmod(0o600)
    print("Passwordless non-admin demo account provisioned; restart Gateway to enable.")


asyncio.run(main())
