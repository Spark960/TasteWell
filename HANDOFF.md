# HANDOFF - for a fresh session (2026-10-21 evening)

> Start with `IMPLEMENTATION.md` (source of truth: decisions log, phases,
> runbook  6, operating notes  10). This file is the session bridge: current
> state + what changed in the last working session + exactly what to do next.
> **Session-end state: ALL servers deliberately killed (see  7). Uncommitted
> work in BOTH frontend and backend - commit it as your first action.**

## 0. Where we are

| Phase | Status |
|---|---|
| P0 harness probes | done |
| P1 adapter layer | done |
| P2 MCP agent loop + CLI | done |
| P3 FastAPI + SSE HTTP layer | done |
| **P4 Next.js UI** | **code complete** (this evening's UX fixes below, uncommitted) |
| P5 deploy (EC2/Docker/Caddy/DuckDNS) | next - `deploy/` dir doesn't exist yet |
| P6 submission package | deadline Oct 29 (internal), hard Oct 30 11:45pm EDT |

Repo: local git only; commits exist for P0..P3. P4 work and everything below
is still uncommitted. **First action next session: commit.**

## 1. What Tastewell is (1-para refresher)

B2B venue/hospitality concept agent for the Qloo agentic hackathon. Operator
gives concept + area + audience -> agent resolves real taste anchors via Qloo
MCP tools (only route allowed by hackathon rules) -> grounded concept brief
(menu tilt, music programming, adjacent brands, tag themes) with per-claim
citations and a 6-status honest envelope (abstain, never invent). The UI runs
the SAME brief twice - grounded vs Qloo-off - side by side, so judges see the
differentiator in one click. Aggregate framing only, disambiguation picker is
a headline feature (Qloo's "five Jazzes" problem made a feature).

## 2. Frontend - `frontend/` (all this evening's additions uncommitted)

- Next 16.4.2 (App Router, TS, Tailwind 4, npm) + mocked-Playwright smoke.
- Files (evening's UX-fix batch):
  - `lib/api.ts` streamRun - **ends SSE consumption right at `run_done`**
    (reader.cancel + return) so a run flips to done/needs_input instantly
    instead of lingering "running until the server closes".
  - `app/components/TracePanel.tsx` - auto-opens once ANY events exist
    (manual toggle overrides via userOpen); every row tagged with pane pill
    `Q+` (grounded) / `noQ` (ungrounded) + legend, so a `run_done` row can't
    be misread as the other pane finishing; compact `LiveTrace` component
    (auto-scrolling, last 14 rows) exported.
  - `app/components/ResultPane.tsx` - takes `events` prop, renders LiveTrace
    INSIDE the pane while starting/running (skeleton only pre-events).
  - `app/TastewellApp.tsx` - main column order now Grounded result ->
    Live trace panel -> Ungrounded box; grid rows `1.5fr / 0.8fr / 0.8fr`.
  - `e2e/smoke.spec.ts` - trace-panel test skips the toggle click when the
    panel is already auto-open.
- Run commands unchanged: `npm run dev` :3000 / `npm run build` / `npm run
  lint` / `npm run e2e:smoke` (lint+build+3 smoke tests verified green).

## 3. Backend (all tonight's edits uncommitted; 58 mocked tests pass)

- `app/agent/loop.py` - logs `llm_started` (step, mode, tools) BEFORE
  provider.chat so the trace shows movement during slow LLM waits.
- `app/agent/provider.py`:
  - `_MAX_429_RETRIES=3`, `_MAX_429_WAIT=240` (waits capped at 240s, sized
    for minute-scale rolling quota windows; never one step = whole deadline).
  - `max_tokens` default 16384 -> 4096; `reasoning_effort="low"` for
    gpt-oss* models only (cuts completion tokens 192 -> 64 on step 1 and
    wall-clock latency).
- `app/api/engine.py` - summary() now reports terminal `exit_status`
  ("done"/"error") when the outcome is absent after a crash/timeout kill;
  pollers no longer see a dead run as "running" forever.
- `tests/test_provider.py` - 429-budget test updated (initial + 3 retries).
- `backend/serve.ps1` (NEW) - THE restart script (see  5/ 7): kills the
  existing :8000 listener first, parses repo .env into the same
  shell, launches uvicorn hidden, asserts the fresh log reports a
  successful bind. **Pure-ASCII constraint: PS 5.1 misdecodes non-ASCII
  (em-dash) in .ps1 and executes garbage - keep this file ASCII-only.**

## 4. ROOT CAUSE of the slow runs (fully diagnosed with probes - trust this)

Layered: provider quota + a silent-restart trap.

1. **Provider capacity, measured:**
   - Groq free tier on this key family: `gpt-oss-120b` = **8k tokens/min
     (TPM) and a rolling ~200k tokens/day (TPD)**. The original account hit
     `Used 197659 / Limit 200000` -> EVERY grounded call 429'd with
     retry-after ~207s; 3 retries x <=240s can span past the 600s run wall
     so runs froze ~10 min then died at the deadline. Generic runs are
     prompt-only (~1-2k tokens) and always squeaked through in 2-6s.
   - One grounded step = ~2.8k input tokens (system 510 + user + LIVE tool
     specs 2550 chars; tool-spec payload measured directly from the MCP
     harness). Same request OUTSIDE the app returned 200 in 1.0-1.3s with
     tool_calls on the fresh key - the LLM endpoint itself is healthy.
   - `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `llama-4-scout` all
     **404 (not available on this key)**; `gemini-3.8-flash` = 429 (RPD
     drained; resets ~07:30 UTC); `OPENAI_API_KEY` exists but EMPTY.
   - User swapped to a NEW Groq account late in the session (fresh TPD).
   - Probe scripts live in `%TEMP%\opencode\`: `model_limits.py`,
     `probe_tools.py` (exact grounded step-1 request), `live_drive.py`
     (full double-run with polling), `groq_probe.py`. Rerun with
     `py -3.12 -u` (unbuffered!) - see quirk below.
2. **The silent-restart trap (the real wolf):** plain `Start-Process`
   "restarts" that skip killing the :8000 listener FAIL with
   Errno 10048 (bind) - but health keeps 200 because the OLD process keeps
   serving. That night, two "restarts" no-oped silently, so a live drive and
   parts of the probe session ran against a backend on the OLD drained key
   with workflow/code older than assumed. Evidence: `[Errno 10048]` line in
   `uvicorn.err.log`. **Rule from now on: restart ONLY via
   `backend\serve.ps1`** (kills first, asserts bind in the log). Also: the
   checked message may print "(launcher pid != owner pid)" EXPECTEDLY -
   py.exe (launcher) vs python3.12.exe (child owns the port).
3. Not-a-cause (verified): client SSE handling, pane wiring, 600s wall -
   those behave; the 206s/600s stalls were 429 wait-chains on a drained key.

## 5. Quirks/lessons (don't relearn these)

- **PS 5.1 + UTF-8 = footgun.** Same as before, now with two new heads:
  (a) non-ASCII chars (em-dash) in a .ps1 get misdecoded and the line is
  EXECUTED as garbage (happened in serve.ps1 - keep scripts ASCII-only);
  (b) writing source files must go through editor tools, never PS cmdlets.
- **`py -3.12 script.py` buffers stdout when no TTY** - a long polling loop
  prints NOTHING to the captured shell until exit. Always `py -3.12 -u`.
- **py.exe launcher pid != actual python pid** (child process owns the
  port). Never compare port-owner vs launcher pid; assert via log content.
- **Playwright wire mocks:** glob `*` does NOT cross `/` - `**/api/agent/run*`
  matches POST run but never `/api/agent/runs/<id>`; register
  `**/api/agent/runs/**` separately. Strict mode breaks `.or(...)` - use
  `expect(cb).toPass()` polling.
- **React-compiler lint rules**: no setState in effect body, no ref reads /
  Date.now() during render. Clocks: parent captures `Date.now()` in the
  handler -> prop -> child ticks via `setInterval` setState.
- Backend process env: Start-Process inherits the current shell - env
  parsing + Start-Process MUST be in the same bash call (now packed into
  `backend\serve.ps1`).
- Trapped earlier, still true: `_proc.Started` etc. irrelevant; uvicorn MUST
  have stderr redirected or diagnostics like 10048 vanish forever.

## 6. Next steps, in order

0. **Commit everything** (frontend + backend, likely 2 commits) - the tree
   is green-verified where tested: backend 58 mocked pass; frontend
   lint/build/3-smoke pass. Live end-to-end re-verify is step 2.
1. **One verified live end-to-end drive** (quota budget is fresh today):
   `powershell -ExecutionPolicy Bypass -File backend\serve.ps1` ->
   expect `Uvicorn running` in `%TEMP%\opencode\uvicorn.err.log` ->
   `py -3.12 -u %TEMP%\opencode\live_drive.py` -> expect grounded DONE in
   well under 2 min now (fresh key + reasoning_effort=low + fast probe).
   Then browser: `npm run dev` in frontend and run a preset, hard-refresh
   first. If grounded still stalls >60s at llm_started, rerun
   `probe_tools.py` to recheck quota/latency.
2. P5 deploy when UI is verified: `deploy/` per previous plan (Dockerfiles,
   compose, Caddyfile, smoke_test.sh, bootstrap.sh; AWS t3.micro  6.1 /
   plan B Fly.io  6.4 in IMPLEMENTATION.md).
3. Lighthouse a11y >=95 check (still open).
4. P6 package: MIT LICENSE, README per kit SUBMISSION.md, public repo,
   Devpost by Oct 29.

## 7. Working session env (end state)

- **All servers KILLED deliberately at session end** (:8000 python and
  :3000 node, verified ports clear; no uvicorn strays).
- Frontend: bring up with `npm run dev` in `frontend/` (log to dev.log if
  hidden).
- Backend: bring up ONLY with
  `powershell -ExecutionPolicy Bypass -File backend\serve.ps1` (from repo
  root), then verify: `Invoke-WebRequest http://localhost:8000/api/health`
  and tail `%TEMP%\opencode\uvicorn.err.log` for `Uvicorn running`.
- Provider: `LLM_PROVIDER=groq` + `LLM_MODEL=openai/gpt-oss-120b` (svc env
  in `backend\serve.ps1`); Groq key = new account as of this evening.
  Remember gemini resets ~07:30 UTC if you need a fallback (small
  `gemini-3.8-flash` RPD).
- Playwright browsers installed (chromium 1248).
- Live smoke = `GET /api/health`, `GET /api/qloo/status` (zero data cost),
  then the preset click in the browser or `live_drive.py` for the full
  double-run.
