# Tastewell

**Choose an artist and venue for one live-music test.** Tastewell asks who you
want to reach, uses Qloo to find and rank artists for your venue, and shows the
sources behind each option. An agent reviews those results and suggests a
small pilot. You make the final call after checking costs and availability.

**Why Qloo matters:** Change the audience or region and Tastewell reranks the
*same artists*. You can see when the cultural evidence changes the choice,
instead of accepting a generic AI suggestion.

**Hosted preview:** [Open the Tastewell decision workspace](https://tastewell.35-154-50-144.sslip.io/decision).
The demo is password protected. Access details and a short judge walkthrough
are below. The instant example is invented and labeled; create a new decision
to see live Qloo results.


## Judge access and testing

Open the [hosted decision workspace](https://tastewell.35-154-50-144.sslip.io/decision).
When the browser asks for HTTP Basic Authentication, enter:

```text
Username: judge
Password: spark123
```
It was added in additional info for judges too

**Fast path:** Choose **See an illustrative decision** to inspect a completed
example immediately. It is read-only, uses invented data, and makes no Qloo
call.

**Live Qloo path:**

1. Enter venue `Judge test listening room`, concept `jazz`, region `Brooklyn,
   New York`, audience `millennials`, and objective `Choose an artist for a
   quiet weeknight`. Keep **Live music is permitted at this venue** checked,
   then start the decision. If asked, select the music-genre jazz tag.
2. Compare the artists, open **Inspect Qloo evidence**, then choose
   **Review the pilot choice**. The agent suggests a pilot and cites its
   sources; you still decide whether to select it.
3. Change the scenario region to `Los Angeles, California` and choose
   **Compare scenario**. See whether the *same artists* move in the ranking.
   Saved history and JSON export let you revisit the evidence.

The brief and decisions in this walkthrough are synthetic. Do not record a
real-world outcome for the test.

Live Qloo results may vary by audience and region, so exact artist names and
rank changes are not guaranteed on every run. The [official hackathon rules](https://qloo.devpost.com/rules)
allow private demos when login credentials are provided in testing instructions.

## Why Qloo

Qloo supplies cultural relationships for the audience and area. Tastewell uses
the Qloo harness over MCP to turn those relationships into a checkable choice:

1. `find_tags` resolves the venue concept into candidate Qloo tag IDs, with a
   human choice when the match is ambiguous.
2. `recommend` discovers artists and an optional brand using the chosen tag,
   audience, and region; supplied artist names can instead be resolved with
   `describe`.
3. `rank` orders the same artist IDs within each eligible venue. The UI
   preserves source queries and IDs, and a scenario can rerank those IDs for
   a changed audience or region.

A proposed artist has a Qloo ID and an inspectable source row. A changed
audience can change the ordering of the same artist shortlist; ranks from
different calls are labeled separately. Ambiguous matches require a user
choice, and missing evidence is reported rather than filled with guesses.
See [the Qloo contract](docs/qloo-contract.md) for observed request and
response shapes.

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
- A bounded agent review of a ready saved decision. The agent can inspect
  option evidence and venue constraints, request at most one operator-confirmed
  fixed-ID Qloo scenario on a live decision, and propose a pilot or abstain.
  Its action record, citations, and evidence fingerprint persist in the
  decision export. The operator still submits the pilot plan.
- Inspectable Qloo source IDs and a picker for ambiguous concept or artist
  matches.
- An instant read-only illustrative decision with invented `urn:sample` IDs,
  a rank-changing audience scenario, and a sample plan. It does not call
  Qloo or save an outcome; use the live brief for actual Qloo evidence.
- Bounded retries for transient provider/tool failures and malformed final
  model output. Failed runs surface an error rather than invented evidence.

For the deployed AWS pilot and its repeatable smoke checks, see the root
[deployment guide](DEPLOYMENT.md).

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

Open <http://localhost:3000> for the decision workspace. The backend health check is
<http://localhost:8000/api/health>.

## API and development

The frontend is Next.js; the backend is FastAPI. The browser never receives a
Qloo or LLM key. The older `/api/agent/*` endpoints remain only as an internal
development harness; the product UI does not call them.
`POST /api/decision-jobs` starts a cancellable decision; polling
`GET /api/decision-jobs/{job_id}` shows progress and `DELETE` cancels it.
Saved decision routes support resolution, scenario comparison, pilot
selection, outcomes, replay, and export. `POST
/api/decisions/{id}/agent-reviews` starts a cancellable review; `GET` and
`DELETE /api/decisions/{id}/agent-reviews/{review_id}` inspect or cancel it.

Run backend tests with `python -m pytest -q` from `backend/`; run frontend
lint with `npm run lint` from `frontend/`. The backend suite uses mocked
services by default. Live Qloo tests require explicit opt-in.

For a precise feature inventory, see
[current functionality](docs/CURRENT_FUNCTIONALITY.md). The proposed next
product is described in the
[phased product plan](docs/PRODUCT_IMPLEMENTATION_PLAN.md).

## Limitations and status

Tastewell runs as a small private preview on AWS Lightsail. A synthetic hosted
journey exercised Qloo resolution and ranking, a cited agent recommendation,
saved history, and persistence after backend restart. The public browser UI
also completed a live brief, review, and fixed-ID region comparison. The
instance has a shared demo password; production decision records are isolated
by signed browser session, but there are no recoverable user accounts or
measured production capacity. Do not remove the access gate without adding
abuse controls for the paid Qloo/model calls.
Concept resolution and recommendation coverage vary by audience and region.
Qloo affinity is a cultural signal, not a demand or sales forecast. In-flight
decision jobs reset when the backend restarts; completed
decisions persist in SQLite. Buyer interviews and real operator pilots are
still required before claiming product value or commercial viability.

## License

This project is open source under the [MIT License](LICENSE). The license file
is at the repository root. Do not commit `.env`, API keys, or private Qloo
results.
