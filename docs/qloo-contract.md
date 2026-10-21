# Qloo Contract — live-verified workflow shapes

> Status: **LIVE-VERIFIED 2026-10-21 (P0)** against `hackathon.api.qloo.com` with
> harness 0.1.26. **MCP route live-verified 2026-10-21 (P2)** — tool names,
> schemas and envelope parity confirmed over stdio. Every entry below comes
> from captured responses (`probe/out/`, gitignored raws). When the harness
> CLI differs from IMPLEMENTATION.md, trust the harness and update both.

Capture method: `qloo exec <workflow> --input-file <json>` (files in
`probe/inputs/`, runner `probe/run-probes.ps1` + `probe/run-resolved.ps1`).
MCP capture: Python `mcp` SDK stdio client → `qloo mcp` (`backend/app/qloo/mcp_client.py`).
Raw outputs: `probe/out/<operation>.<variant>.json`.

## Harness facts (live-verified P0)

- Harness version installed: **0.1.26** (`qloo --version`), Node v22.23.2.
- Exact CLI invocation syntax verified:
  `qloo exec <operation> --input '<json>'` | `--input-file <path>` | stdin | `--jsonl`.
  No per-operation `--help`; `qloo exec <op> --help` → `unknown option`.
- **PS 5.1 gotcha:** npm `qloo.ps1` shim mangles inline `--input '{"a":"b"}'`
  → "workflow input must be valid JSON". Always use `--input-file`.
- Auth: `QLOO_API_KEY` env var works (`Qloo data: ready (environment)`);
  interactive `qloo setup --qloo` requires a TTY (piping prints the key only to
  itself? no — it just refuses: "interactive setup requires a TTY").
- Envelope statuses observed: **ok, needs_input, error** (empty proven via
  find_tags semantic=false, 0 results; partial/degraded not observed yet).
- Error codes observed: `QLOO_AUTH` (key missing — *fires before input schema
  validation*, so even bad inputs need a key set), `TOOL_INPUT` (schema
  violation), `QLOO_CONTRACT` (upstream rejects a valid-but-unsupported combo —
  see trends/place below; `retryable:false`).
- No per-call rate-limit payloads seen; ~25 sequential calls at 2s spacing
  caused no 429s.
- Common envelope fields: `schema_version:"1.0-preview.1"`, `operation`,
  `status`, `results[]`, `result_count`, `provenance` (source + real Qloo
  endpoint + GET request preview), `query_intent`, `execution`
  (`correlation_id`, `duration_ms`). `needs_input` adds `resolution.issues[]`
  with `candidates[] {id,name,type,popularity,description?,address?}`.
- Workflows accept plain entity **names** (auto-resolved) or Qloo UUIDs;
  ambiguous names → `needs_input` with candidates → re-run with UUID.

## Workflows

### 0. MCP surface (live-verified P2)
- `qloo mcp` exposes exactly **10 tools**: `qloo_capabilities` + the 9
  workflows below, names = `qloo_<workflow>`. `inputSchema.required` per tool:
  find_tags[query] · describe[entity] · recommend[target_type] ·
  rank[options,option_type] · where_popular[entity,within] ·
  compare_audiences[group_a,group_b] · audience_demographics[entity] ·
  entity_tags[entities] · trends[entities,entity_type,start_date,end_date].
- `qloo_capabilities` returns a **raw contract manifest** — NOT a 6-status
  envelope: `{manifest_schema_version:"1.1", contract_version:"1.0.0",
  capabilities_tool, result_schema_version:"1.0-preview.1", result_schema,
  operations[9], upstream, contract_checksum, adapter}`. Treat presence as ok.
- Data-tool envelopes over MCP are **identical** to `qloo exec` (same fields,
  same statuses) — one normalizer serves both routes.
- MCP-only quirks: `recommend` with `demographic` but no `signal_location` →
  `needs_input`, **zero candidates**, summary: "Demographic Qloo signals
  require signal_location so the audience geography is explicit" (self-heal:
  re-call with location). `audience_demographics` on a TAG URN (not an
  entity) → `needs_input`, zero candidates (abstain, not a picker case).
- env must carry `QLOO_API_KEY` + base URLs into the spawn (mcp_client does
  `os.environ` + setdefault).


### 1. find_tags
- real invocation: `qloo exec find_tags --input-file probe/inputs/...json`
- input schema (verified): `{query: string(min 1), semantic?: bool (default true), limit?: 1–20}`
- output shape per result: `{id (tag URN), name, type (tag URN), popularity}`
- jazz-probe result: **10** candidates (kit said 5; actual take=10), 9 distinct
  types: `genre:qloo, genre:music, music:qloo, genre_category:qloo,
  subgenre:qloo, influenced_by:qloo, influence:qloo, interests:qloo,
  cultural_genre:qloo`. Renamed "five Jazzes" problem → "nine Jazzes".
- Tastewell probes: "natural wine" → 10 tags across `cuisine:qloo,
  product_service:qloo, interests:qloo, amenity:qloo, resy:collection:place,
  genre:place:restaurant` (incl. `Natural Wine Bar`, `Natural Wine Selection`).
  "tacos" → `cuisine:qloo, popular_food_item:qloo, specialty_dish:place` +
  subitems (Tex-Mex Tacos, Tacos Mexicanos). "listening bar" → `setting:qloo,
  activity_type:qloo, amenity:qloo, cuisine:qloo, ambience:qloo, good_for:qloo`
  + related `Music Bar`, `Listening Station`.
