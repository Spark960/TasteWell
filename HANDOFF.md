# HANDOFF - fresh session (2026-10-27, session ended by user)

> Start here. `IMPLEMENTATION.md` remains the deep source of truth.
> Tree is clean as of commit `6f6d58d` except this handoff edit.
> **Servers were left RUNNING at session end (backend :8000 on OpenRouter,
> frontend :3000). Verify before assuming.**

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

- Backend: :8000 running via `backend\serve.ps1`, OpenRouter +
  `openai/gpt-oss-20b`, health 200. Restart ONLY via that script.
- Frontend: dev server on :3000 (hot reload). Open http://localhost:3000.
- Stop: kill the :8000 python pid and :3000 node pid from
  `Get-NetTCPConnection -LocalPort <port> -State Listen`.
- Qloo key: hackathon host, unchanged. Qloo MCP readiness spawn can take
  ~5-30s (source of the silent-start issue above).
- Playwright chromium 1248 installed; demo driver
  `%TEMP%\opencode\demo_shot2.cjs`; timed API driver
  `%TEMP%\opencode\live_drive_preset.py` (args: brief, region, audience).
