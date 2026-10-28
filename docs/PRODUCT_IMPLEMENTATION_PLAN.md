# Tastewell: product implementation plan

Status: desk-research direction and implementation record, 2026-10-28. This plan supersedes the feature
priorities in the deadline-driven `IMPLEMENTATION.md`; that file remains the
record of what was built and learned. Start with
[CURRENT_FUNCTIONALITY.md](CURRENT_FUNCTIONALITY.md) and
[qloo-contract.md](qloo-contract.md) when resuming work.

### Implementation checkpoint (2026-10-27)

| Phase | Implemented or verified | Open gate |
| --- | --- | --- |
| 0 | Validation pack and cited published proxy research. The user chose a desk-research path. | Buyer and willingness-to-pay claims remain unverified; online sources are contextual proxies, not interviews. |
| 1 | Typed evidence ledger, per-session MCP cache, total decision time budget, cancellable jobs, and saved-evidence replay. | Consent-safe fixture capture and a stronger claim validator for generated prose. |
| 2 | Operator artist names, human ambiguity choice, shared-ID rank calls per venue, and distinct pilot formats. | Real operator shortlist; verified fee/availability and stronger hard constraints. |
| 3 | Decision workspace, evidence drawers, progress, pilot selection, and mocked/live browser journeys. | Candidate pin/exclude/revision, accessibility and mobile audit with new users. |
| 4 | Fixed-ID audience/region scenario rank comparison, verified live. | Geographic semantics gate for a map and single-signal sensitivity checks. |
| 5 | SQLite decisions, plans, aggregated outcomes, JSON export, replay, and validated venue CSV import. | Projects, revisions, outcome CSV import, ownership, and retention rules. |
| 6 | Private-preview Compose/Caddy package and root `DEPLOYMENT.md` prepared. AWS Lightsail costs researched. | Docker build and hosted smoke test, multi-user auth, load/restart evaluation, real pilot outcomes, and public deployment. No AWS credentials are configured. |

See [the current functionality inventory](CURRENT_FUNCTIONALITY.md) for
exact API and UI behavior. The implementation is still a local product path;
none of the operator or production gates above has been claimed as passed.

## Product thesis

Tastewell should help a hospitality group make and revisit specific
programming and partnership decisions across its venues. The initial buyer
hypothesis is a marketing/experience lead or regional operator responsible
for roughly 3–30 venues; the exact segment must be tested in Phase 0. An
independent venue can use a self-serve version, but a portfolio team has
recurring decisions, several candidate sites, and a clearer budget owner.
The initial wedge is:

> “Given our venues, audiences, shortlist of acts/themes/partners, and
> operational constraints, which programming concept should we pilot next,
> where should we pilot it, why, and what will we learn?”

The system should return alternatives the operator can inspect, compare,
select, revise, and turn into a plan. Qloo supplies the cultural evidence;
the model interprets it and drafts copy. The model must not create the IDs,
rankings, measured affinities, or geographic claims that decide the winner.

