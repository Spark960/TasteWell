"""Tastewell backend entrypoint (P3). Run: uvicorn app.main:app --port 8000."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import routes
from app.api.engine import Engine
from app.settings import get_settings


def create_app(engine: Engine | None = None) -> FastAPI:
    settings = engine.settings if engine is not None else get_settings()
    frontend = f"http://localhost:{settings.frontend_port}"
    app = FastAPI(title="Tastewell", version="0.1.0")
    if settings.app_env == "production":
        if len(settings.session_secret) < 32:
            raise RuntimeError("SESSION_SECRET must contain at least 32 characters in production")
        app.add_middleware(
            SessionMiddleware, secret_key=settings.session_secret,
            session_cookie="tastewell_session", same_site="lax", https_only=True,
            max_age=60 * 60 * 24 * 30,
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend, f"http://127.0.0.1:{settings.frontend_port}"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes.router)
    app.state.engine = engine or Engine(settings)
    return app


app = create_app()
