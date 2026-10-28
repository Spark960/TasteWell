# Tastewell: current implementation and intended product

Updated 2026-10-28. This is a map of **what exists in this repository today** and **what the project is meant to become**. The current app is a working local prototype and a prepared private-pilot deployment package. It is not a deployed public product or a validated hospitality business.

For hands-on commands, see [README.md](README.md). For AWS setup, see [DEPLOYMENT.md](DEPLOYMENT.md). The detailed product sequence and known gaps are in [docs/PRODUCT_IMPLEMENTATION_PLAN.md](docs/PRODUCT_IMPLEMENTATION_PLAN.md).

## What Tastewell is supposed to be

Tastewell is intended to help a hospitality operator make a specific programming or partnership decision across one or more venues: **which concept or act should we pilot, at which venue, why, and what will we measure?** The likely first user is a marketing or experience lead managing multiple venues. That user and the 3–30-venue range are design hypotheses based on desk research, not interviewed or confirmed customers.

The intended workflow is an operating loop:

1. Enter venues, a target audience, a shortlist of acts or themes, objectives, and operational limits.
2. Resolve those concepts and candidates to real Qloo IDs. Use Qloo's aggregate cultural signals to discover and compare alternatives.
3. Show a small number of distinct pilot options with source rows, constraints, and unknowns. Keep artist ranking within a single comparable Qloo shortlist call per venue.
4. Change one assumption, such as audience or region, to see whether the shortlist order changes.
5. Select a pilot, record a practical owner/date/measurement plan, then save aggregated results beside the original rationale.

The intended value is a **traceable, revisitable decision record** rather than a one-off AI paragraph. Qloo supplies cultural evidence; it does **not** supply booking availability, fees, staffing, licensing, sales forecasts, or causal proof that a pilot worked. Those facts must come from the operator or another verified source. No real operator interviews or measured pilot outcomes are claimed in this project.

## What is implemented now

There are **two related frontend experiences**:

| Route | Purpose | Current status |
| --- | --- | --- |
| **/** and **/decision** | Primary programming-decision workspace: compare artist options across venues, choose a pilot, save evidence and an outcome. | Implemented for an artist-led live-music slice, with meaningful limitations below. |
| **/compare** | Secondary concept-brief demo: compare a Qloo-grounded brief with a generic model-only brief. | Implemented; useful for showing what Qloo adds, but runs are not saved as decisions. |

### The original brief demo at /compare

The user can choose one of nine quick presets or type a venue concept, region/catchment, and target audience. **Run both panes** starts two backend runs in parallel. The grounded run uses the Qloo harness to resolve a concept tag and find cultural recommendations; the generic run asks the configured language model without Qloo. The page streams progress and a live trace, then displays brief sections such as audience profile, menu tilt, music/programming, adjacent brands, tag themes, and explicit absences. Ambiguous Qloo matches are presented for a user choice, which restarts the relevant run with the selected ID.

This route is a **comparison/demo**. Its runs and trace are held in backend memory and are lost on backend restart. The Stop button aborts browser stream consumption; it does not reliably stop backend work already started.

### The programming-decision workspace at / and /decision

The form accepts a venue concept, audience, objective, first venue, up to nine additional venues, a live-music permission flag, optional budget ceiling for each venue, and up to five artist names. A four-column CSV can populate 1–10 venue rows in the browser; the file itself is not sent to the server until the user submits the resulting form.

The backend asks the user to resolve ambiguous concept tags or artist names. It uses Qloo to discover artists when no shortlist is supplied, or to resolve supplied names with describe. It obtains an optional brand suggestion. When at least two artists are available, it sends the **same artist ID set** to one Qloo rank call per eligible venue. It constructs up to three artist-led pilot formats, with Qloo evidence IDs and explicit unknowns. Venues that prohibit live music are excluded. Rankings from different venue calls are displayed separately; their affinity values are not combined into a universal score.

The user can inspect source rows, choose an option and eligible venue, and record a pilot owner, date/window, success measure, baseline, cost assumption, next action, and optional known total cost. If that known cost exceeds the selected venue's budget ceiling, the API rejects the selection. If cost is unknown, affordability remains unverified. The user can later enter an **aggregated** outcome against a baseline from their own records; the difference is not presented as causal impact.