This wedge uses the strongest current cross-domain evidence (concept tags,
artists, brands). Operators can supply a real shortlist; Qloo can discover
additional candidates when needed. Menu and location decisions can become
separate workflows after their data contracts and evaluation cases are
validated. A broad
“instant market analysis of any location” product would overlap last year's
[GeoTaste winner](https://devpost.com/software/geotaste-your-agentic-qloo-taste-business-consultant)
and dilute Tastewell's operator decision focus.

## Who uses it and why

| Role | Recurring job | What they bring | Decision Tastewell should improve |
| --- | --- | --- | --- |
| Hospitality group marketing/experience lead (first buyer hypothesis) | Fill a monthly events and partnerships calendar across several venues. | Venue list, audience, program shortlist, calendar, budget, brand constraints. | Which program and partner to test at which venue. |
| Regional operations manager | Approve a feasible pilot and allocate staff/capacity. | Hours, capacity, noise rules, staffing, margin targets. | Which attractive option is operationally possible. |
| Promoter or agency managing venue clients (second buyer hypothesis) | Pitch differentiated cultural programs repeatedly. | Client briefs, partner roster, creative concepts. | Which evidence-backed proposal to present. |
| Independent venue owner (self-serve user) | Pick one next event or collaboration. | One venue and a few candidate ideas. | What to try next and how to judge the trial. |

These are desk-research hypotheses, not validated customers. Restaurant operators report
uneven traffic and cost pressure and interest in technology for marketing,
feedback, and analytics ([National Restaurant Association, 2026](https://restaurant.org/education-and-resources/resource-library/report-sales-to-hit-%241-55t-in-2026-despite-challenging-business-environment/)).
That supports building and technically evaluating this workflow; it does not
prove a willingness to buy Tastewell. Operator frequency, current tools,
decision ownership, and purchase intent remain unknown by choice.

### Concrete operating case

A regional bar group has eight locations and needs to fill weak midweek
slots next month. Its marketing lead has a shortlist of performers, event
themes, and possible brand partners. They import venue addresses and
constraints (capacity, quiet hours, staffing, budget) plus optional
**aggregated** attendance or sales baselines from their own systems. No
customer names, transaction histories, or other personal data go to Qloo.

Tastewell resolves shortlist items to Qloo IDs, adds relevant discoveries,
and asks which combinations fit each venue's concept, audience, and area.
It shows three feasible pilot concepts with evidence and open questions,
including artist availability or fee where the operator must verify it.
The lead selects one concept and two candidate sites, gets an editable
activation plan, and later records actual attendance and cost. Tastewell
can then show whether the pilot beat **the group's own baseline**. Qloo
provides cultural fit evidence, not a prediction of attendance or profit.

The compelling output is a decision record: **“Try this at these sites,
because these Qloo signals and these operational constraints favor it;
here is the cheapest credible test and what would change our mind.”**

## Experience to build

1. **Set the decision.** Operator selects one or more venues, a target group,
   objective, and hard constraints (budget range, live music/no live music,
   opening hours, excluded categories, etc.). They may enter their own
   shortlist or ask for Qloo-backed discovery. The UI distinguishes required
   facts from optional preferences.
2. **Discover alternatives.** Resolve the venue concept, obtain Qloo-backed
   artist and brand candidates, and construct three genuinely different
   programming concepts from those returned entities. Every proposed entity
   must be in the evidence ledger.
3. **Compare.** Show a short option card for each: target audience fit within
   the same Qloo shortlist call, supporting signals, constraint fit, unknowns,
   and a concrete example event. The venue-by-option matrix distinguishes
   evidence from operator-supplied feasibility; it must not turn separate
   Qloo calls into one fake universal score. Let the operator inspect the
   evidence path and reject a questionable match.
4. **Stress-test.** Hold the candidate set fixed while changing one input
   (audience or location). Re-run the supported Qloo calls, show which option
   changes rank and why, and label non-comparable values clearly. A map can
   locate the group's venues and show validated geographic affinity evidence
   for a selected cultural anchor; it is not a foot-traffic map.
5. **Choose and act.** Operator picks an option. Tastewell generates a
   reviewable first event/partnership plan, outreach draft, and a small test
   with success measures chosen by the operator. Save the decision and its
   evidence snapshot so a later run can be compared with it.

The default product view is grounded. The existing generic run becomes an
optional “How would an ungrounded model answer?” explanation in a demo or
methodology panel; it should not double latency for every operator action.

## Map decision: useful, but only for a geographic question

**Add a map when it helps choose a pilot site or inspect a geographic
signal.** It is not required for the first evidence-backed programming
choice. A decorative heatmap would make Tastewell appear more precise than
its data supports. The map should answer: Where are the operator's venues?
Which area did a Qloo `where_popular` result cover for a resolved entity?
Which candidate site is operationally feasible? It must not label Qloo
affinity as traffic, demand, or revenue.

Recommended stack:

- **Renderer:** [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs),
  an open-source browser map library.
- **Basemap:** a region extract of
  [Protomaps PMTiles](https://docs.protomaps.com/basemaps/downloads) served
  from our own static/object storage, with required OpenStreetMap attribution.
  MapLibre can read it using the
  [PMTiles protocol](https://docs.protomaps.com/pmtiles/maplibre). The data
  and libraries are open; storage and bandwidth may still cost money.
- **Overlay:** our own venue points and catchment geometry, plus Qloo
  `where_popular` geohash/affinity cells only after checking their spatial
  resolution and meaning on real examples. The legend must say “aggregate
  cultural affinity for [entity] in [area]”, with date/source and limitations.
- **Geocoding:** start with verified venue coordinates or a switchable,
  cached address provider. Do not build typeahead on the public OSM Nominatim
  service; its [policy](https://operations.osmfoundation.org/policies/nominatim/)
  forbids that and limits heavy usage. Keep private venue data out of public
  geocoding requests unless the operator understands the data flow.

Do not depend on the public OSM tile servers for a commercial product: OSM
data is free, but its public [tile service](https://operations.osmfoundation.org/policies/tiles/)
has limited capacity and no SLA. MapTiler's free cloud plan is restricted
to non-commercial use or R&D for commercial products under its
[terms](https://www.maptiler.com/terms/cloud/). A self-hosted regional
basemap is the cleanest no-license-fee path; use a paid tile service if
operations become a distraction.

Map acceptance gate: the same decision must still be understandable in a
table/list without a map, and a reviewer must be able to explain exactly
what every colored cell represents. If validated Qloo geography adds no
decision value, keep the map out of the primary workflow.

## What would make this stand out

The competitive bar is already above “three AI ideas with citations.”
Current entries such as [TasteStage](https://devpost.com/software/tastestage)
compare Qloo-backed concepts, while
[TasteTest](https://devpost.com/software/tastetest) maps candidate store
locations for a product test. Tastewell should demonstrate a **closed
operating loop** that neither a broad market dashboard nor a one-off concept
generator provides:

1. An operator can enter their own venues, shortlist, and constraints. The
   current demonstration uses explicitly synthetic inputs.
2. Qloo changes a concrete choice. The UI shows which alternative would
   have been chosen without a particular signal, and what remains uncertain.
3. The operator rejects or edits an option and the system re-plans without
   losing source history or confirmed constraints.
4. The selected option becomes an executable pilot with owner, date,
   budget assumptions, and measurable success criteria.
5. Later, the team records the outcome beside the original rationale and
   can use it for the next decision. Outcome data stays distinct from Qloo.

The flagship demonstration should follow one believable decision from
input to pilot plan in a few minutes, then show a saved follow-up. A
recorded, clearly labeled case provides instant inspection; a live path
proves the integration. Both must expose evidence and limitations without
requiring viewers to read an internal trace. Avoid claiming that a
single pilot proves lift or that cultural affinity forecasts sales.

## Non-negotiable product rules

- **Evidence before prose.** Store typed Qloo entities, tags, envelopes,
  query context, and IDs before model synthesis. Validate that displayed
  entities/citations exist in that run's evidence ledger.
- **Comparable only when comparable.** `rank` orders a single shared options
  set per call. Do not compare rank numbers from different calls as if they
  shared a scale. Scenario changes can show ordinal shifts and evidence
  differences, with a warning about the changed context.
- **No false precision.** Do not call affinities sales forecasts, audience
  shares, predicted ROI, or causal effects. Separate Qloo observations,
  model interpretation, operator assumptions, and test outcomes in the UI.
- **Human resolution.** Ambiguous entity/tag matches stop the dependent path
  and ask for a choice. An empty/error/degraded response is visible; it does
  not silently turn into a model guess.
- **A useful artifact.** Every completed journey should end in a decision
  record and a practical next action, not just a longer report.
- **Operational truth is separate.** Qloo says nothing about an act's booking
  availability, fee, venue capacity, licensing, weather, or margin. Those
  come from operator inputs or separately verified integrations, and unknown
  values stay explicitly unknown.
- **Replayable demos.** Keep redacted, consent-safe evidence snapshots for
  deterministic examples; distinguish replay from live Qloo results.

## Phases

### Phase 0 — Validate the wedge and define success

**Outcome:** a narrow operator decision with an evaluation rubric, not a
feature list.

Work:
- Use published industry reports and vendor surveys as context. Label every
  inferred buyer, workflow, pain point, and budget assumption; do not write
  invented interview answers or pilot outcomes.
- Choose one initial decision (recommended: weekly event/programming
  direction). Write three realistic benchmark briefs including a difficult
  audience, ambiguous concept, and sparse-data area.
- Define a quality rubric: option distinctness, evidence validity, decision
  usefulness, constraint fit, uncertainty honesty, time to first useful
  result, and ability to complete a decision without explanation from the
  builder. Record a pre-Tastewell decision for comparison.
- Run a short contract probe for any proposed new tool combinations before
  designing around them. Record results in `docs/qloo-contract.md`.

Gate for this run: three synthetic benchmarks have expected acceptable and
unacceptable outcomes, cited market context, and recorded technical results.
This gate cannot establish buyer demand or willingness to pay.

Resume context: use `docs/CURRENT_FUNCTIONALITY.md`, `docs/qloo-contract.md`,
and the nine current presets. Use clearly labeled proxy assumptions wherever
operator facts are unavailable.

### Phase 1 — Evidence ledger and deterministic data pipeline

**Outcome:** each option and claim can be traced to a stable Qloo result.

Work:
- Introduce typed request, entity, tag, envelope, evidence, and decision
  models. Give every evidence row a stable internal ID and preserve the Qloo
  query, selected candidate ID, status, correlation ID, and retrieval time.
- Split the current open-ended `AgentRunner` into explicit stages: resolve,
  discover, rank, synthesize. Let the model plan within bounded choices;
  keep ID validation and scoring outside model text.
- Implement run-level caching for identical safe Qloo requests on the MCP
  path, with TTL and key isolation. Add cancellation and hard time budgets
  that cover MCP readiness, tools, and LLM together.
- Add fixture capture/replay that strips credentials and personal data. Use
  it for deterministic UI/evaluation runs. A replay badge must be visible.
- Reject an output that cites unknown IDs, changes measured numbers, or
  invents a candidate, then request a bounded repair or surface an error.

Gate: every displayed recommendation can open its source row; invalid IDs
never render as grounded; repeated identical requests reuse cached evidence.

Resume context: start at `backend/app/agent/tools.py`,
`backend/app/qloo/mcp_client.py`, `backend/app/api/engine.py`, and
`backend/app/agent/loop.py`. The existing `qloo exec` TTL cache is not on the
served MCP path. Preserve six-status semantics and existing tests.

### Phase 2 — Decision engine for programming alternatives

**Outcome:** three evidence-backed options and a reasoned choice, with no
fabricated ranking.

Work:
- Accept an operator's actual shortlist and use `find_tags`/`recommend` to
  build a typed candidate pool of artists, relevant brands, and concept
  tags. Resolve entity ambiguity before ranking. Add `entity_tags`/
  `describe` only where a validated entity ID gives useful differentiation.
- Build alternatives from distinct combinations of returned candidates and
  operator constraints. Enforce diversity rules so three cards are not
  synonyms. Use a deterministic constraint filter before ranking, and keep
  unavailable/unknown booking, fee, and staffing facts visible.
- Probe and integrate `rank` for a **single shared shortlist** of the same
  entity type under the same signal context. Record the full option set and
  ranking call. Do not merge artist and brand affinity into an invented
  universal score.
- Generate a decision explanation with four labeled parts: Qloo evidence,
  operator constraints, interpretation, and unknowns. Permit “no supported
  recommendation” when evidence is thin.

Gate: each benchmark produces distinct, feasible alternatives; a reviewer
can reconstruct the choice from saved Qloo IDs and rules; swapping audience
or constraints can change the recommendation for a defensible reason.
For this desk-research run, test a clearly labeled synthetic shortlist. A
real-world feasibility or value claim would still require real operator data.

Resume context: `docs/qloo-contract.md` verifies `rank` only within one
call, and `GroundedTools.DEFAULT_LLM_TOOLS` currently exposes just
`find_tags`/`recommend`. Expand a stage's allowed tools deliberately rather
than exposing all nine to one unbounded agent loop.

### Phase 3 — Decision workspace UI

**Outcome:** an operator can complete the journey without reading an agent
trace or comparing two chat responses.

Work:
- Replace the dual-pane first screen with a decision setup, progress,
  three option cards, evidence drawer, and selected-plan workspace.
- Add clear states for missing evidence, ambiguity, retries, and cancelled
  runs. Show progress by pipeline stage and time elapsed.
- Allow a user to pin, exclude, or revise candidate entities and regenerate
  only dependent stages. Show exactly what changed between versions.
- Keep the generic comparison as an opt-in explainer. Make the grounded
  evidence and decision difference legible without it.
- Test keyboard navigation, mobile layout, readable source context, and
  a complete no-login demo journey.

Gate: a new user can select a feasible option and explain its evidence in
under five minutes; a sparse-data case exits honestly and usefully.

Resume context: `frontend/app/TastewellApp.tsx` currently starts both modes
with `Promise.allSettled`; `BriefForm.tsx` only gathers concept/region/
audience; `ResultPane.tsx` renders prose sections. Replace that orchestration
incrementally against the typed Phase 1/2 API, retaining the current path
as a regression fixture until the new flow is stable.

### Phase 4 — Scenario lab and geographic intelligence

**Outcome:** the operator can test whether the choice is robust to a changed
audience or catchment, without mistaking affinity for revenue.

Work:
- Hold candidate IDs fixed and re-run ranking/recommendation for a changed
  audience or region. Display ordinal movements, new/absent evidence, and
  query-context differences; do not subtract separate-call scores.
- Evaluate `where_popular` for validated concrete entities and a bounded
  region. If its geohash output supports a useful map, render it with a
  legend describing cultural affinity rather than demand or foot traffic.
- Add a MapLibre/PMTiles view only after the geographic evidence gate above.
  Plot verified venue coordinates and optional operator-defined catchments.
  Make spatial resolution, source, and attribution visible; give every map
  point/cell an equivalent accessible table entry.
- Use `compare_audiences` only on actual entity groups. For free-text
  demographic scenarios, use separate supported queries and label them as
  scenario comparisons, not that workflow's output.
- Add sensitivity checks: remove one anchor/tag at a time and flag rankings
  that depend heavily on a single signal.

Gate: users can see what changed, what stayed stable, and which comparisons
are not valid; map claims match the underlying Qloo response semantics. A
pilot operator can use the venue view to pick a test site or explain why the
map did not help.

Resume context: consult `docs/qloo-contract.md` for `where_popular`,
`compare_audiences`, and `rank`; never infer demographics from entity-group
comparison or predict sales from geohash affinity.

### Phase 5 — Persistent decisions and action loop

**Outcome:** Tastewell becomes a working tool used after the first answer.

Work:
- Persist projects, brief versions, option sets, evidence snapshots,
  operator selections, rejected options, and generated plans. Add ownership
  and data-retention rules before multi-user accounts.
- Produce a concrete launch experiment: event/partner concept, operational
  checklist, outreach draft, budget assumptions supplied by the operator,
  and success measures. Mark generated text as editable and unverified.
- Let the operator record actual outcomes (attendance, sales, feedback) as
  **their** data. Show outcomes beside the original hypothesis; do not use
  them to claim Qloo predicted the result or expose them to Qloo without
  explicit product consent.
- Support a minimal CSV import of venue metadata and aggregated past event
  results before attempting POS integrations. Separate operator data from
  Qloo evidence in storage, access control, and exports.
- Export a decision record that includes sources, assumptions, and
  limitations. Support re-opening and revising an earlier decision.

Gate: a user can return later, understand why they chose an option, record
what happened, and make a better next decision without losing provenance.

Resume context: today `Engine.runs` is an in-memory dictionary; SSE history
and picks disappear on restart. Pick a persistent storage design only after
the Phase 1 evidence schema is stable.

### Phase 6 — Reliability, evaluation, and production

**Outcome:** the product works for strangers and its quality claims are
measured.

Work:
- Build an evaluation set from the Phase 0 briefs and later real cases.
  Score evidence validity, useful distinction, honest abstention, latency,
  completion rate, and operator preference. Measure whether operators make
  a different and better-explained choice than they would from a generic
  brief; then follow actual pilots without claiming causal proof. Include
  adversarial ambiguous, empty, degraded, 429, malformed-output, and
  MCP-timeout cases.
- Run model comparisons on the **same saved Qloo evidence** to separate LLM
  quality from data variance. Track token cost and failure rates; select a
  fallback policy that cannot silently change evidence or exhaust quotas.
- Add authentication, per-user limits, secrets hygiene, monitoring,
  structured logs, durable run jobs, retries with idempotency, and safe
  caching. Load-test concurrent decisions and verify restarts.
- Deploy the full backend/MCP runtime and frontend behind HTTPS. Provide a
  live path and a labeled recorded case that can be inspected instantly.
- Audit accessibility, mobile use, setup from a fresh clone, and every
  statement in the product and README against the implemented system.

Gate: external users can finish the journey; failure modes are observable;
the evidence rubric improves on the current brief baseline; at least two
pilot operators complete a real decision and one records an outcome; saved
decisions survive a restart; a fresh install and hosted smoke test pass.

Resume context: the current mocked backend suite passed 69 tests with one
live test skipped on 2026-10-27. There is no `deploy/` directory. See
`backend/serve.ps1`, `frontend/.env.local`, and the deployment notes in
`IMPLEMENTATION.md` for the present local setup, but reassess capacity and
storage for the larger product.

## Sequencing and decision points

Phases 0–2 form the first new vertical slice. Build and evaluate one
programming decision before adding menu optimization or a geographic map.
Phase 3 exposes that slice to users. Phase 4 broadens its reasoning only
after its Qloo semantics are confirmed. Phase 5 gives the product memory;
Phase 6 makes quality and reliability measurable.

Open decisions to settle during Phase 0: whether the first buyer is a
hospitality group marketing lead, regional operator, or agency; the first
recurring decision; required constraints; and which operator outcome counts
as a successful recommendation. The implementation should remain narrow
until those answers are supported by real user evidence.

## Next-chat launch checklist

1. Read `HANDOFF.md`, `docs/CURRENT_FUNCTIONALITY.md`, this plan, and the
   relevant sections of `docs/qloo-contract.md`. Treat the old P5/P6 dates in
   `IMPLEMENTATION.md` as historical.
2. Read `AGENTS.md`. Query the existing Graphify code graph before raw code
   search/read; use `graphify explain "GroundedTools"` or a focused query to
   locate implementation seams. The code-only graph is sufficient for this
   plan. Do not upload repo documents/images to an LLM indexing backend
   without specific authorization.
3. Preserve the current working tree. Run `git status --short`; do not reset
   the uncommitted fixes/docs. Verify listeners before assuming local servers
   are alive.
4. Create `docs/VALIDATION.md` for Phase 0: buyer and purchase hypotheses,
   a short interview guide, three concrete decisions from a plausible
   multi-venue operator, expected outputs, failure cases, and the scoring
   rubric. Mark assumptions and evidence separately.
5. Build a probe table for the first decision: inputs, Qloo workflow, exact
   contract, ambiguity handling, output field, and claim it can support.
   Probe only unanswered contract questions with bounded live calls; record
   results in `docs/qloo-contract.md`.
6. Use the resulting brief and rubric to define the Phase 1 typed evidence
   schema and a narrow Phase 2 programming-decision slice. Keep the map and
   persistent workspace behind their own gates.

Phase 0 is ready to hand off when another developer can run the three cases,
judge the outputs against written criteria, and list the questions that
require a real operator rather than guessing them in code.
