# Tastewell — Implementation Plan & Knowledge Base

**Project:** Tastewell — a Qloo-grounded venue & hospitality taste agent (Qloo Agentic Hackathon, Devpost).
**One-liner:** An agent that tells restaurants/venues what their catchment area and target audience actually like — menu tilt, music/programming, brand direction — grounded in Qloo's taste graph, with a built-in "grounded vs. ungrounded" side-by-side demo.
**Repo owner:** Local git only for now; GitHub remote added later (public + MIT license required by rules).
**Hackathon manager contact:** `ian@qloo.com` (private things only — e.g. leaked key).

---

## 0. Snapshot — resume here first

> If you are returning to this project after a break, read this section, then
> find the **lowest-numbered phase whose checklist is not fully checked** and
> run its "Resume context → next command".

| Phase | What it is | Status | Gate |
|---|---|---|---|
| P0 | Harness spike: install, env vars, first probes, record contract | ✅ done 2026-10-21 | every planned Qloo call verified live |
| P1 | Integration layer: Python wrapper around `qloo exec` + status normalizer | ✅ done 2026-10-21 | mock tests green (22) + live adapter call ok |
| P2 | Agent loop: FastAPI ↔ `qloo mcp` stdio, tools, grounding contract, abstain policy, CLI test runner | ☐ | one brief → full concept via CLI |
| P3 | HTTP layer: FastAPI endpoints + SSE trace + Qloo-off toggle | ☐ | curl-able end to end |
| P4 | Next.js UI: brief form, side-by-side, trace panel, disambiguation picker | ☐ | demoable locally |
| P5 | Deploy: EC2 t3.micro + Docker Compose + Caddy + DuckDNS TLS | ☐ | public URL, HTTPS, external smoke test |
| P6 | Submission package: README, LICENSE, Devpost description, presets | ☐ | **submit by Oct 29** |
| P7 | Buffer | ☐ | hard deadline Oct 30 11:45pm EDT |

**How to keep this doc accurate while working:** never leave a session without
updating (a) the Status column, (b) the phase's Resume Context block, (c) any
newly learned Qloo fact → `docs/qloo-contract.md`.

---

## 1. Decisions log (locked — don't relitigate)

| # | Decision | Rationale |
|---|---|---|
| D1 | Project name: **Tastewell** | chosen; rename later is cheap (package names + README) |
| D2 | B2B: **venue/hospitality concept agent** | JCal judges a startup pitch; B2B fits; last year's winner was B2B |
| D3 | Stack: **Next.js frontend + FastAPI backend**, Docker Compose | boring infra, exciting output; sponsor supports backend-on-VM pattern |
| D4 | LLM: **Google Gemini Flash (free tier)** behind an OpenAI-compatible provider interface | free tier suits unknown judge traffic, no card needed; `LLM_PROVIDER` env swaps to OpenAI/Groq in one line if tool-calling quality disappoints (then: GPT-4.1-mini ≈ good price/quality; Groq free = emergency fallback) |
| D5 | Qloo access: **through the harness only** (`qloo exec`, `qloo mcp`) | email: "We support qloo exec and qloo mcp at the event" — explore/plan/build modes and raw-key REST bypass are out |
| D6 | Deploy: **AWS EC2 t3.micro**, us-east-1, Docker Compose (frontend + backend + Caddy) | user has $100 credits/90d ≈ $25–30 total cost; no sleep (Render-style PaaS explicitly rejected by user); sponsor bans serverless for the MCP route |
| D7 | TLS domain: **DuckDNS free subdomain** (no domain owned) | free, works with Caddy/Let's Encrypt |
| D8 | Plan B deploy: **Fly.io VM(s)** if AWS setup eats >4h | pre-written runbook in §6.4; Vercel backend is dead (serverless unsupported) |
| D9 | Demo differentiator: **"Grounded / Ungrounded" side-by-side toggle** + live tool-call trace | converts the core requirement ("would not work without Qloo") into a one-click judge experience |
| D10 | Grounding honesty: 6-status envelope mapping; abstain/`needs_input` never hallucinate; **aggregate framing only** ("groups tend to like, not one person") | sponsor telegraphed both as scoring/ethics points |
| D11 | Local git; GitHub repo created/uploaded by user at P6 | submission requires a public repo then |
| D12 | Tag/entity disambiguation is a **headline feature**, not plumbing | "All five results are named Jazz but differ in type — picking the one you mean is your first real decision with Qloo data" |

---

## 2. Rules of record (from the kit + kickoff email — verified 2026-10)

