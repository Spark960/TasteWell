# Tastewell handoff for the next chat (2026-10-29)

## Latest checkpoint — release pushed; Lightsail creation pending (2026-10-29)

The user asked to pause because usage is low. Resume the active goal when they
return. This section supersedes older checkpoint statements below about no
Git remote, missing browser ownership, or Qloo readiness.

- The Qloo-grounded decision review is implemented and visible in the decision
  workspace. It runs a bounded tool-calling review, validates evidence and
  allowed actions, persists the review, and leaves final pilot selection to the
  human operator. The live browser journey passed with real Qloo and a model
  on a synthetic brief in the previous turn. See `docs/VALIDATION.md`.
- Production decisions now belong to a signed, secure browser session. Other
  browsers cannot list, read, export, replay, mutate, or inspect jobs for that
  session's decisions. Existing unowned rows are inaccessible in production.
  The public session test and full non-live backend suite pass: **97 passed,
  3 deselected**. The legacy `/api/agent/*` routes return 404 in production.
  Frontend lint/build and five mocked browser tests passed in the previous
  turn; the opt-in real Qloo/model browser journey passed there too.
- `graphify update .` completed after code edits (876 nodes, 2,114 edges).
  Follow `AGENTS.md`: query Graphify before code searches and update after
  further code edits.
