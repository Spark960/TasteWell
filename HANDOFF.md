# HANDOFF - fresh session (2026-10-22 midday, session ended leaving)

> Start with this file. `IMPLEMENTATION.md` remains the deep source of truth
> (decisions log, phases, runbook 6, operating notes 10). This bridge captures
> the 2026-10-22 midday session state + exactly what to do next.
> **Servers: all KILLED (no changes this session). Tree: clean as of the
> final commit except nothing pending.**

## 0. Where we are

| Phase | Status |
|---|---|
| P0 harness probes | done |
| P1 adapter layer | done |
| P2 MCP agent loop + CLI | done |
| P3 FastAPI + SSE HTTP layer | done |
| P4 Next.js UI | committed (`d29d12b`, `384b408`); hardening committed (`c05305b`, this session) |
| **P4.1 preset expansion** | **IN PROGRESS - this session's active task (see section 2)** |
| P5 deploy | next - `deploy/` still does not exist |
| P6 submission | deadline Oct 29 internal, hard Oct 30 11:45pm EDT |

## 1. What happened this session (2026-10-22 midday)

1. **Committed all pending backend hardening as `c05305b`** (the previous
   handoff flagged it as uncommitted): zero-candidate dead-end now bans the
   tool FAMILY for the whole run; `urn:tag:*` URNs are rejected before they
   reach entity-only args (probe-verified they always return zero-candidate
   needs_input and loop the model); `qloo_capabilities` + 5 unused tools
   trimmed from LLM specs into `DEFAULT_LLM_TOOLS` (token budget: Groq 8k
   TPM); transient QLOO_DNS/QLOO_TIMEOUT/QLOO_NETWORK retried even when
   envelope says retryable=false. +4 tests. **63 mocked tests green**
   (`py -3.12 -m pytest -q` in backend: 63 passed, 1 skipped live).
2. **Verified the live run this morning performed as designed** (user-pasted
   trace): grounded run 05:46:44 -> 05:47:43 = ~59s, 23 trace events, 3 Qloo
   envelopes, exit=ok; ungrounded pane still intentionally fake + honest
   disclaimer. The hardening is working; no further loop fixes needed.
