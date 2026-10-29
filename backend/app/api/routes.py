"""HTTP layer (P3): run + SSE trace + health/status endpoints (api/routes.py)."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api.engine import Engine, RunRequest
from app.api.decisions import DecisionRequest, PilotOutcome, PilotPlan, ScenarioRequest
from app.agent.decision_review import ReviewRequest
from app.api.stream import sse_line

router = APIRouter(prefix="/api")


class ResolutionChoice(BaseModel):
    candidate_id: str


def get_engine(request: Request) -> Engine:
    return request.app.state.engine


def browser_owner(request: Request, engine: Engine) -> str | None:
    if engine.settings.app_env != "production":
        return None
    if "owner_id" not in request.session:
        request.session["owner_id"] = uuid.uuid4().hex
    return request.session["owner_id"]


def require_decision_owner(request: Request, engine: Engine, decision_id: str) -> str | None:
    owner = browser_owner(request, engine)
    if owner is not None and engine.decision_store.get_owner(decision_id) != owner:
        raise HTTPException(status_code=404, detail="unknown decision_id")
    return owner


@router.post("/decisions")
async def create_decision(payload: DecisionRequest, request: Request,
                          engine: Engine = Depends(get_engine)) -> dict:
    try:
        return (await engine.new_decision(payload, owner_id=browser_owner(request, engine))).model_dump()
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="decision exceeded its total time budget") from exc


@router.post("/decision-jobs", status_code=202)
async def create_decision_job(payload: DecisionRequest, request: Request,
                              engine: Engine = Depends(get_engine)) -> dict:
    return engine.start_decision_job(payload, owner_id=browser_owner(request, engine)).summary()


@router.get("/decision-jobs/{job_id}")
async def get_decision_job(job_id: str, request: Request,
                           engine: Engine = Depends(get_engine)) -> dict:
    job = engine.decision_jobs.get(job_id)
    if job is None or (engine.settings.app_env == "production"
                       and job.owner_id != browser_owner(request, engine)):
        raise HTTPException(status_code=404, detail="unknown job_id")
    return job.summary()


@router.delete("/decision-jobs/{job_id}")
async def cancel_decision_job(job_id: str, request: Request,
                              engine: Engine = Depends(get_engine)) -> dict:
    job = engine.decision_jobs.get(job_id)
    if job is None or (engine.settings.app_env == "production"
                       and job.owner_id != browser_owner(request, engine)):
        raise HTTPException(status_code=404, detail="unknown job_id")
    return engine.cancel_decision_job(job_id).summary()


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str, request: Request,
                       engine: Engine = Depends(get_engine)) -> dict:
    require_decision_owner(request, engine, decision_id)
    result = engine.get_decision(decision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="unknown decision_id")
    return result.model_dump()


@router.get("/decisions/{decision_id}/export")
async def export_decision(decision_id: str, request: Request,
                          engine: Engine = Depends(get_engine)) -> JSONResponse:
    require_decision_owner(request, engine, decision_id)
    result = engine.get_decision(decision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="unknown decision_id")
    return JSONResponse(result.model_dump(), headers={
        "Content-Disposition": f'attachment; filename="tastewell-{decision_id}.json"',
    })


@router.post("/decisions/{decision_id}/replay", status_code=201)
async def replay_decision(decision_id: str, request: Request,
                          engine: Engine = Depends(get_engine)) -> dict:
    owner = require_decision_owner(request, engine, decision_id)
    try:
        return engine.replay_decision(decision_id, owner_id=owner).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown decision_id") from exc


@router.post("/decisions/{decision_id}/resolve")
async def resolve_decision(decision_id: str, payload: ResolutionChoice, request: Request,
                           engine: Engine = Depends(get_engine)) -> dict:
    require_decision_owner(request, engine, decision_id)
    if engine.get_decision(decision_id) is None:
        raise HTTPException(status_code=404, detail="unknown decision_id")
    try:
        result = await engine.resolve_decision(decision_id, payload.candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="decision exceeded its total time budget") from exc
    return result.model_dump()


@router.post("/decisions/{decision_id}/resolve-jobs", status_code=202)
async def resolve_decision_job(decision_id: str, payload: ResolutionChoice, request: Request,
                               engine: Engine = Depends(get_engine)) -> dict:
    owner = require_decision_owner(request, engine, decision_id)
    try:
        return engine.start_resolution_job(decision_id, payload.candidate_id, owner_id=owner).summary()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown decision_id") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/decisions/{decision_id}/scenarios")
async def create_scenario(decision_id: str, payload: ScenarioRequest, request: Request,
                          engine: Engine = Depends(get_engine)) -> dict:
    require_decision_owner(request, engine, decision_id)
    try:
        decision, scenario = await engine.new_scenario(decision_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown decision_id") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="scenario exceeded its total time budget") from exc
    return {"decision": decision.model_dump(), "scenario": scenario.model_dump()}


@router.post("/decisions/{decision_id}/agent-reviews", status_code=202)
async def create_agent_review(decision_id: str, payload: ReviewRequest, request: Request,
                              engine: Engine = Depends(get_engine)) -> dict:
    require_decision_owner(request, engine, decision_id)
    try:
        return engine.start_agent_review(decision_id, payload).summary()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown decision_id") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/decisions/{decision_id}/agent-reviews/{review_id}")
async def get_agent_review(decision_id: str, review_id: str, request: Request,
                           engine: Engine = Depends(get_engine)) -> dict:
    require_decision_owner(request, engine, decision_id)
    job = engine.get_agent_review_job(decision_id, review_id)
    if job:
        return job.summary()
    decision = engine.get_decision(decision_id)
    review = next((item for item in decision.agent_reviews if item.id == review_id), None) if decision else None
    if review:
        return {"review_id": review_id, "status": "done", "stage": "complete",
                "elapsed_seconds": None, "review": review.model_dump(), "error": None}
    raise HTTPException(status_code=404, detail="unknown review_id")


@router.delete("/decisions/{decision_id}/agent-reviews/{review_id}")
async def cancel_agent_review(decision_id: str, review_id: str, request: Request,
                              engine: Engine = Depends(get_engine)) -> dict:
    require_decision_owner(request, engine, decision_id)
    try:
        return engine.cancel_agent_review(decision_id, review_id).summary()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown active review_id") from exc


@router.get("/decisions")
async def list_decisions(request: Request, engine: Engine = Depends(get_engine)) -> list[dict]:
    return engine.decision_store.list_recent(owner_id=browser_owner(request, engine))


@router.post("/decisions/{decision_id}/select/{option_id}")
async def select_decision(decision_id: str, option_id: str, payload: PilotPlan, request: Request,
                          engine: Engine = Depends(get_engine)) -> dict:
    from app.api.decisions import stamp

    require_decision_owner(request, engine, decision_id)
    result = engine.get_decision(decision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="unknown decision_id")
    if not any(option.id == option_id for option in result.options):
        raise HTTPException(status_code=422, detail="option is not in this decision")
    if not payload.venue_id and len(result.venues) == 1:
        payload.venue_id = result.venues[0].id
    if payload.venue_id not in {venue.id for venue in result.venues}:
        raise HTTPException(status_code=422, detail="choose a venue in this decision")
    selected_venue = next(venue for venue in result.venues if venue.id == payload.venue_id)
    if not selected_venue.live_music_allowed:
        raise HTTPException(status_code=422, detail="this venue excludes live music")
    if (selected_venue.budget_limit is not None
            and payload.quoted_total_cost is not None
            and payload.quoted_total_cost > selected_venue.budget_limit):
        raise HTTPException(status_code=422, detail="quoted total cost exceeds this venue's budget ceiling")
    result.selected_option_id = option_id
    result.selected_at = stamp()
    result.pilot_plan = payload
    engine.save_decision(result)
    return result.model_dump()


@router.post("/decisions/{decision_id}/outcome")
async def record_outcome(decision_id: str, payload: PilotOutcome, request: Request,
                         engine: Engine = Depends(get_engine)) -> dict:
    require_decision_owner(request, engine, decision_id)
    result = engine.get_decision(decision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="unknown decision_id")
    if result.selected_option_id is None or result.pilot_plan is None:
        raise HTTPException(status_code=409, detail="select and plan a pilot before recording outcome")
    result.outcome = payload
    engine.save_decision(result)
    return result.model_dump()


@router.post("/agent/run")
async def start_run(
    payload: RunRequest, engine: Engine = Depends(get_engine)
) -> dict:
    if engine.settings.app_env == "production":
        raise HTTPException(status_code=404, detail="unknown endpoint")
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
    if engine.settings.app_env == "production":
        raise HTTPException(status_code=404, detail="unknown endpoint")
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
    if engine.settings.app_env == "production":
        raise HTTPException(status_code=404, detail="unknown endpoint")
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
    result = await asyncio.wait_for(engine.qloo_status(), timeout=55.0)
    return JSONResponse(result)
