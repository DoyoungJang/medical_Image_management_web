from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.container import AppContainer


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_db(container: AppContainer = Depends(get_container)) -> Iterator[Session]:
    session = container.session_factory()
    try:
        yield session
    finally:
        session.close()