3. **Preset expansion started** (user complaint: "very limited selection,
   only 3 options" -> the 3 chips in `BriefForm.tsx`). Quota-safe tag probing
   done (direct `qloo exec` harness calls, no LLM steps). Implementation NOT
   started - that is exactly where the session stopped.

## 2. ACTIVE TASK: presets 3 -> 9 (verified data - do not re-probe)

### Verified via `qloo exec find_tags` (semantic, all `[ok]`, 10 results each)
Specialty coffee | Jazz club | Ramen | Barbecue | Craft beer | Izakaya |
Vegan | Bubble tea | Speakeasy | Record store | Hot pot | Baked goods.
=> Any of these can be a preset venue concept.

### Verified via `qloo exec recommend` (signal_tags=[urn:tag:genre:music:jazz], limit 5)
DEMOS THAT ARE SAFE (ok, 5 rows):
- `gen z` @ `Silver Lake, Los Angeles` (first: Dam-Funk)
- `young families` @ `Austin, Texas` (first: NoName)
- `young women` @ `Harlem, Manhattan` (first: H.E.R.)
- `men 25-34` @ `Denver, Colorado` (first: Vulfpeck)

DEMOS THAT DEAD-END (needs_input, implementation must NOT use):
`families` | `parents` | `college students` | `couples` | `tourists`.
(Verified independent of location: families failed @ Queens AND @ Austin.)
**The existing taco preset's audience `families` is UNSAFE - it must become
`young families`.**

### Planned final catalog (place into `frontend/app/components/BriefForm.tsx` PRESETS)
1. Natural wine bar / millennials / Brooklyn, New York      [all verified]
2. Taco shop / young families / Austin, Texas               [verified today]
3. Listening bar / young professionals / Williamsburg       [live-verified]
4. Specialty coffee / gen z / Silver Lake, Los Angeles      [verified today]
5. Izakaya / young professionals / East Village, Manhattan  [audience verified LIVE (Williamsburg); exact location pair NOT probed]
6. Jazz club / young women / Harlem, Manhattan              [verified today]
7. Craft beer / men 25-34 / Denver, Colorado                [verified today]
8. Bubble tea / gen z / Monterey Park, California           [pair NOT probed]
9. Record store / gen z / Bushwick, New York                [pair NOT probed]

### Remaining steps, in order
1. ONE probe round for the 3 unproven pairs (2s spacing, ~1 min):
   recommend(signal_tags=[urn:tag:genre:music:jazz], target_type=artist,
   limit=5) for: gen z + `Monterey Park, California`; gen z + `Bushwick, New York`;
   young professionals + `East Village, Manhattan`. Swap in probed-safe
   locations (Silver Lake / Denver / Harlem / Williamsburg) for any that
   needs_input. Reusable probe scripts: `%TEMP%\opencode\preset_demo_probe.ps1`
   and `preset_demo_probe2.ps1` (edit the `Probe` list; keep ASCII-only).
2. Edit `BriefForm.tsx` PRESETS with the catalog above. UI change: chips
   should use SHORT venue-only labels ("Wine bar", "Tacos", "Listening bar",
   "Coffee", "Izakaya", "Jazz club", "Craft beer", "Bubble tea", "Record
   store") - full combined labels wrap badly in the 300px sidebar (one chip
   ~= one row); the full combination is visible in the three inputs after
   click. Keep the existing chip style/classes.
3. `npm run lint`, `npm run build`, `npm run e2e:smoke` in `frontend/`
   (react-compiler lint rules apply - see quirks). Playwright smoke mocks
   `**/api/agent/runs/**`; preset count changes should not touch tests, but
   verify.
4. Persist today's demographic findings into `docs/qloo-contract.md`
   (safe/unsafe free-text demographic list; note the demographic-word
   needs_input failure mode and zero-candidate needs_input = dead-end).
   Also note `young families`,
   `men 25-34`, `young women`, `gen z` verified live 2026-10-22.
5. Then ONE live browser run of 2-3 new presets via `backend\serve.ps1` +
   `npm run dev` (each grounded double-run costs ~11k TPD of ~200k; budget
   is fine). Confirm every section populated, no dead-end omissions.

## 3. State of the two sides (unchanged this session)

- Frontend `frontend/`: Next 16.4.2 App Router, TS, Tailwind 4. Key files:
  `app/TastewellApp.tsx` (two-pane driver + re-drive on pick),
  `app/components/BriefForm.tsx` (PRESETS - the file being edited),
  `components/ResultPane.tsx`, `components/TracePanel.tsx`, `lib/api.ts`
  (SSE stream ends at `run_done`).
- Backend `backend/`: FastAPI :8000 + SQLite run registry + agent loop;
  restart ONLY via `backend\serve.ps1` (kills :8000 first, asserts bind).
  Provider: `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`.

## 4. Known root cause of old slow runs (condensed)

Groq free tier = 8k TPM rolling + ~200k TPD; a drilled TPD 429-chains past
the 600s wall. Plus a silent-restart trap (plain Start-Process cannot bind
:8000 while the old process lives, health still answers 200 -> stale app).
Both are handled now (fresh key account + reasoning_effort=low + serve.ps1).
Full detail: IMPLEMENTATION.md runbook.

## 5. Quirks/lessons (still true - do not relearn)

- **PS 5.1 + UTF-8 = footgun.** Non-ASCII (em-dash) in a .ps1 gets
  misdecoded and EXECUTED as garbage - keep .ps1 ASCII-only. Write source
  files via editor tools, never PS cmdlets.
- **`py -3.12 script.py` buffers stdout without a TTY** - always `py -3.12 -u`.
- **py.exe launcher pid != owner pid** - assert restarts via uvicorn log
  content, never pids.
- **Playwright mocks:** glob `*` does not cross `/` - register
  `**/api/agent/run/**` AND `**/api/agent/runs/**` separately.
- **React-compiler lint:** no setState in effect body, no ref/Date.now()
  reads during render; clocks must be parent-handler -> prop -> interval.
- **PS 5.1 npm shims mangle inline --input JSON** - always `--input-file`.
- Quota hygiene: sequential, 2s spacing; never loop probes.
- Live demographic probes (recommend) DID behave independently of location:
  demographic WORD is what failed, so verified words are portable.

## 6. Next steps after P4.1 (unchanged plan)

1. P5 deploy: `deploy/` (Dockerfiles, compose, Caddyfile, smoke_test.sh,
   bootstrap.sh) - AWS t3.micro, plan B Fly.io (IMPLEMENTATION.md 6.x).
2. Lighthouse a11y >= 95 check (open).
3. P6 package: MIT LICENSE, README per kit SUBMISSION.md, public repo,
   Devpost by Oct 29.
4. Optional demo polish ideas surfaced but NOT implemented: URL params for
   shareable preset links (init state from useSearchParams, Suspense
   boundary needed), a shuffle/"surprise" button over the catalog, a
   grounded-vs-generic verdict strip. Do not let these block P5/P6.

## 7. Working session env (end state)

- **Servers KILLED at session end.** Backend up: from repo root
  `powershell -ExecutionPolicy Bypass -File backend\serve.ps1`, then
  `Invoke-WebRequest http://localhost:8000/api/health` + tail
  `%TEMP%\opencode\uvicorn.err.log` for `Uvicorn running`. Frontend up:
  `npm run dev` in `frontend/`.
- Full live smoke: GET /api/health, GET /api/qloo/status (zero cost), then
  `py -3.12 -u %TEMP%\opencode\live_drive.py` or the browser preset click.
- Probe scratch: `%TEMP%\opencode\preset_tag_probe.ps1` (12 find_tags),
  `preset_demo_probe.ps1`, `preset_demo_probe2.ps1`; last full envelope at
  `%TEMP%\opencode\presets_probe\in.json` + `students_full.json`
  (college-students needs_input shape).
- Provider: new-account Groq key (TPD fresh-ish; ~1 live double-run burned
  ~11-15k this morning + ~33 direct harness probes, no LLM steps - quota is
  safe). `gemini-3.8-flash` fallback resets ~07:30 UTC.
- Playwright chromium installed (1248).
