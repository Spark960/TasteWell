# Tastewell: product implementation plan

Status: product direction and implementation record, updated 2026-10-29 with the agentic decision slice. This plan supersedes the feature
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

## Scope decision: one product journey

Retire the standalone `/compare` Qloo-versus-model demo. It asks a different
question from the operator's job, duplicates an agent run, and did not give a
reliable demonstration in the 2026-10-28 live browser check: the listening-bar
case returned three successful Qloo envelopes but no grounded brief; the
jazz-club case showed tags while leaving the actionable sections empty. The
decision workspace completed a live concept resolution, returned three
artist-led pilots with source IDs, changed artist order under a new audience,
and saved a sample plan and explicitly synthetic outcome. These observations
support making the decision workspace the only product surface; they do not
establish operator value or real-world pilot impact.

The frontend `/compare` route, its navigation entry, dual-pane components,
and their UI tests are removed. Keep the old `/api/agent/*` backend path only
as an internal development harness until its callers and tests are audited;
it is not part of the product or submission story. Retire it separately if
the decision path has no dependency. Do not replace the page with another
model-only comparison. Demonstrate Qloo's contribution in the decision itself:
the selected concept tag, exact source entities and queries, within-call
artist ranks, changed-audience or changed-region rank movement, and an
operator-selected pilot with stated unknowns.

### Next implementation slice, in priority order

1. **Restore and prove the live path.** Diagnose the Qloo MCP harness spawn
   timeout, then complete a fresh decision through the visible UI. Confirm
   concept or artist ambiguity handling, option sources, and a fixed-ID
   scenario comparison. Health alone does not satisfy this gate.
2. **Prove an external demo path.** Build and smoke-test the current app on
   external hosting, protect shared decision history and operator data, and
   verify a public repository with a visible license. Do not depend on a
   private-access-only site for eligibility. Keep this deployment repeatable
   so the agent slice can be released and tested on the same host.
3. **Add one bounded decision agent.** Implement the agent review specified
   below on a saved, ready decision. It must use the operator's objective,
   inspect Qloo evidence, choose whether a supported scenario test is useful,
   and recommend one option and venue or ask for input or abstain. Persist
   its action record. Keep pilot selection with the operator.
4. **Make the agent legible.** Add one review action and an inspectable result
   to `/decision`: proposed pilot, why, alternatives considered, Qloo source
   links, scenario movement, unknowns, and next check. Keep the invented
   instant example explicitly separate from a live or saved-Qloo review.
5. **Verify and publish the agent journey.** Run B1–B3 in `VALIDATION.md`, including
   ambiguous IDs, sparse evidence, unsupported audience wording, unavailable
   LLM/Qloo, and invalid model citations. Check keyboard/mobile use and
   cancellation. Then test the agent journey on the external host from a
   fresh browser and keep submitted claims within what that build shows.
   An honest no-choice is a valid result.

### 2026-10-29 implementation checkpoint

- The workspace now opens a read-only illustrative decision instantly. Its
  two venues, three artists, partner, Qloo-shaped source rows, IDs, ranks,
  rank-changing audience scenario, and pilot plan are invented and labeled
  as such. It makes no Qloo request, writes nothing to SQLite, hides the
  live brief and selection/outcome controls, and provides a direct return
  to the real brief.
- The live ambiguity chooser now explains what the candidate tag describes
  (place category, venue style, amenity, audience, activity, and other known
  types). A place-category match is visually distinguished but still requires
  the operator to choose it. Raw tag IDs remain inspectable in the evidence
  drawer after selection. Artist records still lack enough metadata to
  distinguish identical names reliably; their IDs remain visible in that
  case, and richer candidate context is an open gate.
- Frontend lint and production build passed. A live browser run for a
  synthetic cocktail-bar brief reached the improved chooser, selected the
  place-category tag, produced three options, and displayed the selected
  tag ID in the source row. This proves the local flow, not recommendation
  usefulness for a real venue.
- Still open: fresh-session sample review by another person, the three
  benchmark journeys, sparse-data and accessibility checks, hosted smoke
  test, ownership/access control, and real operator feedback. The old
  `/api/agent/*` backend remains an internal harness pending a careful audit.

## Agentic decision slice: bounded pilot strategist

**Decision:** extend the existing decision workspace with an agent review of
a saved Qloo-backed shortlist. Do not put the legacy concept-brief agent on
the page unchanged. Its prompt fixes two `recommend` calls and writes a
different artifact; it does not inspect the decision's `rank` evidence or
choose a pilot. Reuse its provider and trace plumbing where useful, but give
the decision agent its own typed tools, output schema, and validator.

The deterministic path remains responsible for Qloo concept and artist
resolution, discovery, per-venue ranking, evidence capture, and hard checks.
The agent receives the operator's objective, the eligible venues, option
IDs, and a compact saved evidence summary. It may inspect source rows and
choose one relevant Qloo-backed scenario test when the operator has supplied
an alternate audience or region. It then proposes a first pilot and the
smallest check that could change that choice. It may instead ask for an
ambiguous or missing operator fact, or abstain when evidence is insufficient.
It never books an artist, records a pilot selection, or fabricates an
operational fact.

