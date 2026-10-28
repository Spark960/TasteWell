# Tastewell

Tastewell helps a venue operator choose a programming pilot across one or
more venues. The experimental workspace at `/decision` resolves a concept
and artist shortlist with Qloo, compares the same artist IDs per venue,
shows inspectable evidence, and saves the selected pilot and outcome. The
older `/` demo still generates a Qloo-grounded concept brief beside a
generic LLM-only brief.

## Why Qloo

A generic model can suggest a playlist or a menu theme, but it cannot establish
which cultural signals are connected in Qloo's graph for the requested audience
and area. Tastewell's grounded agent uses the Qloo harness over MCP:

1. `qloo_find_tags` resolves the venue concept into candidate Qloo tag IDs.
2. `qloo_recommend` asks for artists and brands using those tags, the audience,
   and the region.
3. The agent writes a brief with source IDs. The UI exposes each tool's status,
   result count, and provenance in a live trace and evidence chips.

For example, a request for a taco shop in Austin targeting young families
first resolves “taco shop” to Qloo tags. Those tag IDs, `Austin, Texas`, and
`young families` become inputs to artist and brand recommendation calls. A
recommendation can appear in the brief only when it is supported by a returned
Qloo ID. Ambiguous matches are shown for a user choice; missing results are
reported as absences. See [the Qloo contract](docs/qloo-contract.md) for
observed request and response shapes.

Qloo data describes aggregate affinities. It does not establish what any
individual likes, what they will buy, or that a venue concept will succeed.

## Current features

- A decision workspace for up to ten venues and five operator-supplied
  artist names, validated venue CSV import, and human resolution of
  ambiguous Qloo matches.
- Per-venue artist ranks from separate calls over one shared shortlist;
  changed-audience or changed-region scenario comparisons keep those IDs
  fixed and show ordinal movement without combining affinity scores.
- Cancellable decision jobs with stage and elapsed-time display, saved
  evidence, pilot selection, aggregated outcomes, JSON export, and labeled
  replay from a saved snapshot.
- Nine quick-start venue presets and free-form concept, region, and audience
  fields in the older brief demo.
- A grounded brief with audience profile, menu tilt, music programming,
  adjacent brands, tag themes, and explicit absences.
- A generic comparison showing what the same model suggests without
  Qloo data.
- Live tool-call trace, source IDs, and a picker for ambiguous Qloo matches.
- Bounded retries for transient provider/tool failures and malformed final
  model output. Failed runs surface an error rather than invented evidence.

For a private AWS pilot, see the root [deployment guide](DEPLOYMENT.md).

## Run locally

Requirements: Node.js 22.19 or newer, Python 3.12 or newer, a Qloo hackathon
API key, and a key for one supported LLM provider. The Qloo key must use the
hackathon host configured in `.env.example`.

1. Install the Qloo harness and backend dependencies:

   ```bash
   npm install --global @qloo/qloo-harness
   python -m pip install -e "./backend[dev]"
   ```

2. Copy `.env.example` to `.env` at the repository root. Set `QLOO_API_KEY`,
   `LLM_PROVIDER`, and the matching provider API key. For the current
   OpenRouter setup, use `LLM_PROVIDER=openrouter`,
   `LLM_MODEL=openai/gpt-oss-20b`, and `OPENROUTER_API_KEY`. Keep `.env` private.

3. Create `frontend/.env.local` with this line:

   ```ini
   NEXT_PUBLIC_API_BASE=http://localhost:8000
   ```

4. From the repository root, start the backend:

   ```bash
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```

   On Windows with the Python launcher, `py -3.12` can replace `python`.
   `backend/serve.ps1` is a Windows helper that reads the root `.env`, restarts
   the port 8000 listener, and launches the backend from `backend/`.

5. In another terminal, start the frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Open <http://localhost:3000/decision> for the decision workspace or
<http://localhost:3000> for the brief demo. The backend health check is
<http://localhost:8000/api/health>.

## API and development

The frontend is Next.js; the backend is FastAPI. The browser never receives a
Qloo or LLM key. `POST /api/agent/run` starts a grounded or generic run,
`GET /api/agent/stream/{run_id}` streams trace events, and
`GET /api/agent/runs/{run_id}` returns the current result.
`POST /api/decision-jobs` starts a cancellable decision; polling
`GET /api/decision-jobs/{job_id}` shows progress and `DELETE` cancels it.
Saved decision routes support resolution, scenario comparison, pilot
selection, outcomes, replay, and export.

Run backend tests with `python -m pytest -q` from `backend/`; run frontend
lint with `npm run lint` from `frontend/`. The backend suite uses mocked
services by default. Live Qloo tests require explicit opt-in.

For a precise feature inventory, see
[current functionality](docs/CURRENT_FUNCTIONALITY.md). The proposed next
product is described in the
[phased product plan](docs/PRODUCT_IMPLEMENTATION_PLAN.md).

## Limitations and status

Tastewell is currently a local prototype. A [private-preview Compose package](deploy/README.md)
is prepared but has not been built on a Docker host or deployed. It uses one
shared password rather than multi-user ownership. Do not expose the local
decision API or its saved history publicly without an access-control layer.
Concept resolution and recommendation coverage vary by audience and region.
Qloo affinity is a cultural signal, not a demand or sales forecast. The
brief demo can end with an error when bounded model repair fails. Brief runs
and in-flight decision jobs reset when the backend restarts; completed
decisions persist in SQLite. Buyer interviews and real operator pilots are
still required before claiming product value or commercial viability.

## License

[MIT](LICENSE). Do not commit `.env`, API keys, or private Qloo results.