- empty-result behavior: `{"query":"quantum flux dining","semantic":false}` →
  `status:"ok"`, `result_count:0` (results absent). With semantic=true the same
  query returned 10 fuzzy matches — **semantic search never yields an honest
  empty; use semantic:false to get the abstain-testable empty case, or treat
  far-fetched fuzzy hits as weak and check popularity.**

### 2. describe
- real invocation: `--input-file` `{"entity":"Franklin Barbecue"}` →
  `needs_input` (2 candidates: Austin TX vs Uganda; +popularity, description,
  address). Re-ran with UUID → ok.
- confirmed UUID call input: `{entity: <UUID>, type?: entity_type}` 
- output: `results[0] = {entity_id, name, type}` (single entity row; +
  `provenance.endpoint:"/entities"`).

### 3. recommend
- input schema (verified): `{target_type, signals?: string[≤10], signal_tags?:
  string[≤10] (tag URNs or words), signal_tags_operator?: union|intersection,
  signal_location?: string, demographic?: natural-language string
  ("millennials"), filter_location?, include_tags?/exclude_tags? + operators,
  explain?: bool, limit?}`. `target_type` ∈ artist, book, brand, movie,
  person, place, podcast, tv_show, videogame (aliases accepted).
- live call: `{"target_type":"artist","signal_tags":["urn:tag:genre:music:jazz"],
  "signal_location":"Brooklyn, New York","demographic":"millennials","limit":5}`
  → ok, count 5, per result: `{entity_id, name, type:"urn:entity",
  subtype:"urn:entity:artist", popularity, affinity (0–1, ranked top first),
  properties:{description, image.url}}`.

### 4. rank
- input schema (verified): `{options: string[≤10] (names or UUIDs),
  option_type, signals?, signal_location?, demographic?, include_tags?,
  exclude_tags?}` — **one shared options set per call; scores from separate
  calls are not comparable** (harness prompt guideline).
- live call: 3 coffee brands + Brooklyn + millennials → ok, count 3, per
  result `{entity_id, name, type, subtype?, popularity, affinity}` sorted by
  affinity (Blue Bottle 0.963 > Intelligentsia 0.917 > Stumptown 0.881).

### 5. where_popular
- input schema (verified): `{entity, entity_type?, within: string (required
  geographic area), limit?}`. Note `where_popular`/`describe`/
  `audience_demographics` use `entity_type_*` naming; insights-family uses
  `target_type`/`option_type`.
- live call: Franklin Barbecue (UUID) + "Austin, Texas" → ok, 10 geohash rows:
  `{location:{latitude, longitude, geohash}, query:{affinity, affinity_rank,
  popularity, entity_place_affinity, entity_place_affinity_rank}}`.

### 6. compare_audiences
- input schema (verified): `{group_a: string[≤10], group_b: string[≤10],
  target_type?, limit?}`. Ambiguous names → needs_input (Daft Punk → artist /
  person / album candidates).
- live call with artist UUIDs → ok; `results` is **a single object**
  (`result_count` absent): `{tags:[{tag_id, name, type, subtype, entity_id,
  popularity, query:{score, a.…, b.…}}], a: entity rows, b: entity rows,
  matchEntities}` — tags sorted by score; a/b are the two resolved groups.

### 7. audience_demographics
- input schema (verified): `{entity, entity_type?, limit?}`.
- live call Franklin Barbecue UUID → ok, count 1; per result:
  `{entity_id, query:{age:{24_and_younger,25_to_29,30_to_34,35_to_44,
  45_to_54,55_and_older}, gender:{male,female}}}` — **values are signed
  affinities (−1…1), not shares** (e.g. 30_to_34: −0.85 = below-average skew
  ... interpret as relative over/under-index). Render with aggregate framing.

### 8. entity_tags
- input schema (verified): `{entities: string[≤10], entity_type?, limit?}`.
- live call Franklin Barbecue UUID, limit 15 → ok, 15 rows:
  `{id (tag URN), name, type, popularity, affinity}` (affinity used to build
  the seed's taste profile).

### 9. trends
- input schema (verified): `{entities: string[1–5], entity_type,
  start_date: YYYY-MM-DD, end_date: YYYY-MM-DD, limit?}`.
- live call Daft Punk artist UUID, 2025-10-01→2026-10-01 → ok; top-level
  **`series[]`** (plus results-less envelope): per entity
  `{entity:{…, match:"identifier"}, points:[{date (weekly 2026-09-30 backwards),
  population_percentile, population_rank, population_rank_velocity,
  velocity_fold_change, population_percent_delta}]}`. Endpoint
  `/v2/trending`, real query param `signal.interests.entities`.
- **place is rejected**: `{"entities":[<Franklin place UUID>],"entity_type":"place",…}`
  → `error/QLOO_CONTRACT`, `retryable:false`. For venue concepts use a city
  locality or brand/artist proxies, or drop trends.

## Open questions for P0 probes → resolved
- [x] stdin or --input-file? — **both**; on PS 5.1 use `--input-file`
      (inline `--input` breaks through the npm .ps1 shim).
- [x] What does `degraded` look like in practice? — not triggered by any
      probe; treat as "results + reduced quality, read summary" (P1 fixture).
- [x] Do workflows take demographic/audience URNs? — `demographic` is free
      text ("young women", "men 25-34", "millennials"), harness converts to
      Qloo demographic signals; group_a/group_b take **entities**, not
      demographic URNs.

## Notes carried into IMPLEMENTATION.md §2.3 (name drift check)
- All nine workflow names match §2.3 exactly. `find_tags` takes `query`,
  `semantic`, `limit` only. Insights-family type enum above; search-family
  adds locality, actor, album, author, director.
