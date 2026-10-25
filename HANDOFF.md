# HANDOFF - fresh session (2026-10-25)

> Start with this file. `IMPLEMENTATION.md` is the deep source of truth
> (decisions log, phases, runbook §6, operating notes §10). This bridge is
> the session state + next steps.
> **Tree: clean, everything committed. Servers are UP (see §7) - the user
> asked to see the demo, do not assume they were killed.**

## 0. Where we are

| Phase | Status |
|---|---|
| P0 harness probes | done |
| P1 adapter layer | done |
| P2 MCP agent loop + CLI | done |
| P3 FastAPI + SSE HTTP layer | done |
| P4 Next.js UI | done (`d29d12b`, `384b408`, `c05305b`) |
| P4.1 presets 3 -> 9 | done + live-verified (`d76aeda`) |
| P4.2 Groq 413 fix | done + live-verified (`ae9a644`) |
| P4.3 minimal tool chain | done + live-verified (`dbc8a79`) |
| P5 deploy | NEXT - `deploy/` does not exist yet |
| P6 submission | deadline Oct 29 internal, hard Oct 30 11:45pm EDT |

Commits this session: `c05305b` (loop hardening) -> `5c6d720` (handoff)
-> `d76aeda` (presets 9 + contract demographics) -> `ae9a644` (413 fix)
-> `dbc8a79` (tool-chain trim). Tests: **66 mocked backend green**
(`py -3.12 -m pytest -q` in backend; 1 live skipped), frontend
lint + build + 3 Playwright smoke green.

## 1. Live verification done this session (trust these numbers)

- **craft beer** (Denver / men 25-34): 109s, 18 events, exit=ok, all brief
  sections grounded (menu=cuisine tags, artists + brands with entity ids).
- **record store** (Bushwick / gen z): FAILED before the 413 fix (final step,
  "Requested 8088 tokens, limit 8000"); AFTER fix: 55s, 18 events, ok.
- **coffee** (Silver Lake / gen z): 143s + 6 envelopes + music section
  dropped (model detours via describe/where_popular/extra recommends) BEFORE
  the tool trim. After trim: 51s, 2 envelopes, ALL 5 sections, zero absences.
- **jazz club** (Harlem / young women), browser demo after trim: **38s wall,
  3 Qloo envelopes, 23 events, sections: menu/music/brands/tags + audience
  profile, no absences**; grounded artists H.E.R. + SZA, brands Glossier /
  CUUP, honest tag themes. Ungrounded pane finished in ~5s with its designed
  "no Qloo data" note.
- Screenshots: `%TEMP%\opencode\demo_shots2\{01_selected,02_running_10s,
  05_final}.png` (Playwright demo driver: `%TEMP%\opencode\demo_shot2.cjs`).

## 2. The three fixes that mattered (do not regress)

1. **Groq free tier hard-rejects ANY single request >8k tokens with HTTP
   413** - deterministic, not a 429 wait; it killed a final step at
   "Requested 8088". Guard rails now:
   - `tools._cap_texts` truncates model-facing `description` prose to 120
     chars (URN/ids untouched; evidence + UI keep full text).
   - `provider._shrink_levels` 413 recovery: collapse older -> all tool rows
     to envelope summaries, then drop tool schemas; retried inline.
2. **Tool detours**: LLM tool surface is now ONLY `find_tags` +
   `recommend` (`DEFAULT_LLM_TOOLS`); prompt rule 2 demands exactly one
   artist + one brand recommend, then final. Each extra step costs a whole
   TPM window on free tier. `qloo_describe`/`qloo_where_popular` remain
   available over MCP but are not exposed to the model (no section needs
   them).
3. **Dead-end family ban + tag-URN guard** (previous session, `c05305b`):
   zero-candidate needs_input bans the tool for the rest of the run;
   `urn:tag:*` in entity-only args is rejected pre-flight.

## 3. Presets (done, verified - do not re-probe)

`frontend/app/components/BriefForm.tsx` PRESETS (short chips, full values
fill the three inputs):
1. Wine bar / natural wine bar / Brooklyn / millennials
2. Tacos / taco shop / Austin, Texas / young families
3. Listening bar / listening bar / Williamsburg / young professionals
4. Coffee / specialty coffee shop / Silver Lake, Los Angeles / gen z
5. Izakaya / izakaya / East Village, Manhattan / young professionals
6. Jazz club / jazz club / Harlem, Manhattan / young women
7. Craft beer / craft beer hall / Denver, Colorado / men 25-34
8. Bubble tea / bubble tea shop / Monterey Park, California / gen z
9. Record store / vinyl record store / Bushwick, New York / gen z

