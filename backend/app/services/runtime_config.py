from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import AppSetting


@dataclass(frozen=True, slots=True)
class ImageRootConfig:
    root_dir: str
    env_root_dir: str
    source: str


class RuntimeConfigService:
    IMAGE_ROOT_DIR_KEY = "png_root_dir"

    def __init__(self, session_factory: sessionmaker[Session], *, env_root_dir: str) -> None:
        self.session_factory = session_factory
        self.env_root_dir = env_root_dir

    def get_image_root_config(self) -> ImageRootConfig:
        with self.session_factory() as session:
            value = self._get_value(session, self.IMAGE_ROOT_DIR_KEY)
        if value:
            return ImageRootConfig(root_dir=value, env_root_dir=self.env_root_dir, source="database")
        return ImageRootConfig(root_dir=self.env_root_dir, env_root_dir=self.env_root_dir, source="environment")

    def set_image_root_dir(self, root_dir: str) -> ImageRootConfig:
        with self.session_factory() as session:
            self._set_value(session, self.IMAGE_ROOT_DIR_KEY, root_dir)
            session.commit()
        return ImageRootConfig(root_dir=root_dir, env_root_dir=self.env_root_dir, source="database")

    def _get_value(self, session: Session, key: str) -> str | None:
        setting = session.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
        if setting is None:
            return None
        value = setting.value_text.strip()
        return value or None

    def _set_value(self, session: Session, key: str, value: str) -> None:
        now = datetime.now(tz=timezone.utc)
        setting = session.execute(select(AppSetting).where(AppSetting.key == key)).scalar_one_or_none()
        if setting is None:
            session.add(AppSetting(key=key, value_text=value, updated_at=now))
            return
        setting.value_text = value
        setting.updated_at = now