### Review contract and allowed actions

| Part | Implementation contract |
| --- | --- |
| Entry | `DecisionResult.status == "ready"`; a live decision or a clearly labeled replay of saved Qloo evidence. A replay permits saved-evidence inspection only and makes no fresh Qloo call. The invented `sampleDecision.ts` never calls the agent or appears as live evidence. |
| Inputs | Saved decision ID and snapshot version, plus optional operator-confirmed alternate audience **or** region. Do not invent a demographic synonym or silently change the decision brief. |
| Agent tools | `inspect_option(option_id)` returns only saved option and evidence rows; `check_venue(venue_id)` returns operator-supplied eligibility and budget facts; `compare_scenario(venue_id, audience, region)` delegates to the existing fixed-shortlist Qloo rank path, at most once on a live decision, only when the context actually changes. No arbitrary tool name, free-form Qloo arguments, web search, or direct write tool. The existing scenario path persists any new comparison. |
| Limits | At most four model turns and one new Qloo rank call, inside a total review timeout. Cancel on request. If the LLM is unavailable, retain the deterministic options and show review unavailable; do not silently substitute generic prose. |
| Output | A typed `recommend`, `needs_input`, or `abstain` result. A recommendation contains `option_id`, `venue_id`, cited `evidence_ids`, any `scenario_id`, a short rationale, alternatives considered, material unknowns, and one next validation action. Save the action log and the exact evidence snapshot version used. |
| Human control | The agent proposes. The existing selection endpoint still requires the operator's venue, owner, timing, measure, cost assumptions, and explicit submit action. A later scenario or evidence change marks an older review as stale. |

Use structured claim fields and render factual Qloo statements from validated
IDs, ranks, and query contexts rather than trusting free-form model prose.
The server validates every model output before it is saved or displayed.
Option, venue, scenario, and evidence IDs must exist in the reviewed snapshot;
cited evidence must have an appropriate successful status and actually support
the named option or scenario. A selected venue must permit live music. A
known quoted cost above the operator's budget is disallowed; unknown costs
remain unverified. Artist ranks are ordinal only within their own Qloo call.
The output schema has no fields for cross-call affinity arithmetic, combined
artist/brand scores, fees or availability, individual preference, predicted
attendance or sales, or unsupported geographic claims. On one invalid
model response, retry with validation errors and the same evidence; then
abstain with an explicit reason. Treat Qloo names and operator text as data,
not instructions to the tool dispatcher.

### Build sequence and file boundaries

1. **Grounding and storage.** Add typed `AgentReview`, `AgentAction`, and
   snapshot fingerprint fields alongside `DecisionResult` in
   `backend/app/api/decisions.py`. Save them through
   `backend/app/api/decision_store.py`; include them in export and preserve
   clear live/replay labels. Fingerprint the canonical request, options,
   evidence, and scenarios before and after a review. If the agent adds a
   scenario, store that final fingerprint with its result; compare it with
   the current decision to mark the review stale after later changes.
2. **Agent execution.** Add a decision-specific runner under
   `backend/app/agent/`. Reuse `LlmProvider`, but pass only bounded tool
   schemas and compact evidence. Its dispatcher calls existing engine
   functions for a scenario, records actions and correlation/evidence IDs,
   and returns typed results. Ensure repeated requests use the same
   snapshot version or explicitly start a new review.
3. **HTTP jobs.** Add `POST /api/decisions/{id}/agent-reviews` and
   `GET`/`DELETE /api/decisions/{id}/agent-reviews/{review_id}` in
   `backend/app/api/routes.py`, with progress, cancellation, a bounded
   timeout, and useful failures. Persist completed reviews; in-flight jobs
   may remain in memory as current decision jobs do. Do not let cancellation
   leave a partial recommendation marked ready.
4. **Decision UI.** Add a single "Review the pilot choice" action after
   options in `frontend/app/decision/page.tsx`. Show the agent's action
   summary in operator language, the Qloo comparison it ran, linked source
   rows, uncertainty, and an explicit "Choose this pilot" path to the
   existing plan form. Label replay or saved evidence; show no agent result
   on the invented example. Keep raw tool arguments in a disclosure, not as
   the primary explanation.
5. **Verification.** Unit-test dispatch limits, status handling, snapshot
   staleness, ID/claim validation, no-selection side effects, and LLM/Qloo
   failures. Run a browser journey from a fresh live decision through review
   and human selection; verify export/reopen shows the same action record.
   Use one consent-safe, redacted Qloo snapshot for a read-only replay demo
   only after checking the data and license terms. Update
   `CURRENT_FUNCTIONALITY.md`, `VALIDATION.md`, and the root overview with
   observed behavior, then run `graphify update .` after code changes.

