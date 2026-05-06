from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import AppSetting, User


@dataclass(slots=True)
class AuthenticatedUser:
    username: str
    is_admin: bool = False


class AuthService:
    SIGNUP_CODE_KEY = "signup_code"

    def __init__(self, settings: Settings, session_factory: sessionmaker[Session] | None = None) -> None:
        self.settings = settings
        self.session_factory = session_factory

    def authenticate_credentials(self, username: str, password: str) -> AuthenticatedUser:
        username = username.strip()
        if not self.settings.auth_enabled:
            return AuthenticatedUser(username=username, is_admin=self._is_admin_username(username))

        db_user = self._authenticate_database_user(username, password)
        if db_user is not None:
            return db_user

        if not self._is_admin_username(username):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
        if not self._password_matches(password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
        return AuthenticatedUser(username=username, is_admin=True)

    def register_user(self, username: str, password: str, signup_code: str) -> AuthenticatedUser:
        username = username.strip()
        signup_code = signup_code.strip()
        if not self.settings.auth_enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authentication is disabled.")
        if not username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required.")
        if self._is_admin_username(username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This username is reserved.")

        effective_code = self.get_signup_code_value()
        if not effective_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signup code is not configured.")
        if not hmac.compare_digest(signup_code, effective_code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Signup code is incorrect.")
        if self.session_factory is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User database is unavailable.")

        now = datetime.now(tz=timezone.utc)
        with self.session_factory() as session:
            session.add(
                User(
                    username=username,
                    password_hash=self.hash_password(password),
                    is_admin=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.") from exc

        return AuthenticatedUser(username=username, is_admin=False)

    def change_password(self, username: str, current_password: str, new_password: str) -> AuthenticatedUser:
        username = username.strip()
        if not self.settings.auth_enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authentication is disabled.")
        if self.session_factory is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User database is unavailable.")

        now = datetime.now(tz=timezone.utc)
        with self.session_factory() as session:
            user = self._get_user(session, username)
            if user is not None:
                if not self._hash_matches(current_password, user.password_hash):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")
                user.password_hash = self.hash_password(new_password)
                user.updated_at = now
                session.commit()
                return AuthenticatedUser(username=user.username, is_admin=user.is_admin)

            if self._is_admin_username(username):
                if not self._password_matches(current_password):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")
                session.add(
                    User(
                        username=username,
                        password_hash=self.hash_password(new_password),
                        is_admin=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
                session.commit()
                return AuthenticatedUser(username=username, is_admin=True)

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account was not found.")

    def get_signup_code_config(self) -> tuple[str, str]:
        if self.session_factory is None:
            return self.settings.signup_code, "environment"
        with self.session_factory() as session:
            value = self._get_setting(session, self.SIGNUP_CODE_KEY)
        if value is not None:
            return value, "database"
        return self.settings.signup_code, "environment"

    def get_signup_code_value(self) -> str:
        code, _source = self.get_signup_code_config()
        return code.strip()

    def set_signup_code(self, signup_code: str) -> tuple[str, str]:
        if self.session_factory is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Settings database is unavailable.")
        with self.session_factory() as session:
            self._set_setting(session, self.SIGNUP_CODE_KEY, signup_code.strip())
            session.commit()
        return signup_code.strip(), "database"

    def _password_matches(self, password: str) -> bool:
        if self.settings.auth_password_hash:
            return self._hash_matches(password, self.settings.auth_password_hash)
        if self.settings.auth_password:
            return hmac.compare_digest(password, self.settings.auth_password)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_PASSWORD or AUTH_PASSWORD_HASH is not configured.",
        )

    def _hash_matches(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password hash is invalid.") from exc

    def _authenticate_database_user(self, username: str, password: str) -> AuthenticatedUser | None:
        if self.session_factory is None:
            return None
        with self.session_factory() as session:
            user = self._get_user(session, username)
            if user is None:
                return None
            if not self._hash_matches(password, user.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
            return AuthenticatedUser(username=user.username, is_admin=user.is_admin)

    def _get_user(self, session: Session, username: str) -> User | None:
        return session.execute(select(User).where(User.username == username)).scalar_one_or_none()

    def _get_setting(self, session: Session, key: str) -> str | None:
        setting = session.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
        if setting is None:
            return None
        return setting.value_text

    def _set_setting(self, session: Session, key: str, value: str) -> None:
        now = datetime.now(tz=timezone.utc)
        setting = session.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
        if setting is None:
            session.add(AppSetting(key=key, value_text=value, updated_at=now))
            return
        setting.value_text = value
        setting.updated_at = now

    def _is_admin_username(self, username: str) -> bool:
        return hmac.compare_digest(username.encode("utf-8"), self.settings.auth_username.encode("utf-8"))

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

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
        return AuthenticatedUser(username=username, is_admin=self._is_admin_username(username))

    def get_authenticated_user(self, request: Request) -> AuthenticatedUser | None:
        if not self.settings.auth_enabled:
            return AuthenticatedUser(username=self.settings.auth_username, is_admin=True)
        token = request.cookies.get(self.settings.auth_cookie_name, "")
        return self.parse_session_token(token)

    def require_authenticated_user(self, request: Request) -> AuthenticatedUser:
        user = self.get_authenticated_user(request)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login is required.")
        return user

    def is_admin_user(self, user: AuthenticatedUser | None) -> bool:
        if user is None:
            return False
        return user.is_admin or self._is_admin_username(user.username)

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