### 2.1 Environment & credential
- Node.js **22.19.0+**; global harness: `npm install --global @qloo/qloo-harness` (min version **0.1.26** — verify with `qloo --version`).
- Hackathon keys ONLY work against the hackathon host. Before `qloo setup --qloo`, set in shell profile (and in deploy container env):
  ```sh
  export QLOO_BASE_URL=https://hackathon.api.qloo.com
  export QLOO_TRUSTED_BASE_URL=https://hackathon.api.qloo.com
  ```
- `qloo setup --qloo` → paste key (input hidden). Check: `qloo setup --status` → must show **"Qloo data: ready"**. Ignore Model/Chat lines (our route never needs harness model sign-in).
- On servers: set `QLOO_API_KEY` env var instead of interactive setup; **stdio MCP subprocess must be spawned with `env: process.env`** or the key won't forward (Python: pass `env=dict(os.environ)`).
- Key rules: never in web pages, mobile bundles, repos, screenshots, chat, or MCP client configs shared publicly. No `qloo api --api-key` (shell history leak).
- Status escalation ladder: `qloo setup --status --json` → `qloo doctor` (→ `--network` only for a bounded deliberate probe) → Discord `#qloo-hackathon` (https://discord.gg/rF9PKsD5Q7) → `ian@qloo.com` (private/leaked key only). Always report *redacted error category + time*, never the key.

### 2.2 Supported surfaces & compliance
- **Supported at the event:** `qloo exec`, `qloo mcp`. NOT supported: harness `explore`, `plan`, `build` modes. Don't ship anything that depends on them.
- The harness CLI route (`qloo exec`) and MCP route (`qloo mcp`) expose the same validated workflows and identical result shapes — prototype in exec, ship in mcp (our fast path for dev).
- Qloo results are **aggregate tastes**: no personal data (names, emails, device IDs, account IDs, location histories) may be sent to Qloo; no claims about an individual's behavior. Product copy must say "groups in this segment/area tend to like…".
- A search/tag match is **a candidate, not proof of meaning** — never pass an uncertain tag downstream; show candidates to the user (this is our `needs_input` UI flow).
- If a search yields nothing → report "no result"; never fake-fallback to invented entities.

### 2.3 The nine workflows (`qloo exec <workflow>` — verify exact names via `qloo exec --help` in P0)
| Workflow | What it does | Tastewell use |
|---|---|---|
| find_tags | concept → candidate Qloo tags (e.g. "jazz" → 5 similarly-named tags of different types) | resolve vibe/genre words from brief |
| describe | entity/tags → description + entity tags | characterize concept seeds |
| recommend | signals (entities/tags) + target_type → recommendations | playlist/artist + brand + programming per taste |
| rank | options + option_type + signals/demographic → scored shortlist | rank candidate program items for the audience |
| where_popular | entity + within → where it's popular | pick venue neighborhood / catchment check |
| compare_audiences | group_a vs group_b → differences | "how locals differ from the audience profile" |
| audience_demographics | audience → demographic affinities | audience profile rendering |
| entity_tags | entity → its tags | build taste profile from seed entities |
| trends | entity_type + 1–5 entities + date range | "is this concept rising?" credibility check (**live P0: `entity_type:"place"` → `QLOO_CONTRACT` non-retryable error — use artist/brand/locality, not place**) |

### 2.4 MCP tool surface (`qloo mcp`; tool names `qloo_*`)
- Chain shape (canonical, from kit): `qloo_find_tags`/`qloo_describe` → **confirm with user** → `qloo_recommend` / `qloo_rank` / `qloo_where_popular` / `qloo_compare_audiences`.
- Readiness check without a Qloo call: `qloo_capabilities`.
- **Result envelope (every tool):** `{ status, summary, results, result_count, error? }` with six statuses:
  - `ok` → use results
  - `empty` → no match: refine input, tell the user
  - `needs_input` → ambiguous: **show candidates, ask the user** (drives our disambiguation UI)
  - `partial` → some results; read `summary`
  - `degraded` → results with reduced quality/fallback; read `summary`
  - `error` → `error.code` (e.g. `QLOO_AUTH`), `error.retryable` (retry ONLY when true), `error.recovery`
- Desktop MCP note (dev machine): if a client can't start `qloo`, put the full path from `where.exe qloo` (Windows) / `command -v qloo` in `command`.
- Browser **cannot** start `qloo mcp`; serverless is unsupported. Backend on VM/container: Node 22.19+, harness installed, `QLOO_API_KEY`/base-URL vars as secrets.

### 2.5 Submission & judging (from qloo-hackathon-kit `docs/SUBMISSION.md`)
Required in submission:
1. short problem statement; 2. Qloo workflows/MCP tools used + why they fit; 3. redacted request→result explanation incl. entity/tag choices; 4. demo/screenshots with no credential or personal data; 5. setup steps a stranger can run from a clean environment; 6. known limitations (incl. what Qloo results do NOT establish).
Judging criteria surfaced so far: **usefulness · technical execution · provenance and user clarity · responsible data handling · reproducibility.**
Rules of the Devpost listing: live hosted demo (no local-only), public repo with all source + instructions, **open-source license file visible in repo About**, text description.
**Hard deadline: Oct 30, 2026, 11:45pm EDT** (= Oct 31 9:15am GMT+5:30). Internal target: submit **Oct 29**.
Prizes: $15k/$6k/$4k + separate **$25k JCal investment** for his favorite → pitch must read like a company: wedge, buyer, why now.

### 2.6 Demo-brief constraints (so a judge's 2 minutes convert)
- No signup wall, no key entry, first result happens on the **first click** (preset briefs).
- Provenance chips on every recommendation (workflow/tool + envelope status + raw request witness) → provenance + user-clarity scoring.
- Standing footer: *"Aggregate cultural affinity data — describes group tendencies, not individual behavior."*

---

## 3. Architecture

```
[Next.js UI :3000]
   │  brief → /api/agent/stream (SSE)
   ▼
[FastAPI :8000]
   ├─ Agent loop (LLM tool-calling; Gemini Flash via OpenAI-compat shim)
   ├─ QlooAdapter — either:
   │    • subprocess `qloo exec <workflow>` (dev + non-model paths), or
   │    • stdio MCP client → `qloo mcp` (the shipped agent path)
   │  normalizes 6-status envelope → {data, evidence[], next: choose|abstain}
   ├─ Provider shim: gemini | openai | groq (env `LLM_PROVIDER`)
   └─ trace bus → SSE stream (tool, args, request witness, envelope status)
```

- Frontend never sees any key; backend holds all secrets.
- Same brief runs twice in demo mode: with grounded tools vs. prompt-only (Qloo-off) → side-by-side.
- Every claim in output must trace to an envelope `results` entry; ungrounded sentence = flagged in gray, or removed.

### File map (target end-state)
```
qloo/
├─ IMPLEMENTATION.md            ← this file (living doc)
├─ README.md                    ← final product readme (P6)
├─ LICENSE                      ← MIT (P6; must be visible in GitHub About)
├─ .env / .env.example          ← secrets (see §4)
├─ docs/
│  ├─ qloo-contract.md          ← live-verified endpoint/workflow shapes (P0)
├─ probe/                       ← throwaway probe scripts (P0)
├─ backend/
│  ├─ pyproject.toml / requirements.txt
│  ├─ app/
│  │  ├─ main.py                (FastAPI)
│  │  ├─ settings.py            (env parsing)
│  │  ├─ qloo/adapter.py        (exec wrapper + normalizer)
│  │  ├─ qloo/mcp_client.py     (stdio MCP, P2)
│  │  ├─ agent/loop.py, agent/tools.py, agent/provider.py
│  │  ├─ api/routes.py, api/stream.py (SSE)
│  │  └─ trace.py
│  └─ tests/ (+ fixtures/)
├─ frontend/                    (Next.js app; brief form / side-by-side / trace panel)
└─ deploy/
   ├─ Dockerfile.backend  (node:22-slim base + global harness + FastAPI)
   ├─ Dockerfile.frontend
   ├─ docker-compose.yml  (backend + frontend + caddy)
   ├─ Caddyfile
   └─ smoke_test.sh
```

---

## 4. Secrets & env schema

`.env` (gitignored — real values) mirrors `.env.example` (committed):

```ini
# Qloo hackathon credential — NEVER commit real values
QLOO_API_KEY=
QLOO_BASE_URL=https://hackathon.api.qloo.com
QLOO_TRUSTED_BASE_URL=https://hackathon.api.qloo.com

# Agent brain (Gemini Flash free tier; OpenAI-compatible swap interface)
LLM_PROVIDER=gemini
GEMINI_API_KEY=
OPENAI_API_KEY=

# App
APP_ENV=dev
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Deploy (P5)
ACME_EMAIL=
DUCKDNS_DOMAIN=
```

Forbidden patterns (lint-worthy): `NEXT_PUBLIC_QLOO*`, key in any `const`, key in logs/traces. Traces must redact headers.

---

## 5. Phases

> Format per phase: **Purpose → Tasks → Verify (checklist) → Resume context → Escalate**.
> Escalate (every phase): blocked >2h → Discord `#qloo-hackathon`; credential/quota issues → `qloo setup --status --json` then `ian@qloo.com` (redacted).

---

### P0 — Harness spike (Oct 16–17)

**Deliverable:** working harness on dev machine; every Tastewell-critical workflow executed live; `docs/qloo-contract.md` filled from real responses.

**State needed before starting:** `QLOO_API_KEY` and Node 22.19+.

Tasks:
1. `node --version` ≥ 22.19.0; else install LTS from nodejs.org.
2. `npm install --global @qloo/qloo-harness` → `qloo --version` ≥ 0.1.26.
3. Set permanently in PowerShell profile (`$PROFILE`):
   `$env:QLOO_BASE_URL="https://hackathon.api.qloo.com"` and `$env:QLOO_TRUSTED_BASE_URL="https://hackathon.api.qloo.com"` (persist via profile, not session-only).
4. `qloo setup --qloo` (paste key from `QLOO_API_KEY` line in `.env`), then `qloo setup --status` → expect **"Qloo data: ready"**.
5. `qloo exec --help` → record exact workflow names/flags into `docs/qloo-contract.md`.
6. Run probes from `probe/` (thin cmd shims that capture stdout JSON):
   - `find_tags` with `"jazz"` (the kit's canonical case) → note the 5 types
   - `find_tags` with `"natural wine"`, `"tacos"`, `"listening bar"` (Tastewell concepts)
   - `describe` on one resolved entity/tag id
   - `recommend` with entity signal + target_type
   - `rank` with 3 options + signals
   - `where_popular` with entity + region
   - `compare_audiences` two groups
   - `audience_demographics`, `entity_tags`, `trends` once each
7. Record per-workflow: input schema, sample raw JSON output, envelope when a query should be empty (e.g. deliberately obscure concept), error JSON on empty `--input` (safe, no key effect), and rate-limit/429 behavior if JSON mentions it.

Verify checklist:
- [x] `qloo --version` ≥ 0.1.26 (harness 0.1.26 on Node v22.23.2; winget-upgraded from 22.17.1)
- [x] `qloo setup --status` shows "Qloo data: ready" (via `QLOO_API_KEY` env var — "ready (environment)"; interactive setup needs a TTY so the env-var route from §2.1 is the working path on dev too; nothing stored to harness config; re-load key from `.env` per session)
- [x] All 9 workflows executed live at least once; outputs saved under `probe/out/`
- [x] `docs/qloo-contract.md` has input+output shapes per workflow; §2.3 names verified — no rename drift; trends/place limitation noted
- [x] One empty-result case captured (find_tags `semantic:false` → `ok`, result_count:0)

Resume context:
- Done: probes for all 9 workflows live (2026-10-21); 21 raw JSONs in probe/out/ (gitignored); contract doc filled; run scripts probe/run-probes.ps1 + probe/run-resolved.ps1 committed; .gitignore covers probe/inputs/.
- Learned: PS 5.1 breaks inline `--input` JSON through the npm qloo.ps1 shim → always `--input-file`. `needs_input` = name ambiguity → candidates with UUIDs → re-call with UUID works (canonical disambiguation chain, drives D12). QLOO_AUTH is checked before input schema (empty-input error needs key set). compare_audiences: results is one object (tags[], a, b, matchEntities), no result_count. audience_demographics values are signed affinities. trends: works for artist; place rejected (QLOO_CONTRACT). Exactly-empty only via `semantic:false` (semantic search fuzzes to 10 hits).
- In flight: none — P0 complete.
- Next: P1 phase, next command `# scaffold backend/ (P1 tasks 1–2): pyproject + settings`, then `cd backend && pytest -m "not live" -s`
- Session env note: PowerShell $PROFILE sets QLOO_BASE_URL/QLOO_TRUSTED_BASE_URL permanently; the API key must be loaded from .env into `$env:QLOO_API_KEY` before any qloo call in a fresh session (see probe/run-probes.ps1 lines 4–8 for the pattern).
---

### P1 — Integration layer (Oct 17–19)

**Deliverable:** `backend/app/qloo/adapter.py` — `run_workflow(name, payload) -> NormalizedResult` executed via `qloo exec` subprocess with bounded retries; envelope-normalized; mocked tests from P0 fixtures.

Tasks:
1. Scaffold `backend/` (Python 3.12, `pyproject.toml`, pytest, httpx not needed yet).
2. `settings.py`: pydantic-settings reading §4 env schema; fail fast if `QLOO_API_KEY` missing in non-dev env.
3. Adapter: build temp input file (or stdin if supported by workflow CLI — verify via `qloo exec --help`), run `qloo exec <workflow> --input-file <tmp> --json`, parse envelope, map the 6 statuses to internal `{ok|empty|needs_input|partial|degraded|error}` dataclass with `error.retryable` semantics (bounded: max 2 retries, exponential backoff, only when retryable).
4. In-proc LRU response cache (key = workflow + payload hash; TTL ~10 min) — quota hygiene per kit docs.
5. Redact anything resembling the key from logs/traces; structlog or plain logging with filter.
6. Tests: fixtures from `probe/out/` JSONs; success, needs_input, empty, degraded, error-retryable-retry, error-nonretryable-abstain; subprocess failure/timeout simulation.

Verify checklist:
- [x] `pytest` green (mocked; no key needed) — 22 passed, 0.5s
- [x] Integration test (marked live, skipped without env): one real `find_tags` through adapter returns normalized data (`QLOO_LIVE=1` + key in env → passed)
- [x] `.env` never touched in test runs for mocked tests (settings test chdirs to tmp_path)

Resume context:
- Done: `backend/` scaffolded (Python 3.12, pyproject, pytest-timeout); `app/settings.py` (pydantic-settings, §4 schema, fail-fast on missing key in non-dev); `app/qloo/normalizer.py` (envelope→`NormalizedResult`; handles no-`status` error envelopes, needs_input candidates extraction, compare_audiences single-object results wrap, trends `series[]` as `.data`); `app/qloo/adapter.py` (`qloo exec --input-file` subprocess runner, LRU+TTL cache keyed workflow+payload-hash, ≤2 exponential-backoff retries only when `error.retryable`/transport-failure, injectable runner/sleep/clock); `app/qloo/redact.py` (registered-secret + bearer/key-ish scrubbing); tests in `tests/test_adapter.py` + 12 fixture JSONs copied from probe/out into `tests/fixtures/` (committed, UTF-8).
- Learned (this session): (1) bare `python` on PATH is actually another project's venv (`alpaca26`) — use **`py -3.12`** (system 3.12.10; had no pip, bootstrapped via `ensurepip`); (2) that stale venv's pip has a broken TLS path (SSL EOF on pypi even though curl works) — venv deleted, install deps with `py -3.12 -m pip install`; (3) PS 5.1 `>` redirection writes **UTF-16 LE BOM** — all probe/out JSONs were UTF-16 (why the earlier "binary file" read); fixtures were re-encoded to UTF-8 in `tests/fixtures/`; (4) bare `qloo` fails in subprocess (`WinError 2`, npm shim) → `resolve_qloo_bin()` uses `shutil.which` (`qloo.cmd` runs fine); (5) missing `QLOO_BASE_URL`/`QLOO_TRUSTED_BASE_URL` (they're in `$PROFILE`, not session env) gives misleading `QLOO_AUTH` — adapter now injects them into the subprocess env via `setdefault`.
- In flight: none — P1 complete.
- Next: P2, next command `cd backend && py -3.12 -m pip install mcp fastapi uvicorn && python -m app.agent.cli "listening bar" --region "Williamsburg" --audience millennials` (CLI runner to be built first)
- Env note for any shell running qloo/adapter: `$env:QLOO_API_KEY = ((Get-Content ..\.env) -match '^QLOO_API_KEY=' | Select-Object -First 1).Substring('QLOO_API_KEY='.Length).Trim()` (probe runners do this at lines 4–8; adapter injects base URLs itself).
---

### P2 — Agent loop via `qloo mcp` (Oct 19–22)

**Deliverable:** CLI runner (`backend/app/agent/cli.py`) taking a venue brief → full concept brief, grounded exclusively in MCP tool results, with trace log saved to disk.

Tasks:
1. Spawn `qloo mcp` via Python `mcp` package stdio client; **pass `env=dict(os.environ)`** (documented failure mode otherwise: `QLOO_AUTH` on exit).
2. `qloo_capabilities` readiness check on startup (no Qloo call).
3. Tool surface (adapt to live list of tools): `qloo_find_tags`, `qloo_describe`, `qloo_entity_tags`, `qloo_recommend`, `qloo_rank`, `qloo_where_popular`, `qloo_compare_audiences`, `qloo_audience_demographics`, `qloo_trends`.
4. Agent loop (provider shim from D4): system prompt enforces (a) aggregate framing ("people in this segment/area tend to like…" — never individual claims, never causal, never "will buy"), (b) every taste claim must cite the tool result ids it came from, (c) `needs_input` → stop and surface candidates, (d) `empty`/`degraded` → favorable-honest language, abstain from that section.
5. Concept brief output schema: `{audience_profile, menu_tilt[], music_programming[], adjacent_brands[], tag_themes[], evidence[] (tool,status,summary,ids,ts)}`.
6. Qloo-off mode flag: same brief, grounded tools removed, so P3 can produce the side-by-side.
7. CLI test: `python -m app.agent.cli "natural wine bar" --audience millennials --region Brooklyn` → concept brief + `trace.json` saved.

Verify checklist:
- [ ] Readiness check passes without Qloo call
- [ ] One full brief end-to-end via CLI, all claims traceable to evidence ids
- [ ] `needs_input` path exercised (feed an ambiguous seed, e.g. "jazz" tag choice) and the CLI asks/consumes a user choice
- [ ] Qloo-off run completes and is obviously generic (sanity for the differentiator)
- [ ] Trace file contains timestamps, workflows, envelope statuses

Resume context:
- Done: —
- In flight: —
- Next command: `cd backend && python -m app.agent.cli "listening bar" --region "Williamsburg" --audience millennials`
---

### P3 — HTTP layer (Oct 22–24)

**Deliverable:** FastAPI app exposing the agent: run + SSE trace + Qloo-off toggle; CORS for local frontend.

Tasks:
1. `POST /api/agent/run` (payload: brief, audience, region, creations/seeds, mode=grounded|generics) and `GET /api/agent/stream/{run_id}` SSE.
2. Trace messages: `{type: tool_call|tool_result|status|brief_delta|final, ...}` with redaction filter (headers/keys).
3. Reuse P1 cache; add simple in-memory run registry.
4. Health: `GET /api/health` (no Qloo call), `GET /api/qloo/status` → wraps `qloo_capabilities`.
5. curl + `httpx` tests: run→stream→final shape; Qloo-off parity; SSE disconnect resilience.

Verify checklist:
- [ ] `pytest` incl. live-marked smoke green
- [ ] SSE streamed run visible in curl (`curl -N localhost:8000/api/agent/stream/<id>`)
- [ ] `uvicorn app.main:app --reload` + two POSTs (grounded, generic) both complete

Resume context:
- Done: —
- In flight: —
- Next command: `cd backend && uvicorn app.main:app --reload --port 8000`
---

### P4 — Next.js UI (Oct 24–26)

**Deliverable:** single-page app: brief form (concept, audience, region, preset chips), side-by-side result panes, live trace panel, disambiguation picker (needs_input), aggregate-disclaimer footer.

Tasks:
1. Create Next.js app (App Router, TS, Tailwind): `npx create-next-app@latest frontend --ts --app --tailwind`.
2. Layout: left = Brief form + **preset chips** ("Natural wine bar · millennials · Brooklyn", "Taco shop · families · Texas") to guarantee one-click first demo; right = two panes — **Grounded** (default) & **Ungrounded**; bottom = collapsible trace timeline with status chips (ok/empty/needs_input/partial/degraded/error color-coded).
3. `needs_input` → inline picker with candidate candidates from the envelope; chosen id re-drives the run.
4. Provenance: each recommendation chip shows `<workflow> · <status>` tooltip with the envelope summary (rubric: provenance & clarity).
5. Disclaimer footer + copy review passing the aggregate-framing lint list from §2.3/§5-P2.
6. Loading/half-product states: dirty-loading per pane; empty-result pane says "No grounded result — request was honest about it".
7. Next.js module layout Test: Playwright smoke — preset click on the first preset trace (grounded + ungrounded panes render; trace has ≥1 tool_result; `empty` state renders).

Verify checklist:
- [ ] `pnpm build` green; `pnpm e2e:smoke` green locally
- [ ] Lighthouse a11y ≥ 95 + no key in client bundle (grep `NEXT_PUBLIC` for forbidden)
- [ ] Full local demo works: `docker compose up` or dev servers: FastAPI :8000 + Next dev :3000

Resume context:
- Done: —
- In flight: —
- Next command: `cd frontend && pnpm dev`
---

### P5 — Deploy (Oct 26–28)

**Deliverable:** public HTTPS URL (DuckDNS), full stack up as services, external smoke test round-trips. Full runbook in §6.

Verify checklist:
- [ ] `http://<duckdns>.duckdns.org` and HTTPS both serve the UI
- [ ] `deploy/smoke_test.sh` passes from a phone/other network
- [ ] `docker compose ps` all healthy after 12h unattended
- [ ] Cost check in AWS billing console ≤ $15 cumulative by end of phase

Resume context:
- Done: —
- In flight: —
- Next command: `ssh tfaster@ec2-host "docker compose -f /opt/tastewell/docker-compose.yml ps"`
---

### P6 — Submission package (Oct 28–29)

**Deliverable:** submitted-ready repo + Devpost submission.

Tasks:
1. Public GitHub repo (user creates; core files: source, README, **MIT LICENSE**, `.env.example` only).
2. README per kit SUBMISSION.md: problem → Tastewell workflows/tools + why → redacted request→result explanation → screenshots (no credentials/personal data) → clean-env setup (clone, `cp .env.example .env`, keys, docker compose) → known limitations (incl. "aggregate tastes do not establish individual behavior") → JCal-facing pitch paragraph (wedge/buyer/why-now).
3. `docs/qloo-contract.md` already live-checked; verify final.
4. Preset chip tuning + final spot-check of disclaimers and license: `LICENSE` file at root About; verify `setup` steps work on a fresh VM per §6.1.
5. Devpost form: description text → §8; include live URL + repo URL + license notice + confirmation About section shows license.
6. Submit **before Oct 29 11:59pm EDT**; screenshot receipt.

Verify checklist:
- [ ] Submission in Devpost with all 6 kit-required items
- [ ] README shows all 6 (self-audit against §2.5)
- [ ] Repo: public, all source, **.env NOT present**, LICENSE, About shows license
- [ ] Live URL works in incognito from another device
- [ ] No secrets anywhere: `git log -p` spot-check; screenshots replayed
- [ ] Fresh-clone setup script works on a clean machine

Resume context:
- Done: —
- In flight: —
- Next command: `git remote add origin <repo-url> && git push -u origin main`
---

### P7 — Buffer (Oct 29–30)

- Spillover; final Devpost edits; if quota/credential wobble near deadline: escalate early (SMTP/timezone differences — deadline **Oct 30 11:45pm EDT**, attend to IST +0900!).
- Do NOT self-host anything new in P7.
- Verify zero-regression: one post-deadline live URL check per day.

---

## 6. Deployment runbook (details for P5; do not execute before P0 passes)

### 6.1 AWS EC2 t3.micro, us-east-1 — concrete steps
1. AWS console → IAM user (programmatic access). Budget alert at $10/$50.
2. Security group: inbound 80,443 from 0.0.0.0/0; SSH 22 from your IP only.
3. t3.micro (1 vCPU/1GB; fine for demo; a burst credit exists for brief t2 bursts), Ubuntu 22/24, key pair.
4. Elastic IP (stable address; free while attached). DNS: DuckDNS A record → EIP.
5. SSH in:
   ```bash
   sudo apt-get update && sudo apt-get install -y ca-certificates curl git docker.io docker-compose-plugin
   sudo usermod -aG docker $USER   # relogin
   sudo systemctl enable --now docker
   git clone https://github.com/<you>/tastewell.git /opt/tastewell
   cd /opt/tastewell && ./deploy/bootstrap.sh   # creates .env from .env.example; you paste secrets
   docker compose up -d
   ```

### 6.2 Images
- **backend**: `node:22-slim` base (harness needs Node 22.19+; Qloo subprocess needs the CLI on PATH) + global `@qloo/qloo-harness` + pip layer for FastAPI. Boot check: `qloo --version && qloo setup --status` (env-based auth: QLOO_API_KEY/BASE_URL/TRUSTED_BASE_URL provided by compose). If harness can't be installed as root global → install to `/app/bin` and prepend PATH in entrypoint.
- **frontend**: standard node build → `next start` (no serverless).
- **caddy**: official caddy:2 with ACME e-mail env; reverse proxy `/api/*` → backend, `/*` → frontend; automatic TLS for DuckDNS domain.*
- Compose secrets: `.env` produced only on the server; never committed; CI impossible before P6 (public repo replaces).

### 6.3 DuckDNS
1. duckdns.org subdomain → point at EC2 Elastic IP.
2.地带 Caddyfile email = `ACME_EMAIL` (Let's Encrypt ToT; 80/443 must be open before first request).
3. Verify DNS propagation before firing: `nslookup <sub>.duckdns.org`.

### 6.4 Plan B — Fly.io (if AWS burns >4h of P5 window)
- `fly launch` × 2 apps (backend, frontend) with static machines (no serverless); `fly secrets set QLOO_API_KEY=... QLOO_BASE_URL=... QLOO_TRUSTED_BASE_URL=... GEMINI_API_KEY=...`; Dockerfile same; TLS automatic.
- Ceiling: ~$5–8/mo; kill = ship has no back door for serverless rule — Fly = full VM, allowed.

### 6.5 Smoke test (`deploy/smoke_test.sh`, run from anything off-host)
```bash
#!/usr/bin/env bash
set -euo pipefail
T=${TASTEWELL_URL:-https://yourname.duckdns.org}
curl -fsS "$T/api/health" | grep -q ok || { echo FAIL-HEALTH; exit 1; }
curl -fsS "$T/" | grep -qi "<!DOCTYPE html" || { echo FAIL-FRONTEND; exit 1; }
RUN_ID=$(curl -fsS -X POST "$T/api/agent/run" -H 'Content-Type: application/json' \
  -d '{"brief":"listening bar","region":"Austin","audience":"millennials","mode":"grounded"}' | jq -r .run_id)
timeout 90 curl -fsSN "$T/api/agent/stream/$RUN_ID" | grep -q '"type":"final"' || { echo FAIL-AGENT; exit 1; }
echo SMOKE-PASS
```

### 6.6 90-day cost ledger (budget sanity)
| item | monthly |
|---|---|
| t3.micro + 8GB gp3 EBS | ~$8.5 |
| IP/data egress | ~$1 |
| total 3 mo | ~$28–30 | → well inside $100 credit; only if you extend beyond credit expiry 90d does it become real ~$10/mo.

---

## 7. Submission checklist (P6 gate — kit SUBMISSION.md mapped)

- [ ] ① short problem statement (operators guess what their area likes…)
- [ ] ② Workflows/MCP tools used + why: find_tags→describe→confirm→recommend/rank/where_popular→compare_audiences; provenance envelope; abstain
- [ ] ③ Redacted request→result explanation incl. entity/tag decisions (e.g. our jazz-type lesson)
- [ ] ④ Demo/screenshots with zero credential/personal data
- [ ] ⑤ Clean-env setup (clone → env → keys → compose) tested fresh
- [ ] ⑥ Known limitations: aggregate tastes; envelope-degraded honesty; region coverage limits; LLM cost; DuckDNS tier constraints
- [ ] Judge-rubric bullets mirrored in README top (usefulness / technical execution / provenance+clarity / responsible data handling / reproducibility)
- [ ] License file at repo root, listed in GitHub About
- [ ] Devpost: live URL + repo URL + description (§8)

---

## 8. Devpost description (draft, polish at P6)

> **Tastewell** — an agent with actual taste of *a place*.
> Restaurant & venue operators open concepts that fail because "what our target customer loves" is written by a generic LLM's guesswork. Tastewell asks Qloo instead: given a location + audience, the agent resolves real taste anchors (entities, tags, brands), runs Qloo's audience/location/affinity workflows (`qloo mcp` tools with provenance envelopes), and produces a concrete venue brief — menu tilt, music/programming, adjacent brands — every line traceable to a Qloo result. Flip the **Grounded/Ungrounded** toggle and watch the same brief degrade into vibes.
> Aggregate honesty by design: results say what *groups in a place tend to like*, never what an individual will do; ambiguous tag matches surface a candidate picker (Qloo's "five Jazzes" problem, made a feature); empty results stay honestly empty.
> Qloo is load-bearing, not decoration: without the taste graph, the product is a generic LLM in a suit.

---

## 9. Timeline gates (recap)

| Date (2026) | Gate |
|---|---|
| Oct 16–17 | P0 probes green (key-dependent) |
| Oct 19 | P1 integration layer green |
| Oct 22 | P2 CLI brief works |
| Oct 24 | P3 HTTP green |
| Oct 26 | P4 UI demo locally |
| Oct 28 | P5 public HTTPS + smoke pass |
| **Oct 29** | **P6 SUBMIT** |
| Oct 30 11:45pm EDT | organizational hard deadline |

---

## 10. Operating notes (memorize-while-working)

- **Never** commit keys; `git add` checks in flights: `git status` before every commit while `.env` exists early.
- Anything private/knowledge-worthy goes to this file or docs/, never to chat-only memory.
- If the harness CLI flag names in §2.3 drift from reality, **trust the CLI** and update this file + `docs/qloo-contract.md` in the same commit.
- Windows dev machine quirk: PATH for subprocess → if backend can't find `qloo` in tests, capture from `where.exe qloo` and set `QLOO_BIN` env fallback in settings. (`resolve_qloo_bin()` in `backend/app/qloo/adapter.py` now does this automatically via `shutil.which`.)
- Dev-machine Python hygiene (P1 finding): bare `python` on PATH is a stale venv from an unrelated project with a broken pip TLS path. Always use `py -3.12` here. Never `pip install` into a foreign venv.
- PS 5.1 `>` and `Out-File` default to UTF-16 LE BOM: any captured probe JSON through them needs re-encoding to UTF-8 (fixtures in backend/tests/fixtures are already UTF-8; prefer `-Encoding utf8` or Set-Content over raw `>`).
- Quota hygiene: batch small; always reuse cache; never rapid-loop workflows for fun.