Additional current actions are saved-decision history, JSON export, a labeled replay from the saved evidence without a new Qloo call, and a scenario comparison that reranks the same saved artist IDs after changing audience or region for one venue. Decision creation and ambiguity resolution run as cancellable background jobs with visible stage and elapsed time, under a 180-second total decision budget. Completed decision documents are stored in SQLite; in-flight job state is in memory.

## What the frontend looks like today

The app uses a curated field-guide visual system: warm paper surfaces, deep green navigation, Newsreader headings, DM Sans controls, and small evidence marks. The decision workspace has a visible four-stage trail. Forms use two columns when space allows and stack on smaller screens.

**Comparison page (/compare):** A shared Tastewell header links back to decisions. A brief form with presets sits beside the **Grounded**, expandable **Live trace**, and **Ungrounded** results on wide screens; it stacks above them on smaller screens. Before a run, both result sections show empty states. The footer explains that Qloo's data concerns aggregate cultural affinity.

**Decision page (/ and /decision):** A shared Tastewell header has navigation and **Saved decisions**. A green decision trail shows the brief, options, plan, and outcome stages beside the main workspace on wide screens and as a compact step row on smaller screens. The brief form holds venue/concept/region/audience/objective/budget inputs, the live-music checkbox, additional-venue controls, CSV picker, artist-shortlist textarea, and **Explore options**. After a run, the page shows progress or a resolution chooser, then option records with source counts, venue-by-venue ranks, unknowns, constraints, and expandable Qloo evidence. Scenario comparison, pilot plan, and aggregated outcome follow below. Replay and JSON export remain beside a saved decision. Errors and unavailable evidence stay visible.

These describe the local rendered pages on 2026-10-28, including a phone-width check. They are not a claim that the product has been validated with operators.

## How the frontend connects to the backend

The frontend is **Next.js/React**. The backend is **FastAPI/Python**. The browser never calls Qloo or a model provider directly and never receives their API keys.

~~~mermaid
flowchart LR
    Browser["Browser: Next.js pages"] -->|"JSON fetch or SSE"| API["FastAPI /api/*"]
    API --> Engine["Engine and decision pipeline"]
    Engine --> MCP["Qloo MCP client / harness"]
    MCP --> Qloo["Qloo API"]
    Engine --> LLM["Configured model provider\n(brief demo)"]
    Engine --> DB["SQLite decision snapshots"]
~~~

**Local development:** The frontend normally runs at http://localhost:3000 and the backend at http://localhost:8000. frontend/.env.local sets NEXT_PUBLIC_API_BASE=http://localhost:8000, so browser fetch calls go to the FastAPI server. FastAPI allows the configured local frontend origin through CORS. The comparison demo's typed client is in frontend/lib/api.ts; the primary decision page makes its API requests in frontend/app/decision/page.tsx.

