"""A narrow, deterministic programming decision built from Qloo evidence.

This path deliberately does not ask a model to invent entities or scores.
Qloo order is preserved only inside each recommendation call.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from app.qloo.normalizer import NormalizedResult


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class VenueInput(BaseModel):
    id: str = Field(default_factory=lambda: f"venue_{uuid.uuid4().hex[:10]}")
    name: str = Field(min_length=1, max_length=120)
    region: str = Field(min_length=1, max_length=160)
    live_music_allowed: bool = True
    budget_limit: int | None = Field(default=None, ge=0)


class DecisionRequest(BaseModel):
    venue_name: str = Field(min_length=1, max_length=120)
    concept: str = Field(min_length=1, max_length=120)
    region: str = Field(min_length=1, max_length=160)
    audience: str = Field(min_length=1, max_length=100)
    objective: str = Field(default="Choose a programming pilot", max_length=300)
    budget_limit: int | None = Field(default=None, ge=0)
    live_music_allowed: bool = True
    selected_tag_id: str | None = None
    venues: list[VenueInput] = Field(default_factory=list, max_length=10)
    artist_shortlist: list[str] = Field(default_factory=list, max_length=5)
    artist_resolution: dict[str, str] = Field(default_factory=dict)


class EvidenceRow(BaseModel):
    id: str
    operation: str
    status: str
    query: dict[str, Any]
    correlation_id: str | None
    retrieved_at: str
    source_id: str | None = None
    name: str | None = None
    subtype: str | None = None
    affinity: float | None = None
    summary: str | None = None
    venue_id: str | None = None


class DecisionOption(BaseModel):
    id: str
    format: str
    title: str
    description: str
    evidence_ids: list[str]
    unknowns: list[str]
    constraint_notes: list[str]
    artist_rank: int | None = None
    venue_ranks: dict[str, int | None] = Field(default_factory=dict)


class PilotPlan(BaseModel):
    venue_id: str = ""
    owner: str = Field(min_length=1, max_length=120)
    target_date: str = Field(min_length=1, max_length=80)
    success_measure: str = Field(min_length=1, max_length=300)
    baseline: str = Field(default="Not yet recorded", max_length=300)
    cost_assumption: str = Field(default="Unknown until quoted", max_length=300)
    quoted_total_cost: int | None = Field(default=None, ge=0)
    next_action: str = Field(min_length=1, max_length=300)


class PilotOutcome(BaseModel):
    metric: str = Field(min_length=1, max_length=120)
    baseline_value: float
    actual_value: float
    unit: str = Field(min_length=1, max_length=60)
    period: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=1000)
    recorded_at: str = Field(default_factory=stamp)


class ScenarioRequest(BaseModel):
    venue_id: str
    audience: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=160)


class ScenarioResult(BaseModel):
    id: str = Field(default_factory=lambda: f"scenario_{uuid.uuid4().hex[:10]}")
    created_at: str = Field(default_factory=stamp)
    venue_id: str
    status: Literal["ready", "no_evidence"]
    original_query: dict[str, Any]
    changed_query: dict[str, Any]
    artist_ids: list[str]
    artist_names: dict[str, str]
    baseline_ranks: dict[str, int | None]
    scenario_ranks: dict[str, int | None]
    evidence_ids: list[str]
    note: str


class DecisionResult(BaseModel):
    id: str
    source_mode: Literal["live", "replay"] = "live"
    replay_of: str | None = None
    created_at: str = Field(default_factory=stamp)
    updated_at: str = Field(default_factory=stamp)
    status: Literal["ready", "needs_input", "no_evidence", "blocked"]
    request: DecisionRequest
    venues: list[VenueInput] = Field(default_factory=list)
    options: list[DecisionOption] = Field(default_factory=list)
    evidence: list[EvidenceRow] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    resolution_kind: Literal["tag", "artist"] | None = None
    resolution_key: str | None = None
    notes: list[str] = Field(default_factory=list)
    selected_option_id: str | None = None
    selected_at: str | None = None
    pilot_plan: PilotPlan | None = None
    outcome: PilotOutcome | None = None
    scenarios: list[ScenarioResult] = Field(default_factory=list)


def ledger_rows(operation: str, query: dict, result: NormalizedResult,
                venue_id: str | None = None) -> list[EvidenceRow]:
    common = dict(operation=operation, status=result.status, query=query,
                  correlation_id=result.correlation_id, retrieved_at=result.retrieved_at,
                  summary=result.summary, venue_id=venue_id)
    rows = []
    source_rows = result.results or (result.candidates if result.status == "needs_input" else [])
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        source_id = row.get("entity_id") or row.get("id")
        if not isinstance(source_id, str):
            continue
        affinity = row.get("affinity")
        rows.append(EvidenceRow(
            id=f"ev_{uuid.uuid4().hex[:12]}", source_id=source_id,
            name=row.get("name") if isinstance(row.get("name"), str) else None,
            subtype=row.get("subtype") if isinstance(row.get("subtype"), str) else None,
            affinity=float(affinity) if isinstance(affinity, (int, float)) else None,
            **common,
        ))
    if not rows:
        rows.append(EvidenceRow(id=f"ev_{uuid.uuid4().hex[:12]}", **common))
    return rows


def _usable(result: NormalizedResult) -> bool:
    return result.status == "ok" and bool(result.results)


async def build_decision(req: DecisionRequest, client: Any,
                         progress: Callable[[str], None] | None = None) -> DecisionResult:
    def stage(value: str) -> None:
        if progress is not None:
            progress(value)

    stage("checking venue constraints")
    venues = req.venues or [VenueInput(
        name=req.venue_name, region=req.region,
        live_music_allowed=req.live_music_allowed, budget_limit=req.budget_limit,
    )]
    decision = DecisionResult(id=f"dec_{uuid.uuid4().hex[:12]}", status="no_evidence",
                              request=req, venues=venues)
    eligible_venues = [venue for venue in venues if venue.live_music_allowed]
    if not eligible_venues:
        decision.status = "blocked"
        decision.notes.append("This programming slice requires at least one venue that permits live music. No Qloo call was made.")
        return decision
    primary = eligible_venues[0]

    stage("resolving the venue concept")
    tag_query = {"query": req.concept, "semantic": True, "limit": 10}
    tags = await asyncio.wait_for(client.call_tool("find_tags", tag_query), timeout=45)
    decision.evidence.extend(ledger_rows("find_tags", tag_query, tags))
    if tags.status not in ("ok", "needs_input"):
        decision.notes.append(f"Concept resolution returned {tags.status}; no cultural fit claim is available.")
        return decision

    tag_candidates = tags.results or (tags.candidates if tags.status == "needs_input" else [])
    valid_tags = [r for r in tag_candidates if isinstance(r, dict) and isinstance(r.get("id"), str)]
    if not valid_tags:
        decision.notes.append("Concept resolution returned no selectable tag IDs.")
        return decision
    if req.selected_tag_id:
        selected = next((r for r in valid_tags if r["id"] == req.selected_tag_id), None)
        if selected is None:
            decision.status = "needs_input"
            decision.resolution_kind = "tag"
            decision.notes.append("The selected tag is not in this run's Qloo results. Choose a listed tag.")
            decision.candidates = [{k: r.get(k) for k in ("id", "name", "type", "popularity")} for r in valid_tags]
            return decision
    elif len(valid_tags) == 1 and tags.status == "ok":
        selected = valid_tags[0]
    else:
        decision.status = "needs_input"
        decision.resolution_kind = "tag"
        decision.notes.append("Choose the Qloo tag that represents this venue concept.")
        decision.candidates = [{k: r.get(k) for k in ("id", "name", "type", "popularity")} for r in valid_tags]
        return decision

    tag_id = selected["id"]
    tag_evidence = next(e.id for e in decision.evidence if e.source_id == tag_id)
    base = {"signal_tags": [tag_id], "signal_location": primary.region,
            "demographic": req.audience, "limit": 5}
    artist_query = {"target_type": "artist", **base}
    brand_query = {"target_type": "brand", **base}
    artist_rows: list[EvidenceRow] = []
    if req.artist_shortlist:
        names = [name.strip() for name in req.artist_shortlist]
        if any(not name for name in names) or len(set(n.casefold() for n in names)) != len(names):
            decision.notes.append("Artist shortlist needs distinct, nonempty names.")
            return decision
        for index, name in enumerate(names, 1):
            stage(f"resolving artist {index} of {len(names)}")
            query = {"entity": name, "type": "artist"}
            described = await asyncio.wait_for(client.call_tool("describe", query), timeout=45)
            rows = ledger_rows("describe", query, described)
            decision.evidence.extend(rows)
            raw_choices = described.results or described.candidates
            choices = [
                {"id": row.get("entity_id") or row.get("id"),
                 "name": row.get("name"), "type": row.get("type")}
                for row in raw_choices if isinstance(row, dict)
                and isinstance(row.get("entity_id") or row.get("id"), str)
            ]
            chosen_id = req.artist_resolution.get(name)
            exact = (described.status == "ok" and len(choices) == 1
                     and isinstance(choices[0]["name"], str)
                     and choices[0]["name"].casefold() == name.casefold())
            if described.status not in ("ok", "needs_input") or not choices:
                decision.notes.append(f"Artist {name!r} could not be resolved ({described.status}).")
                return decision
            if chosen_id not in {choice["id"] for choice in choices}:
                chosen_id = None
            if not chosen_id and not exact:
                decision.status = "needs_input"
                decision.resolution_kind = "artist"
                decision.resolution_key = name
                decision.candidates = choices
                decision.notes.append(f"Choose the intended Qloo artist for {name!r}.")
                return decision
            entity_id = chosen_id or choices[0]["id"]
            resolved_row = next((row for row in rows if row.source_id == entity_id), None)
            if resolved_row is None or described.status == "needs_input":
                id_query = {"entity": entity_id, "type": "artist"}
                verified = await asyncio.wait_for(client.call_tool("describe", id_query), timeout=45)
                verified_rows = ledger_rows("describe", id_query, verified)
                decision.evidence.extend(verified_rows)
                resolved_row = next((row for row in verified_rows
                                     if row.source_id == entity_id and verified.status == "ok"), None)
            if resolved_row is None:
                decision.notes.append(f"Selected artist ID for {name!r} could not be verified.")
                return decision
            artist_rows.append(resolved_row)
        if len({row.source_id for row in artist_rows}) != len(artist_rows):
            decision.notes.append("Two shortlist names resolved to the same artist ID; choose distinct acts.")
            return decision
        decision.notes.append("Artist candidates came from the operator shortlist and were resolved with Qloo describe.")
    else:
        stage("discovering artists")
        artists = await asyncio.wait_for(client.call_tool("recommend", artist_query), timeout=45)
        decision.evidence.extend(ledger_rows("recommend", artist_query, artists, primary.id))
        if not _usable(artists):
            decision.notes.append(f"Artist discovery returned {artists.status}; no programming option was constructed.")
            return decision
        artist_rows = [e for e in decision.evidence if e.operation == "recommend"
                       and e.query == artist_query and e.source_id][:3]

    stage("checking optional brand partners")
    brands = await asyncio.wait_for(client.call_tool("recommend", brand_query), timeout=45)
    decision.evidence.extend(ledger_rows("recommend", brand_query, brands, primary.id))
    if brands.status != "ok":
        decision.notes.append(f"Brand discovery returned {brands.status}; a brand partner is optional.")
    brand_rows = [e for e in decision.evidence if e.operation == "recommend" and e.query == brand_query and e.source_id]
    shortlist = artist_rows[:5]
    ranks_by_venue: dict[str, dict[str, tuple[int, str]]] = {}
    if len(shortlist) >= 2:
        for venue in eligible_venues:
            stage(f"ranking artists for {venue.name}")
            rank_query = {
                "options": [row.source_id for row in shortlist],
                "option_type": "artist",
                "signal_location": venue.region,
                "demographic": req.audience,
            }
            ranked = await asyncio.wait_for(client.call_tool("rank", rank_query), timeout=45)
            rank_rows = ledger_rows("rank", rank_query, ranked, venue.id)
            decision.evidence.extend(rank_rows)
            returned_ids = {row.source_id for row in rank_rows if row.source_id}
            expected_ids = {row.source_id for row in shortlist}
            if ranked.status == "ok" and returned_ids == expected_ids:
                ranks_by_venue[venue.id] = {
                    row.source_id: (index, row.id)
                    for index, row in enumerate(rank_rows, 1) if row.source_id
                }
            else:
                decision.notes.append(
                    f"Rank for {venue.name} returned {ranked.status} with "
                    f"{len(returned_ids)} of {len(expected_ids)} artist IDs; "
                    "no rank is displayed for this venue."
                )
    stage("building pilot options")
    formats = [
        ("early_set", "Early live set", "Pilot an early set with {artist} at {venue}."),
        ("hosted_session", "Hosted listening session", "Pilot a hosted listening session featuring {artist} at {venue}."),
        ("partner_showcase", "Partner showcase", "Pilot a showcase featuring {artist} at {venue}."),
    ]
    visible_shortlist = shortlist
    if req.artist_shortlist and ranks_by_venue.get(primary.id):
        visible_shortlist = sorted(
            shortlist,
            key=lambda row: ranks_by_venue[primary.id][row.source_id][0],
        )
    for i, artist in enumerate(visible_shortlist[:3]):
        key, title, template = formats[i]
        evidence_ids = [tag_evidence, artist.id]
        venue_ranks = {venue.id: ranks_by_venue.get(venue.id, {}).get(artist.source_id)
                       for venue in venues}
        evidence_ids.extend(rank[1] for rank in venue_ranks.values() if rank)
        description = template.format(
            artist=artist.name or "the resolved artist",
            venue=primary.name if len(venues) == 1 else "one of the listed venues",
        )
        unknowns = ["Artist availability and fee", "Staffing and licensing", "Expected attendance and revenue"]
        if key == "partner_showcase" and brand_rows:
            brand = brand_rows[0]
            description += f" Explore {brand.name or 'the resolved brand'} as a potential partner."
            evidence_ids.append(brand.id)
            unknowns.append("Brand willingness to partner")
        decision.options.append(DecisionOption(
            id=f"opt_{uuid.uuid4().hex[:10]}", format=key, title=title,
            description=description, evidence_ids=evidence_ids,
            unknowns=unknowns,
            constraint_notes=["Live music permitted by operator input.",
                              "Budget feasibility is unverified until fees and production costs are supplied."],
            artist_rank=venue_ranks[primary.id][0] if venue_ranks[primary.id] else None,
            venue_ranks={venue_id: value[0] if value else None
                         for venue_id, value in venue_ranks.items()},
        ))
    decision.status = "ready"
    decision.notes.append("Each venue's artist rank comes from a separate Qloo call over the same shortlist. Rank positions can be inspected within a venue; affinities from different calls are not a shared score. Formats, costs, and feasibility are not ranked by Qloo.")
    for venue in venues:
        if not venue.live_music_allowed:
            decision.notes.append(f"{venue.name}: live music is excluded by operator input.")
        if venue.budget_limit is not None:
            decision.notes.append(f"{venue.name}: operator budget ceiling {venue.budget_limit}; costs are unknown, so affordability is unverified.")
    return decision


async def compare_scenario(decision: DecisionResult, request: ScenarioRequest,
                           client: Any) -> ScenarioResult:
    if decision.status != "ready":
        raise ValueError("finish the decision before comparing a scenario")
    venue = next((venue for venue in decision.venues if venue.id == request.venue_id), None)
    if venue is None or not venue.live_music_allowed:
        raise ValueError("choose an eligible venue in this decision")
    original = next((row for row in decision.evidence
                     if row.operation == "rank" and row.venue_id == venue.id), None)
    if original is None:
        raise ValueError("this venue has no ranked artist shortlist to compare")
    artist_ids = original.query.get("options")
    if (not isinstance(artist_ids, list) or len(artist_ids) < 2
            or not all(isinstance(item, str) for item in artist_ids)
            or len(artist_ids) != len(set(artist_ids))):
        raise ValueError("the saved artist shortlist is invalid")
    changed_query = {**original.query, "signal_location": request.region,
                     "demographic": request.audience}
    if changed_query == original.query:
        raise ValueError("change the audience or region to compare a scenario")
    baseline_rows = [row for row in decision.evidence
                     if row.operation == "rank" and row.venue_id == venue.id
                     and row.query == original.query and row.source_id]
    complete_baseline = (all(row.status == "ok" for row in baseline_rows)
                         and len(baseline_rows) == len(artist_ids)
                         and {row.source_id for row in baseline_rows} == set(artist_ids))
    baseline_ranks = {artist_id: None for artist_id in artist_ids}
    if complete_baseline:
        baseline_ranks.update({row.source_id: index
                               for index, row in enumerate(baseline_rows, 1)})
    ranked = await asyncio.wait_for(client.call_tool("rank", changed_query), timeout=45)
    scenario_rows = ledger_rows("rank", changed_query, ranked, venue.id)
    decision.evidence.extend(scenario_rows)
    complete_scenario = (ranked.status == "ok"
                         and len(scenario_rows) == len(artist_ids)
                         and {row.source_id for row in scenario_rows} == set(artist_ids))
    scenario_ranks = {artist_id: None for artist_id in artist_ids}
    if complete_scenario:
        scenario_ranks.update({row.source_id: index
                               for index, row in enumerate(scenario_rows, 1)})
    names = {artist_id: next((row.name for row in decision.evidence
                             if row.source_id == artist_id and row.name), artist_id)
             for artist_id in artist_ids}
    note = ("Rank positions compare the same artist IDs within each call. "
            "The changed audience or region creates a new context; affinity values "
            "from the two calls are not a shared score.")
    if not complete_baseline or not complete_scenario:
        note += (" One or both calls did not return the full shortlist, "
                 "so missing ranks are not displayed.")
    result = ScenarioResult(
        venue_id=venue.id, status="ready" if complete_scenario else "no_evidence",
        original_query=original.query, changed_query=changed_query,
        artist_ids=artist_ids, artist_names=names,
        baseline_ranks=baseline_ranks, scenario_ranks=scenario_ranks,
        evidence_ids=[row.id for row in scenario_rows], note=note,
    )
    decision.scenarios.append(result)
    return result
