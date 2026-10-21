"""Tastewell backend entrypoint (P3). Run: uvicorn app.main:app --port 8000."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes
from app.api.engine import Engine
from app.settings import get_settings


def create_app(engine: Engine | None = None) -> FastAPI:
    settings = get_settings()
    frontend = f"http://localhost:{settings.frontend_port}"
    app = FastAPI(title="Tastewell", version="0.1.0")
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
