from __future__ import annotations

from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from app.api.routes import api_router
from app.container import AppContainer
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    container = AppContainer(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container.initialize()
        container.start_background_services()
        try:
            yield
        finally:
            container.stop_background_services()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.container = container

    @app.get("/", include_in_schema=False)
    def root_info() -> HTMLResponse:
        frontend_url = resolved_settings.cors_origins[0] if resolved_settings.cors_origins else "http://localhost:5173"
        app_name = escape(resolved_settings.app_name)
        safe_frontend_url = escape(frontend_url)
        api_prefix = escape(resolved_settings.api_prefix)
        return HTMLResponse(
            f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{app_name} API</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f5f2ea;
      color: #1f2933;
      font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
    }}
    main {{
      width: min(720px, calc(100vw - 40px));
      padding: 32px;
      border: 1px solid #ded6c7;
      border-radius: 24px;
      background: #fffaf0;
      box-shadow: 0 20px 60px rgba(55, 45, 25, 0.12);
    }}
    h1 {{ margin: 0 0 12px; font-size: 28px; }}
    p {{ line-height: 1.7; }}
    a {{ color: #0f766e; font-weight: 700; }}
    code {{
      padding: 2px 6px;
      border-radius: 8px;
      background: #ebe4d5;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{app_name} 백엔드가 실행 중입니다.</h1>
    <p>이 포트는 API 서버입니다. 실제 웹 화면은 프런트엔드 개발 서버 또는 Nginx가 제공하는 주소에서 열어주세요.</p>
    <p>개발 환경 프런트엔드: <a href="{safe_frontend_url}">{safe_frontend_url}</a></p>
    <p>API 상태 확인: <a href="{api_prefix}/health"><code>{api_prefix}/health</code></a></p>
    <p>API 문서: <a href="/docs"><code>/docs</code></a></p>
  </main>
</body>
</html>"""
        )

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
