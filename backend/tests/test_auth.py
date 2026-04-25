from __future__ import annotations

import pytest
import bcrypt
from fastapi import HTTPException

from app.core.config import Settings
from app.services.auth import AuthService


def test_auth_service_accepts_plain_admin_password() -> None:
    service = AuthService(
        Settings(
            auth_enabled=True,
            auth_username="admin",
            auth_password="admin",
            auth_password_hash="",
        )
    )

    user = service.authenticate_credentials("admin", "admin")

    assert user.username == "admin"


def test_auth_service_rejects_wrong_plain_password() -> None:
    service = AuthService(
        Settings(
            auth_enabled=True,
            auth_username="admin",
            auth_password="admin",
            auth_password_hash="",
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        service.authenticate_credentials("admin", "wrong")

    assert exc_info.value.status_code == 401


def test_auth_service_prefers_hash_when_both_password_settings_exist() -> None:
    password_hash = bcrypt.hashpw(b"secure-password", bcrypt.gensalt()).decode("utf-8")
    service = AuthService(
        Settings(
            auth_enabled=True,
            auth_username="admin",
            auth_password="admin",
            auth_password_hash=password_hash,
        )
    )

    user = service.authenticate_credentials("admin", "secure-password")

    assert user.username == "admin"
    with pytest.raises(HTTPException):
        service.authenticate_credentials("admin", "admin")