**Private AWS preview:** Caddy fronts both services on one HTTPS origin. It asks for a shared Basic Auth password, routes /api/* to the backend container on port 8000, and routes other paths to the frontend container on port 3000. The frontend build uses an empty API base, so requests stay on that same origin. The backend receives Qloo/model credentials through a private host .env file. The prepared stack is in deploy/compose.yaml and deploy/Caddyfile. A Docker image build and hosted smoke test have not yet been completed.

### Main request paths

| User action | Browser/API exchange | What the backend does |
| --- | --- | --- |
| Run the original brief | POST /api/agent/run for each mode; GET /api/agent/stream/{run_id} for Server-Sent Events; GET /api/agent/runs/{run_id} for a summary when needed. | Starts grounded and generic AgentRunner tasks; streams trace/final events. Runs are in memory. |
| Explore a decision | POST /api/decision-jobs, then poll GET /api/decision-jobs/{job_id}; DELETE cancels an in-flight job. | Runs the deterministic decision pipeline, records status/stage, and saves a completed DecisionResult in SQLite. |
| Resolve an ambiguous match | POST /api/decisions/{id}/resolve-jobs with a selected candidate ID, then poll the returned job. | Verifies the choice against the saved candidate set and continues the same decision ID. |
| View or export history | GET /api/decisions, GET /api/decisions/{id}, GET /api/decisions/{id}/export. | Reads saved SQLite decision documents. |
| Compare a scenario | POST /api/decisions/{id}/scenarios. | Re-ranks fixed artist IDs for the changed audience or region and saves both contexts. |
| Choose a pilot or record outcome | POST /api/decisions/{id}/select/{option_id}; POST /api/decisions/{id}/outcome. | Checks option/venue membership and known-cost budget limit; saves the plan and later aggregated result. |
| Replay saved evidence | POST /api/decisions/{id}/replay. | Copies the saved snapshot into a new, labeled decision without calling Qloo. |

GET /api/health checks that the API process is alive; it does **not** check Qloo. GET /api/qloo/status attempts a separate harness readiness check. That distinction matters when the page loads but Qloo-backed work cannot start.

## Backend boundaries and data

- **FastAPI routes** live in backend/app/api/routes.py. backend/app/main.py creates the app and local CORS policy.
- **Engine** in backend/app/api/engine.py owns in-memory brief runs and decision jobs, starts Qloo clients, applies the total decision timeout, and saves decisions.
- **Deterministic decision logic** in backend/app/api/decisions.py resolves Qloo tags/artists, obtains recommendations and per-venue rank calls, builds option cards, and records evidence rows. The newer decision path does not ask a model to invent entity IDs or scores.
- **Brief agent** in backend/app/agent/ uses the configured model provider for the older grounded/generic brief comparison.
- **Qloo access** is through backend/app/qloo/mcp_client.py and the installed Qloo MCP harness. The MCP client caches identical safe calls within a client session; it does not make all later decisions permanently cache-resident.
- **Persistence** is backend/data/decisions.sqlite, managed by backend/app/api/decision_store.py. It stores decision JSON with requests, evidence, options, selections, scenarios, and outcomes. That directory is gitignored. Generic brief runs and active decision jobs are not persisted.
- **Evidence rows** retain the operation, input query, status, Qloo source ID where available, correlation ID, retrieval time, and related venue. A card cites evidence-row IDs so its named Qloo entities can be inspected.

## What remains open

| Area | Current boundary |
| --- | --- |
| Operational feasibility | Live-music permission is enforced; a known total cost above a venue budget is rejected. Availability, artist fee unless supplied, staffing, licensing, capacity, sound cutoff, and actual event timing are not verified. |
| Candidate control | No full pin/exclude/revise workflow or editable plan regeneration yet. |
| Program scope | Current decision options are artist-led live-music formats. Maker, film-club, menu, and location decisions are outside this slice. |
| Geographic map | No map or heatmap is rendered; Qloo geographic semantics need validation before adding one. |
| Accounts and privacy | No per-user accounts, ownership, or retention policy. All saved decisions are visible to anyone who can access the API or the shared private-preview password. |
| Evaluation | Desk research and synthetic briefs exist, but no operator interviews, buying evidence, or real pilot uplift measurements were collected. |
| Deployment | A single-host Docker/Caddy package and beginner AWS guide exist. Docker images, hosted Qloo readiness, backups, and an AWS smoke test still need verification. |

The last deterministic backend suite reported **86 passed with 3 live tests deselected**. After the visual redesign, the frontend production build and lint passed, and **seven mocked browser journeys passed with two live journeys skipped**. A local /api/qloo/status check previously returned **harness spawn timeout**. Treat that as an environment readiness issue to resolve before calling a live pilot usable. The local health endpoint alone does not prove Qloo integration is ready.

## Key files

| Path | Role |
| --- | --- |
| frontend/app/TastewellApp.tsx | Original two-pane brief page. |
| frontend/app/decision/page.tsx | Decision workspace UI and its API calls. |
| frontend/app/decision/venueCsv.ts | Strict client-side venue CSV parser. |
| frontend/lib/api.ts | Typed brief-demo API and SSE client. |
| backend/app/api/routes.py | FastAPI HTTP contract. |
| backend/app/api/engine.py | Run/job orchestration, timeouts, save/replay. |
| backend/app/api/decisions.py | Decision models, Qloo-backed option construction, scenarios. |
| backend/app/api/decision_store.py | SQLite storage. |
| backend/app/qloo/mcp_client.py | Qloo harness connection and safe-call cache. |
| deploy/compose.yaml and deploy/Caddyfile | Prepared private-preview containers, routing, and shared password. |
| docs/qloo-contract.md | Observed Qloo request/response shapes and caveats. |
| docs/VALIDATION.md | Published proxy evidence, assumptions, and synthetic benchmarks. |