**Acceptance gate:** a reviewer can identify what the agent chose to inspect,
which Qloo call it requested or why none was needed, what Qloo changed, why it
proposed a specific option and venue, and which facts remain unverified. B1
must produce a cited recommendation or a precise missing-fact request; B2
must not resolve ambiguity or rewrite an audience silently; B3 must show why
review cannot start without evidence, or label cultural fit unverified if
usable evidence exists. Invalid IDs and unsupported claims never
appear as grounded recommendations. The hosted journey must pass this gate
before the submission calls the visible product an agent-powered app.

**Release cutline:** a functioning external Qloo decision and safe public
demo take precedence over the new agent slice. If the agent review cannot
pass its grounding and hosted smoke tests before submission, keep it out of
the public journey and describe the shipped deterministic workflow accurately.
The invented instant example does not substitute for a live Qloo run or an
agent demonstration. Public access also needs isolated or protected decision
records: the present unauthenticated list/get/export endpoints must not
expose another visitor's data.

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

The product view is the grounded decision workspace. An internal offline
model-only benchmark can help evaluation, but it does not appear in the
operator UI or double latency for an operator action.

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
2. Qloo changes a concrete choice. The UI shows how a fixed artist shortlist
   changes rank under a different audience or region, the source calls behind
   each result, and what remains uncertain.
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
and the three benchmark briefs in `docs/VALIDATION.md`. Use clearly labeled
proxy assumptions wherever operator facts are unavailable.

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

Resume context: start at `backend/app/api/decisions.py`,
`backend/app/api/decision_store.py`, and `backend/app/qloo/mcp_client.py`.
The served MCP client has a per-session cache for identical successful or
empty requests. Preserve six-status semantics and existing decision tests.

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
call. The decision path already uses `find_tags`, `recommend`, `describe`,
and `rank` in explicit stages. Add new workflows only after their contracts
and decision value are verified.

### Phase 3 — Decision workspace UI

**Outcome:** an operator can complete the journey without reading an agent
trace or comparing two chat responses.

Work:
- Keep the decision setup, progress, three option cards, evidence drawer,
  scenario comparison, and selected-plan workspace as the only product flow.
- Add clear states for missing evidence, ambiguity, retries, and cancelled
  runs. Show progress by pipeline stage and time elapsed.
- Allow a user to pin, exclude, or revise candidate entities and regenerate
  only dependent stages. Show exactly what changed between versions.
- Remove the legacy dual-pane route and its UI dependencies. Make Qloo's
  contribution legible through the option evidence and scenario movement.
- Test keyboard navigation, mobile layout, readable source context, and
  a complete no-login demo journey.

Gate: a new user can select a feasible option and explain its evidence in
under five minutes; a sparse-data case exits honestly and usefully.

Resume context: `/` and `/decision` render `frontend/app/decision/page.tsx`.
The retired brief page is no longer a frontend regression target. Exercise
`frontend/e2e/decision.spec.ts` and the opt-in live decision test against
the explicit decision API.

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

Resume context: completed decisions, evidence, plans, scenarios, outcomes,
and replays now persist in SQLite. Decision jobs remain in memory, and there
is no user ownership, project versioning, or retention policy. Extend that
storage model before opening access to multiple operators.

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

Resume context: before the comparison removal, the backend suite passed
87 tests with 2 skipped. The frontend lint and production build passed after
the removal on 2026-10-28. `deploy/` contains an unbuilt private-preview
Compose/Caddy package; no hosted smoke test has run. See `backend/serve.ps1`,
`DEPLOYMENT.md`, and `deploy/README.md` for the local and planned setup, and
reassess access control, capacity, and storage before public exposure.

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

1. Read `AGENTS.md`, `HANDOFF.md`, `docs/CURRENT_FUNCTIONALITY.md`, this plan,
   and the relevant sections of `docs/qloo-contract.md`. Treat old milestone
   dates in `IMPLEMENTATION.md` as historical. Query Graphify before raw code
   search or reads. Preserve the working tree and verify listeners.
2. Start from `/` and the decision API. The `/compare` frontend and its
   mocked UI tests were retired; do not restore them as the default demo.
   Audit `/api/agent/*` callers before deleting the internal backend harness.
3. Implement the ordered next slice above: restore Qloo readiness, add the
   bounded agent review to the decision workspace, run benchmark and
   accessibility checks, and smoke-test a judge-accessible deployment.
   Keep Qloo evidence visible without asking users to interpret URNs or an
   internal tool trace.
4. Reconcile `docs/VALIDATION.md` with any new observations. A synthetic
   walkthrough confirms software behavior, not demand, revenue, or a real
   pilot outcome. Record real operator evidence only when it exists.
5. After code edits, run focused decision browser checks, frontend lint/build,
   relevant backend tests, and `graphify update .`. If the installed Graphify
   launcher remains unavailable, record that failure and retry when its uv
   runtime is restored.