- The existing public [Spark960/TasteWell](https://github.com/Spark960/TasteWell)
  repository matches the checkout, so no duplicate was created. The tested
  release commit `9c325ed` was pushed to `origin/main`. A filename and pattern
  audit found no staged credential file, private key, SQLite database, or real
  API key. `git diff --cached --check` passed before the commit.
- The user supplied a signed-in AWS Mumbai console URL. The Lightsail create
  form is open in Chrome at `ap-south-1.console.aws.amazon.com/lightsail/webapp/create/instance`.
  It is configured for **Mumbai, Ubuntu 24.04 LTS, general purpose dual-stack,
  4 GB RAM / 2 vCPUs / 80 GB SSD, $24/month, one instance named
  `tastewell-demo`**. Automatic snapshots are off. The default SSH key option
  is selected; Lightsail says it will create a default key in this region.
  **No instance has been created.** Browser policy requires the user to perform
  the final Create instance action because it starts recurring charges. Keep
  the prepared tab as a handoff; inspect its state again before proceeding.
- AWS CLI has no configured credentials and local Docker daemon is unavailable.
  Once the instance exists, finish the Lightsail setup from `DEPLOYMENT.md`:
  static IP, HTTP/HTTPS firewall, HTTPS hostname (a domain or IP-based
  `sslip.io` hostname), Docker, cloned release, private `.env`, and Caddy
  Compose. `SESSION_SECRET` must be a stable random 32+ character value in the
  private `.env`; the production backend fails fast if missing. Keep Qloo and
  model keys off GitHub. Verify `/api/qloo/status`, a real decision and agent
  review, persistence after restart, and the external browser path. The Caddy
  gate still uses one shared Basic Auth password; supply judge credentials
  through the submission if this remains the external demo configuration.
- `DEPLOYMENT.md` still contains older text describing no Git remote, a stale
  Qloo timeout, and older account credit figures. Update those sections on
  resumption after the live deployment path is known. A hosted demo has **not**
  been verified yet. Do not mark the goal complete before that gate.

## Hackathon requirement and submission status audit (2026-10-29)

The root [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) is now the current status.
The code has a genuine Qloo-backed decision pipeline and an older LLM
tool-calling agent wired to Qloo, but the visible product path is deterministic
and does not use that agent. The "agentic tool" reading is plausible, not a
guaranteed judge interpretation; make agent action visible in the decision
journey before claiming a strong agentic submission. The app only needs one
focused cultural use case, not every Qloo domain.

The current backend health check passed, but `/api/qloo/status` returned
`ready: false` with `harness spawn timeout`. Previous live Qloo runs succeeded,
so diagnose current process readiness and rerun the visible journey. The
official hackathon overview requires an externally hosted, fully published
demo. None is verified, and `git remote -v` currently shows no remote; the
earlier handoff's statement that a public repository exists was incorrect.
`LICENSE` is present locally. Devpost's overview and rules differ on whether
a password-protected demo qualifies; prefer an externally accessible demo
with safe data. No code was changed in this audit, only root documentation.

## Active checkpoint — instant example and clearer Qloo choice (2026-10-29)

The user said to continue from the previous handoff. We followed the first
two priorities in `docs/PRODUCT_IMPLEMENTATION_PLAN.md` while preserving the
uncommitted comparison-page removal.

### Done

- Added `frontend/app/decision/sampleDecision.ts`, an entirely invented,
  read-only example with two sample venues, three artists, a sample partner,
  `urn:sample` IDs, source-shaped rows, a rank-changing audience scenario,
  and a sample pilot plan. The workspace opens it instantly from **See an
  illustrative decision** and returns to the live brief with **Start your own
  decision**. The example makes no Qloo request, is not saved, hides the live
  brief and export/replay/selection/outcome controls, and says no event or outcome has
  occurred. It is a UI fixture, not a real Qloo response or customer story.
- Improved the live concept ambiguity chooser in
  `frontend/app/decision/page.tsx` and `decision.css`: category, venue style,
  amenity, dining option, product/service, activity, setting and other known
  tag types now have plain-language descriptions. Place-category choices are
  visually distinguished but never selected automatically. Artist choices
  still expose their record IDs because the backend does not provide enough
  metadata to distinguish identical names.
- Updated the relevant expectations in `frontend/e2e/decision.spec.ts` and
  described the new state in `README.md`, `docs/CURRENT_FUNCTIONALITY.md`,
  and `docs/PRODUCT_IMPLEMENTATION_PLAN.md`.
- Frontend lint, TypeScript production build, and `git diff --check` passed.
  In the live browser, the sample opened instantly and the real cocktail-bar
  brief reached the new chooser. Selecting the place-category match produced
  three live Qloo options; the evidence drawer showed the selected
  `urn:tag:category:place:cocktail_bar` ID. This was a local synthetic brief,
  not validation of venue usefulness. The backend suite was not rerun because
  no backend code changed.
- Ran `graphify update .` after code changes: 810 nodes, 1,798 edges, 45
  communities. The installed uv launcher still needs an escalated invocation
  in this sandbox. Keep using Graphify before code searches as `AGENTS.md`
  requires.

### Next work

1. Have someone unfamiliar with the app try the instant example and live
   path. Check whether the example labeling is unmistakable and whether the
   choice cards make sense without builder narration. The live tag chooser
   was tested; identical-name artist choices still need richer Qloo metadata
   or a clearly bounded no-choice state.
2. Work through the three synthetic briefs in `docs/VALIDATION.md`. Its
   current gap assessment is still accurate: amplified-sound cutoff,
   capacity, all-ages and known fees are not hard constraints, and maker/film
   programming is outside the current artist-led wedge. Do not mark the
   benchmark gate passed from the browser smoke test.
3. Audit the legacy `/api/agent/*` backend and its dependency on `Engine`
   before removing it. The product frontend does not use it, but the same
   engine module currently imports legacy agent/provider classes. Avoid
   a rushed deletion that destabilizes the decision path.
4. Build and smoke-test a judge-accessible deployment once AWS access and
   paid provisioning are resolved. Current saved decisions have no user
   ownership; keep the preview protected. A local license file exists, but
   this checkout has no Git remote and the hosted demo has not been verified.

### Local state

The live chooser check created local decision `dec_0fee574664d0` for
`Tastewell test room`. It is test data, not an operator record. The earlier
`dec_72d06494c44b` contains a clearly synthetic sample outcome. No code
was committed or deployed during this continuation; preserve the working
tree.

## Active checkpoint — comparison page retired (2026-10-28)

### Intent and decision

The user asked whether to remove **Compare Qloo**, because it does not fit
Tastewell's operator workflow, and to update the implementation plan. We
decided to make the venue programming decision workspace the sole product
journey. The 2026-10-28 live browser test justified the change: the main
decision flow returned three Qloo-sourced artist pilots, changed the first
two ranks under a new audience, saved a plan and a clearly synthetic outcome,
and replayed its evidence. The separate comparison page gave no grounded
brief for a listening bar despite three successful Qloo envelopes; a jazz
club run showed tags but left actionable sections blank. The separate page
is a weak demonstration and distracts from the useful decision workflow.

### Done in this continuation

- Removed the public `/compare` Next.js route, its top-bar link, old dual-pane
  app/components/CSS, and the two browser specs dedicated to that page.
  `/` and `/decision` still render `frontend/app/decision/page.tsx`.
- Simplified `frontend/lib/api.ts` to the shared backend base URL; the product
  frontend no longer calls the old `/api/agent/*` endpoints. Those backend
  endpoints and agent internals remain for an explicit dependency audit.
- Updated `docs/PRODUCT_IMPLEMENTATION_PLAN.md` with the one-journey scope,
  live findings, ordered next slice, and corrected stale resume notes.
  Updated `README.md`, `PRODUCT.md`, `DESIGN.md`, and
  `docs/CURRENT_FUNCTIONALITY.md` to match the current product surface.
- Verified `npm run lint` and `npm run build` in `frontend/` passed. The
  production route list contains `/`, `/decision`, and `/_not-found`, with no
  `/compare`. In the live browser, the main navigation link was gone after a
  reload and direct `/compare` returned 404. `git diff --check` returned no
  whitespace errors (only Git's LF-to-CRLF notices).
- Ran `graphify update .` after code edits: 799 nodes, 1,784 edges, 45
  communities. The default sandbox could not launch the installed uv
  trampoline, so the local Graphify update required an escalated run. Do not
  treat dirty graph output as a reason to skip Graphify.

### Next work

1. Keep `/compare` retired. Audit callers and tests of `/api/agent/*`,
   `backend/app/agent/*`, and the legacy brief backend before deleting it;
   preserve anything the decision path actually uses. The backend suite was
   not rerun during this frontend/doc change.
2. Follow the ordered slice in `docs/PRODUCT_IMPLEMENTATION_PLAN.md`:
   an instant clearly synthetic decision example alongside the live path,
   operator-friendly ambiguity choice, three benchmark journeys including
   sparse evidence, keyboard/mobile checks, and a working hosted demo.
3. Prepare a judge-accessible deployment and submission. The current app
   still runs locally; the Compose/Caddy package has not had a Docker build
   or hosted smoke test. Saved decision history has no per-user ownership, so
   do not expose it without access control. Keep public-repo setup, visible
   license, and testing instructions aligned with the actual deployment.
4. Run focused decision browser checks, frontend lint/build, relevant
   backend tests, and `graphify update .` after further code edits. Keep
   real operator outcomes and synthetic examples explicitly distinct.

### Local test data and working tree

The prior live walkthrough saved decision `dec_72d06494c44b` in the local
SQLite database with an outcome whose source explicitly says
`TEST DATA — synthetic example, no actual event`. It also created replay
`dec_f87f380e6ab9`. These are local demo records, not customer evidence.
The working tree contains the comparison removal and documentation changes;
do not reset or discard them. No public deployment or Devpost submission was
made in this continuation.

## 2026-10-28 deployment decision

The user wants AWS. For a first password-protected private preview, the
recommended target is an Ubuntu Lightsail 4 GB instance (AWS lists $24/month)
with a static IP and a domain. `deploy/README.md` now has the AWS steps and
current pricing links. The local Docker daemon is stopped, and an AWS STS
identity check found no usable credentials. No AWS resource has been created
and no hosted smoke test has run. Do not claim public deployment. The user
still needs to provide account access, preferred AWS region/domain, and
approval for paid provisioning. `docs/VALIDATION.md` now records why the
three synthetic benchmarks still fail their gate despite working slices.

## Newest continuation — scenario and cancellable jobs

Additional work after the live job check:

- Added decision JSON export and replay. Replay copies a saved evidence
  snapshot into a new labeled decision, clears the pilot selection/outcome,
  and makes no Qloo call. The backend test verifies identical evidence and
  no extra client calls; the browser test verifies the replay label.
- Prepared `deploy/` with backend/Next.js images, Caddy same-origin routing
  and Basic Auth, Compose volumes for SQLite, and a private-preview smoke
  script. `docker compose config --quiet` passed. The Docker daemon was not
  running, so images and a hosted smoke test remain unverified. The package
  is intentionally a single-password preview; it is not multi-user
  ownership/authentication.
- Latest suite: **87 passed, 2 skipped**; three mocked browser journeys,
  production frontend build, and lint passed. The live Qloo job+scenario
  journey passed before the replay/deploy additions.

- The `/decision` workspace now compares a saved artist shortlist under a
  changed audience or region for one venue. It reruns `rank` with the same
  artist IDs, stores both query contexts and source rows in the SQLite
  decision, and displays ordinal movement without subtracting affinity
  values across calls. The new API is
  `POST /api/decisions/{id}/scenarios`.
- Decision creation and ambiguity resolution now use background jobs with
  stage/elapsed polling and a Cancel button. The backend cancels the task;
  each decision has a 180-second total budget including MCP startup and
  data calls. Existing synchronous endpoints still work. Job status is
  in-memory, while completed decisions remain in SQLite.
- The new scenario journey passed live Qloo browser verification. It kept
  the same two public artist IDs when changing the audience from millennials
  to young professionals. The subsequent live run through the new job API
  passed as well. Exact-name test decisions were removed from SQLite after
  each run. The current backend process was started with the job code.
- The targeted decision API suite passed 15 tests, three mocked Playwright
  journeys passed, and frontend lint/build passed. Run the full backend
  suite and `graphify update .` after further edits.
- `docs/VALIDATION.md` now has cited published proxy evidence from the
  National Restaurant Association and SevenRooms. The user has no operator
  contacts and asked for online research; the interviews, willingness to
  pay, pilot review, and real outcome gate remain unverified.

Next implementation gaps: fixture replay/export, stronger operational hard
constraints and candidate revision, persistence/ownership rules and auth,
evaluation over benchmark decisions, and production deployment. Avoid
claiming Phase 0 buyer validation or product impact from the proxy sources.

## Latest continuation — 2026-10-27

- Verified the artist-shortlist and multi-venue journey live in the browser
  with two public jazz artists and two eligible venues. Qloo returned both
  artist IDs in each venue's `rank` call, and the UI displayed ranks per
  venue. The ambiguous concept tag was selected by a human-facing chooser.
  The one exact-name live test decision was removed from SQLite afterward.
- Added HTTP coverage for artist ambiguity resolution, ID verification, and
  preserving the decision ID. Added a mocked browser journey for the
  shortlist, three-venue constraints, artist chooser, per-venue matrix, and
  pilot selection. Updated the live browser test to exercise the new path.
- Added a per-MCP-session, five-minute cache for identical successful/empty
  requests, with per-key locking, a 128-entry cap, and no caching of errors
  or degraded results. Evidence rows preserve the original retrieval time on
  cache hits. This cache does not persist across decision resolution HTTP
  requests because those create a fresh MCP session.
- Updated `docs/CURRENT_FUNCTIONALITY.md` to describe the current workspace,
  SQLite persistence, local-only access limit, and verification.
- Latest checks: backend **84 passed, 2 skipped**; frontend lint and
  production build passed; two mocked Playwright tests passed; one live Qloo
  Playwright test passed. Graphify was updated to 715 nodes and 1,662 edges;
  the backend was restarted on :8000 after the cache change. Run
  `graphify update .` after any further code edits.

Next: continue the product plan, especially bounded total decision time and
cancellation, fixture replay, stronger constraints and scenario comparison.
The Phase 0 buyer gate still needs real operator interviews; no customer
validation has occurred.

## Active checkpoint — resume the product build here

The user asked to **build the product in `docs/PRODUCT_IMPLEMENTATION_PLAN.md`**
and test Graphify and Qloo properly. They then asked for this handoff because
limits are low. Continue the product build; the work below is a working local
product path, **not the finished plan**. Preserve all uncommitted work.

### What was bduilt in this continuation

- `frontend/app/decision/page.tsx` is a programming-decision workspace linked
  from the legacy brief home page. It accepts a venue concept, audience,
  objective, first venue and additional venues with live-music and budget
  constraints, plus up to five operator-supplied artist names. It displays
  Qloo-backed option cards, the per-venue rank matrix, evidence drawers,
  unknowns, a pilot selection form, saved decisions, and an aggregated
  outcome form. The old dual-pane brief remains at `/`.
- `backend/app/api/decisions.py` defines typed decision, venue, option,
  evidence, plan, and outcome models. The deterministic path resolves a Qloo
  concept tag; asks for a human choice on ambiguity; discovers artists or
  resolves the operator's artist names with `describe`; obtains an optional
  brand suggestion; ranks the **same artist ID set in one call per eligible
  venue**; and constructs up to three distinct pilot formats. Every named
  Qloo candidate on a card has a ledger ID. Artist availability, fee,
  staffing, licensing, attendance, and revenue remain unknown.
- `backend/app/api/engine.py`, `routes.py`, and `decision_store.py` expose
  create, resolve, list, get, select, and outcome routes. Resolving an
  ambiguous candidate updates the same decision ID. SQLite snapshots at
  `backend/data/decisions.sqlite` survive a restart; that directory is
  gitignored. Decision history has **no authentication yet**, so keep this a
  local development product until access control is added.
- `backend/serve.ps1` now prefers `backend/.venv/Scripts/python.exe` and
  discovers the installed Qloo harness at the user's npm global path.
  `frontend/app/layout.tsx` uses a system font stack so builds work offline.
- `docs/VALIDATION.md` holds buyer hypotheses and benchmark decisions.
  `docs/qloo-contract.md` now records the live `rank` probe: three artist
  IDs returned together without `include_tags`; adding the jazz tag as an
  `include_tags` filter returned only one and is unsuitable for a full-set
  comparison.

### Verification performed

- Graphify works when the command has access to its installed uv runtime.
  `graphify query ...` succeeded, and `graphify update .` succeeded after
  edits: **701 nodes, 1,630 edges**. Continue obeying `AGENTS.md`: query
  Graphify before raw code search/read, update after code changes.
- Local Python 3.12 venv at `backend/.venv` was created with `uv`; backend
  dev dependencies installed. Latest full suite: **80 passed, 2 skipped**
  (`backend/.venv/Scripts/python.exe -m pytest -q`).
- Qloo harness reported `Qloo data: ready (environment)` with `.env` loaded.
  Three marked live Qloo tests passed before the final shortlist addition.
  A live MCP `rank` probe and a live `describe("Miles Davis", type="artist")`
  probe succeeded. A real browser run from `/decision` through Qloo evidence
  passed before the artist-shortlist and multi-venue edits. Live test records
  named `Tastewell live test room` were removed from SQLite afterward.
- Latest frontend production build, lint, and mocked Playwright decision
  journey passed after the shortlist and multi-venue edits. The mocked
  browser journey covers tag resolution, evidence, pilot plan, outcome, and
  reopening a saved decision.

### In flight / first next actions

1. **Verify the newest artist-shortlist and multi-venue path live.** The
   backend server at `:8000` was started before the final edits, so restart
   it with `backend/serve.ps1` first. Frontend dev server at `:3000` was
   running at handoff; check listeners. Use an operator-safe public artist
   example, confirm `describe` resolution, full-set `rank` for each venue,
   and a human ambiguity choice. Keep Qloo probes bounded and sequential.
2. Add an HTTP test for **artist** ambiguity resolution (tag resolution is
   already tested), and a browser test for the multi-venue/shortlist form.
   Investigate any live response differences before expanding stages.
3. Update `docs/CURRENT_FUNCTIONALITY.md`: its experimental-path paragraph
   still describes the older one-venue, in-memory slice. Keep plan claims
   aligned with implemented behavior.
4. Continue `docs/PRODUCT_IMPLEMENTATION_PLAN.md` in order. The current
   slice still needs a validated operator shortlist/decision, better hard
   constraints and scenario comparison, run-level MCP caching, bounded total
   time/cancellation, evidence replay, authentication, and a production
   deployment. The geographic map remains optional behind its Qloo semantics
   gate. No operator interviews have occurred, so Phase 0's buyer gate is
   **not** passed; do not claim customer validation or sales impact.

### Operational notes

- The Qloo global `qloo.cmd` is at
  `C:\Users\parsa\AppData\Roaming\npm\qloo.cmd` on this machine. Tool
  invocations under the workspace sandbox could not access it; running the
  command with the existing local credential and required permission worked.
  Never print `.env` or commit credentials. The backend venv uses Python
  3.12.10 and is gitignored.
- With servers already up, mocked browser test:
  `cd frontend; npx playwright test e2e/decision.spec.ts --reporter=line`.
  Starting Playwright's own `webServer` sometimes hung during teardown;
  reusing a separately running `npm run dev` server made the test exit cleanly.
  Live browser test: set `E2E_LIVE=1` and run
  `npx playwright test e2e/decision.live.spec.ts --reporter=line` after
  restarting the backend. It creates a test decision record; remove only
  records with the exact test venue name afterward.
- `git status --short` includes prior uncommitted agent fixes and docs from
  before this continuation. Do not reset or overwrite them. The new SQLite
  DB and local venv are ignored. Run `graphify update .` after future code
  edits, and expect graph output to be rewritten.

---

The remaining sections are earlier handoff history. Use the active checkpoint
above for current implementation status and next actions.

## Start here

The user has set aside the hackathon deadline and wants a substantially
stronger product. **Use [the new product plan](docs/PRODUCT_IMPLEMENTATION_PLAN.md)
as the forward plan** and [current functionality](docs/CURRENT_FUNCTIONALITY.md)
as the code baseline. `docs/qloo-contract.md` records live Qloo behavior.
`IMPLEMENTATION.md` and the older notes below are historical build context;
their deployment-first ordering is no longer the product priority.

Product hypothesis: a hospitality group marketing/experience lead uses
Tastewell repeatedly to choose a programming or partnership pilot across
several venues. The operator supplies real venues, candidate acts/themes/
brands, constraints, and later an aggregated outcome. Tastewell uses Qloo
to discover and assess cultural fit, presents traceable alternatives, and
saves a decision and pilot plan. MapLibre plus self-hosted PMTiles is an
**optional** geographic evidence view, gated on validated Qloo location
semantics. It must not imply foot traffic, sales, or causal impact.

**Next work: Phase 0 of the product plan.** Create a validation pack with
buyer hypotheses, interview guide, three realistic benchmark decisions,
quality rubric, and Qloo probe matrix. Work on the pack and safe contract
probes independently; the gate for advancing to the decision engine needs
feedback from real operators. Once the first decision is confirmed, build
Phases 1–2 as a narrow vertical slice before redesigning the UI.

Phase 0 progress (2026-10-27): `docs/VALIDATION.md` now contains the buyer
hypotheses, interview guide, three synthetic benchmark decisions, scoring
rubric, probe matrix, and record template. Its examples and thresholds are
explicit assumptions pending operator feedback. No new Qloo contract claim
has been made: `qloo` was unavailable on this shell's PATH when the bounded
probes were attempted, and Graphify's installed launcher failed before a
query could run (`uv trampoline failed to canonicalize script path`). No code
was changed. The five interviews, buyer gate, and three live probes remain.

Experimental product slice (2026-10-27): `/decision` now exercises a typed,
deterministic Qloo evidence path and records an operator's pilot choice in
memory. See `docs/CURRENT_FUNCTIONALITY.md` for exact scope and limitations.
Seven focused backend `unittest` checks pass; frontend lint, TypeScript,
and production build pass. The full pytest suite could not run in this shell
(`py -3.12` finds no installed Python; the available Python lacks pytest).
The frontend now uses a system font stack so builds do not depend on fetching
Google Fonts. `graphify update .`
was attempted after code changes and failed with the same uv trampoline
error. No live Qloo calls or operator interviews have been completed for this
slice, so the Phase 0 gate is still open.

Before editing code, read `AGENTS.md`. It requires querying the local
Graphify index before searching or reading source for codebase questions.
`graphify-out/graph.json` exists (code-only AST map: 492 nodes, 1,236 edges);
for example, run `graphify query "brief flow Qloo evidence" --budget 1800`.
The full `graphify .` semantic scan was rejected by automatic approval
review because it would upload repository docs/images to Gemini. The safe
local map was built with `graphify . --code-only`. After code changes, use
`graphify update .` per `AGENTS.md`.

Check `git status` before work and preserve all existing changes; the tree
currently includes uncommitted agent fixes, docs, `LICENSE`, `README.md`,
and Graphify install files. Servers were restarted on 2026-10-27 at backend
:8000 and frontend :3000, but verify listeners before relying on them.
The latest backend suite passed 69 tests with one live test skipped; the
frontend lint passed. A live grounded taco-shop run completed after the
empty-final repair was added, though that run did not exercise the repair.

## Historical hackathon handoff

The following notes describe the deadline-driven plan and prior live runs.
They remain useful for operations and regressions, but P5 deployment is not
the next product-design phase.

## Current session update (2026-10-27)

- Product planning: `docs/CURRENT_FUNCTIONALITY.md` records implemented
  behavior and limits; `docs/PRODUCT_IMPLEMENTATION_PLAN.md` proposes a
  venue decision workspace with phased gates. The revised buyer hypothesis
  is a multi-venue hospitality group making recurring programming and
  partnership decisions. The plan includes real operator pilots, optional
  MapLibre/PMTiles geographic evidence, saved decisions, and an outcome loop.
  It supersedes this handoff's old deployment-first priority when choosing
  new feature work. Graphify's
  local code-only index was used for navigation (492 nodes, 1,236 edges);
  full doc/image semantic indexing was blocked by auto-review.
- Root `LICENSE` (MIT) and `README.md` added for the submission package. The
  README documents the current local product, Qloo evidence flow, setup,
  limitations, and honest hosting status. Public deployment/repo remain open.
- User-run taco preset failed after both Qloo recommendations returned `ok`:
  backend logged "final reply not parseable as JSON brief" and returned
  `exit=aborted`. This is the intermittent 20b final-response issue, not
  Qloo readiness or a tool failure. The agent now retries an empty/invalid
  final up to twice with tools disabled, using existing Qloo evidence; it
  records content length and model `finish_reason` on each failure. It still
  aborts honestly if the repair attempts fail. Backend tests: 69 passed,
  1 live skipped. Backend restarted with this fix.
- One live grounded taco-shop/Austin/young-families rerun finished `ok` in
  4 LLM steps with 19 trace events (run `2026-10-27T121118-0095f2`). This
  rerun did not require the repair path; the intermittent case remains to
  be observed live when it next occurs.
- The grounded pane's apparent stall was traced to Qloo MCP startup before
  `run_started`, matching the timed run below. It now emits
  `connecting_qloo_mcp` immediately and displays "connecting to Qloo…";
  readiness has a 90-second timeout that ends the run with an error if the
  connection truly stalls. `readiness_ok` displays "Qloo connected".
- Frontend lint passed for the readiness UI change.
- Keep `openai/gpt-oss-20b` on OpenRouter for the demo. The provider already
  has bounded 429/5xx retries. OpenRouter free models are limited to 50/day
  and 20/minute unless at least $10 of credits have been purchased, which
  raises the daily cap to 1,000. The user confirms the account has purchased
  $10 of credits, so the 1,000/day cap applies. Failed free requests count.
  The user also reports that gpt-oss-20b sometimes returns an empty reply;
  capture the response shape/finish reason on the next reproduction before
  changing models or retry behavior.
- Verify the connection event and empty-final recovery in future live runs;
  the historical P5 deployment phase is not the next product-design phase.

## 0. Where we are

| Phase | Status |
|---|---|
| P0-P3 | done |
| P4 Next.js UI | done |
| P4.1 presets 3 -> 9 | done, live-verified (`d76aeda`) |
| P4.2 Groq 413 fix | done, live-verified (`ae9a644`) |
| P4.3 minimal tool chain | done, live-verified (`dbc8a79`) |
| P4.4 OpenRouter provider | done, live-verified (`6f6d58d`) |
| P5 deploy | NEXT - `deploy/` still does not exist |
| P6 submission | due Oct 29 internal / Oct 30 11:45pm EDT hard |

Tests: **67 mocked backend green** (`py -3.12 -m pytest -q` in backend; 1 live
skipped). Frontend lint/build/3 smoke green (unchanged since P4.1).

## 1. Current LLM config (verified working this session)

- Provider switched to **OpenRouter** (`P4.4`, commit `6f6d58d`): provider
  registry entry, settings/engine/cli key wiring, `serve.ps1` now respects
  `LLM_PROVIDER`/`LLM_MODEL` from `.env` (defaults to groq only when unset).
- `.env` (local, gitignored) now has:
  - `LLM_PROVIDER=openrouter`
  - `LLM_MODEL=openai/gpt-oss-20b`
  - `OPENROUTER_API_KEY` present; account limit $1, usage at session end
    **$0.007303178**.
- OpenRouter is OpenAI-compatible: base_url `https://openrouter.ai/api/v1`,
  no Groq 8k per-request TPM wall. `reasoning_effort=low` passthrough works
  (gpt-oss family).
- Measured cost: **$0.000303 per full double-run** (~0.03 cents; key usage
  delta) => $1 buys ~3,300 double-runs, $0.50 ~1,650.
- Price table (verified live 2026-10-27 via `openrouter.ai/api/v1/models`,
  $/1M in-out, all tool-capable): gpt-oss-20b 0.018/0.09; mistral-nemo
  0.029/0.03 (weak tools); ling-3.0-flash 0.021/0.063; qwen3.7-flash
  0.03/0.13; deepseek-v4-flash-0731 0.044/0.133; mistral-small-3.2-24b
  0.075/0.20; gemini-2.5-flash-lite 0.10/0.40; gpt-oss-120b 0.15/0.60.
  Free `:free` models exist but are rate-limited - dev only, not demo day.
- Switching models = edit `LLM_MODEL` in `.env` and restart backend.

## 2. Last live run (2026-10-27, OpenRouter gpt-oss-20b, jazz club preset)

Preset: `jazz club` / `Harlem, Manhattan` / `young women` via
`live_drive_preset.py` (timed, polled).

- Generic (noQ) pane: **8.8s**, exit=ok, 5 events.
- Grounded pane: **66.3s**, 18 events, exit=ok, **all sections present**
  (audience_profile, menu_tilt, music_programming, adjacent_brands,
  tag_themes), honest_absences empty, no needs_input.
- **The "stuck" was not a hang:** the grounded pane emitted ZERO trace
  events for ~28-29s while it was still in Qloo MCP readiness (harness spawn
  + capabilities) BEFORE `run_started`; then events flowed 3 -> 18 and it
  finished OK. The generic pane had already completed in that window, which
  made the grounded pane look dead. This is pre-agent MCP startup latency,
  not the LLM. UI improvement idea: emit a "connecting Qloo MCP" status
  event before the readiness call so the trace is never silent (small loop/
  engine change, do before P5 if demo-day UX matters).
- gpt-oss-20b followed the 2-tool chain (find_tags + recommend artist +
  recommend brand) and produced a complete cited brief. Deep quality review
  not done; A/B against gpt-oss-120b is one env line + restart.

## 3. Presets (done, verified - do not re-probe)

`frontend/app/components/BriefForm.tsx` PRESETS (short chips):
1. Wine bar / natural wine bar / Brooklyn / millennials
2. Tacos / taco shop / Austin, Texas / young families
3. Listening bar / listening bar / Williamsburg / young professionals
4. Coffee / specialty coffee shop / Silver Lake, Los Angeles / gen z
5. Izakaya / izakaya / East Village, Manhattan / young professionals
6. Jazz club / jazz club / Harlem, Manhattan / young women
7. Craft beer / craft beer hall / Denver, Colorado / men 25-34
8. Bubble tea / bubble tea shop / Monterey Park, California / gen z
9. Record store / vinyl record store / Bushwick, New York / gen z

Demographic rule (live-verified, in `docs/qloo-contract.md`): SAFE =
millennials, young professionals, gen z, young women, men 25-34, young
families. DEAD-END (needs_input, zero candidates -> section omitted) =
families, parents, college students, couples, tourists. All 12 candidate
venue concepts resolve. Do not add presets with dead-end audiences.

## 4. Fixes that matter (do not regress)

1. **Groq 413 was a hard per-request >8k-token cap** (not a wait). Fixed by
   capping model-facing `description` prose at 120 chars + history-shrink
   retry in `provider._shrink_levels`. Kept even though OpenRouter removes
   the wall (protects any provider swap).
2. **Tool detours**: LLM tools are ONLY `find_tags` + `recommend`;
   prompt demands exactly one artist + one brand recommend, then final.
   This took a run from 143s/6 envelopes/music-dropped to 38s/3 envelopes/
   all sections on Groq.
3. **Dead-end family ban + tag-URN guard** (`c05305b`): zero-candidate
   needs_input bans the tool for the run; `urn:tag:*` rejected in
   entity-only args.

## 5. Quirks/lessons (still true)

- **PS 5.1 + Unicode = footgun.** Round-tripping source files through
  `Get-Content|Set-Content` mangles UTF-8 (a JS regex ellipsis became `???`
  and crashed Node). Use editor tools for source; keep .ps1 ASCII-only.
- `py -3.12` buffers stdout without a TTY - always `py -3.12 -u`.
- py.exe launcher pid != owner pid - assert restarts via uvicorn log text.
- Playwright mocks: `*` does not cross `/`; register `**/api/agent/run/**`
  and `**/api/agent/runs/**` separately. Real-browser scripts in %TEMP%
  must require playwright by absolute path from `frontend/node_modules`.
- React-compiler lint: no setState in effect body, no ref/Date.now() reads
  during render. Clocks: parent handler -> prop -> interval setState.
- `qloo exec` on PS 5.1: always `--input-file`, never inline `--input`.
- Probe hygiene: sequential, 2s spacing, never loop.
- OpenRouter key usage can be checked with
  `GET https://openrouter.ai/api/v1/key` (Bearer) - use it to prove which
  provider a run actually used and to measure cost.

## 6. Next steps, in order

1. Optional but cheap: emit a pre-readiness "connecting Qloo MCP" trace
   event so the first ~30s is never silent (fixes the exact confusion that
   ended this session). Then one timed re-run.
2. Optional: A/B `openai/gpt-oss-120b` vs `20b` for brief quality (env line
   + restart). 20b already produced all sections; 120b is safer for demo.
3. **P5 deploy** (biggest hackathon-readiness gap): `deploy/` with
   Dockerfile.backend, Dockerfile.frontend, docker-compose.yml, Caddyfile,
   smoke_test.sh (AWS t3.micro; plan B Fly.io; IMPLEMENTATION.md §6). Wire
   frontend `API_BASE` to the public origin.
4. Lighthouse a11y >= 95 on the production build.
5. P6 package: MIT LICENSE, README per kit SUBMISSION.md, public repo,
   Devpost submission (draft in IMPLEMENTATION.md §8) by Oct 29.

## 7. Working session env (end state)

- Backend: :8000 running, configured for OpenRouter +
  `openai/gpt-oss-20b`. Restart ONLY via `backend\serve.ps1`.
- Frontend: :3000 running via `npm run dev` from `frontend/`.
- Stop: kill the :8000 python pid and :3000 node pid from
  `Get-NetTCPConnection -LocalPort <port> -State Listen`.
- Qloo key: hackathon host, unchanged. Qloo MCP readiness spawn can take
  ~5-30s (source of the silent-start issue above).
- Playwright chromium 1248 installed; demo driver
  `%TEMP%\opencode\demo_shot2.cjs`; timed API driver
  `%TEMP%\opencode\live_drive_preset.py` (args: brief, region, audience).
