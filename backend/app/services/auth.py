from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, Request, Response, status

from app.core.config import Settings


@dataclass(slots=True)
class AuthenticatedUser:
    username: str


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def authenticate_credentials(self, username: str, password: str) -> AuthenticatedUser:
        if not self.settings.auth_enabled:
            return AuthenticatedUser(username=username)
        if username != self.settings.auth_username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자명 또는 비밀번호가 올바르지 않습니다.")
        if not self._password_matches(password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자명 또는 비밀번호가 올바르지 않습니다.")
        return AuthenticatedUser(username=username)

    def _password_matches(self, password: str) -> bool:
        if self.settings.auth_password_hash:
            try:
                return bcrypt.checkpw(password.encode("utf-8"), self.settings.auth_password_hash.encode("utf-8"))
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="비밀번호 해시 설정이 올바르지 않습니다.") from exc
        if self.settings.auth_password:
            return hmac.compare_digest(password, self.settings.auth_password)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AUTH_PASSWORD 또는 AUTH_PASSWORD_HASH가 설정되지 않았습니다.")

    def create_session_token(self, username: str) -> str:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=self.settings.auth_session_ttl_hours)
        payload = f"{username}|{int(expires_at.timestamp())}"
        signature = hmac.new(
            self.settings.auth_secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
        signature_b64 = base64.urlsafe_b64encode(signature).decode("ascii")
        return f"{payload_b64}.{signature_b64}"

    def parse_session_token(self, token: str) -> AuthenticatedUser | None:
        if not token:
            return None
        try:
            payload_b64, signature_b64 = token.split(".", 1)
            payload = base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8")
            provided_signature = base64.urlsafe_b64decode(signature_b64.encode("ascii"))
        except Exception:
            return None

        expected_signature = hmac.new(
            self.settings.auth_secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            return None

        try:
            username, expires_epoch = payload.split("|", 1)
            expires_at = datetime.fromtimestamp(int(expires_epoch), tz=timezone.utc)
        except Exception:
            return None
        if expires_at < datetime.now(tz=timezone.utc):
            return None
        return AuthenticatedUser(username=username)

    def get_authenticated_user(self, request: Request) -> AuthenticatedUser | None:
        if not self.settings.auth_enabled:
            return AuthenticatedUser(username=self.settings.auth_username)
        token = request.cookies.get(self.settings.auth_cookie_name, "")
        return self.parse_session_token(token)

    def require_authenticated_user(self, request: Request) -> AuthenticatedUser:
        user = self.get_authenticated_user(request)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
        return user

    def is_admin_user(self, user: AuthenticatedUser | None) -> bool:
        if user is None:
            return False
        return hmac.compare_digest(user.username, self.settings.auth_username)

    def require_admin_user(self, request: Request) -> AuthenticatedUser:
        user = self.require_authenticated_user(request)
        if not self.is_admin_user(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
        return user

    def set_session_cookie(self, response: Response, username: str) -> None:
        token = self.create_session_token(username)
        response.set_cookie(
            key=self.settings.auth_cookie_name,
            value=token,
            httponly=True,
            secure=self.settings.environment == "production",
            samesite="lax",
            max_age=self.settings.auth_session_ttl_hours * 3600,
            path="/",
        )

    def clear_session_cookie(self, response: Response) -> None:
        response.delete_cookie(key=self.settings.auth_cookie_name, path="/")
