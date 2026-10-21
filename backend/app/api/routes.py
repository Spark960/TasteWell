"""HTTP layer (P3): run + SSE trace + health/status endpoints (api/routes.py)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.engine import Engine, RunRequest
from app.api.stream import sse_line

router = APIRouter(prefix="/api")


def get_engine(request: Request) -> Engine:
    return request.app.state.engine


@router.post("/agent/run")
async def start_run(
    payload: RunRequest, engine: Engine = Depends(get_engine)
) -> dict:
    if not payload.brief.strip():
        raise HTTPException(status_code=422, detail="brief must not be empty")
    state = await engine.new_run(payload)
    return {
        "run_id": state.run_id,
        "status": state.status,
        "mode": payload.mode,
        "stream_url": f"/api/agent/stream/{state.run_id}",
    }


@router.get("/agent/stream/{run_id}")
async def stream_run(run_id: str, engine: Engine = Depends(get_engine)):
    state = engine.runs.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="unknown run_id")

    async def gen():
        q = state.bus.subscribe()
        try:
            # Replay buffered events first. There is no await between
            # subscribe and the replay snapshot, so nothing can be missed
            # or duplicated (single event loop).
            done = False
            for ev in list(state.trace.events):
                yield sse_line(ev)
                if ev.get("type") == "run_done":
                    done = True
            if done:
                return
            while True:
                ev = await q.get()
                yield sse_line(ev)
                if ev.get("type") == "run_done":
                    return
        finally:
            state.bus.unsubscribe(q)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/agent/runs/{run_id}")
async def run_summary(run_id: str, engine: Engine = Depends(get_engine)):
    state = engine.runs.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    return state.summary()


@router.get("/health")
async def health(engine: Engine = Depends(get_engine)) -> dict:
    # No Qloo call (plan task 4) — liveness only.
    return {"status": "ok", "app": "tastewell", "app_env": engine.settings.app_env}


@router.get("/qloo/status")
async def qloo_status(engine: Engine = Depends(get_engine)) -> JSONResponse:
    # qloo_capabilities is a readiness check without a data-call, but the
    # MCP spawn itself can hang → cap it (server default 10s is too tight).
    result = await asyncio.wait_for(engine.qloo_status(), timeout=30.0)
    return JSONResponse(result)