Audience rule (live-verified, also in `docs/qloo-contract.md`): SAFE =
millennials, young professionals, gen z, young women, men 25-34, young
families. DEAD-END (needs_input, zero candidates -> section omitted) =
families, parents, college students, couples, tourists. Concept words all
resolve (specialty coffee, jazz club, ramen, barbecue, craft beer, izakaya,
vegan, bubble tea, speakeasy, record store, hot pot, baked goods).

## 4. Expected live behavior (for demos)

Grounded run: ~40-70s for 3 envelopes/23-ish events on a fresh quota;
occasionally ~2 min if a TPM window is tight - the pane shows a ticking
`running… Ns` and the trace keeps moving, so narrate the contrast while it
runs. Ungrounded pane: 2-8s. One double-run costs ~10-15k TPD of ~200k.

## 5. Quirks/lessons (still true - do not relearn)

- **PS 5.1 + Unicode = footgun.** New concrete case: `Get-Content | -replace
  ... | Set-Content` mangled a JS regex's U+2026 ellipsis into `???` and the
  demo script died on a Node syntax error. Do not round-trip source files
  through PS text cmdlets; use editor tools. .ps1 files stay ASCII-only
  (non-ASCII lines get executed as garbage).
- **`py -3.12` buffers stdout without a TTY** - always `py -3.12 -u`.
- **py.exe launcher pid != owner pid** - assert restarts via uvicorn log
  content, never pids.
- **Playwright mocks:** glob `*` does not cross `/`; register
  `**/api/agent/run/**` AND `**/api/agent/runs/**`. Real-browser driver:
  require playwright by absolute path from `frontend/node_modules` when the
  script lives in %TEMP%.
- **React-compiler lint:** no setState in effect body, no ref/Date.now()
  reads during render. Clocks: parent handler -> prop -> interval setState.
- **PS 5.1 npm shims mangle inline --input JSON** - always `--input-file`
  with `qloo exec`.
- Quota hygiene: probes sequentially, 2s spacing, never loop.
- `ngrok`-style public tunnels: not needed; P5 is EC2/Caddy per runbook.

## 6. Next steps, in order

1. **P5 deploy** (biggest hackathon-readiness gap): `deploy/`
   Dockerfile.backend + Dockerfile.frontend + docker-compose.yml + Caddyfile
   + smoke_test.sh; AWS t3.micro, plan B Fly.io (IMPLEMENTATION.md §6.1/§6.4).
   Frontend needs `NEXT_PUBLIC_API_BASE`/`API_BASE` pointed at the public
   origin (check `frontend/lib/api.ts` + `.env.local`).
2. **Lighthouse a11y >= 95** on the production build (still open).
3. **P6 package:** MIT LICENSE, README per kit SUBMISSION.md, public repo,
   Devpost draft (IMPLEMENTATION.md §8), submit by Oct 29.
4. Optional demo polish (do not block P5/P6): URL params for shareable
   preset links; verdict strip "grounded citations vs model guesses";
   "Surprise me" shuffle over the 9 presets.

## 7. Working session env (end state - SERVERS ARE RUNNING)

- Backend: :8000, started via `backend\serve.ps1` with the latest code
  (P4.3); health 200. Restart ONLY via that script (it kills the listener
  first and asserts the bind in the log).
- Frontend: `npm run dev` on :3000 (Next hot-reload; picks up frontend
  edits automatically). Open http://localhost:3000 to demo.
- To stop: kill the :8000 python pid and the :3000 node pid from
  `Get-NetTCPConnection -LocalPort <port> -State Listen`.
- Provider: `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`; this
  session burned roughly 5 live double-runs + ~35 direct Qloo probes
  (probes cost no LLM quota); TPD still comfortable. Gemini fallback resets
  ~07:30 UTC.
- Playwright chromium installed (1248). Demo driver + screenshots paths
  in §1; probe scratch in `%TEMP%\opencode\preset_*.ps1`.
