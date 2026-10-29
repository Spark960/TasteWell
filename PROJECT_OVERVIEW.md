# Tastewell — current project status

Updated 2026-10-29. This is the root status for the Qloo Agentic Hackathon submission. See [README.md](README.md) for local setup, [HANDOFF.md](HANDOFF.md) for the latest work log, and [docs/PRODUCT_IMPLEMENTATION_PLAN.md](docs/PRODUCT_IMPLEMENTATION_PLAN.md) for the remaining product work.

## Verdict against the hackathon requirement

**Code-level Qloo integration: yes. A bounded agent review is visible in the product. Submission-ready: no.** The [hackathon overview](https://qloo.devpost.com/) asks for a working Qloo-powered application that is an agentic tool, uses an agent framework, or connects Qloo to an existing agent. Those are alternatives; the app does not need to recommend across every cultural category. The current product focuses on live-music programming, with place/concept tags and optional brand affinities.

| Requirement | Current evidence | Assessment |
| --- | --- | --- |
| Working software application | Next.js decision workspace, FastAPI decision API, SQLite snapshots, local end-to-end browser checks. | Working local prototype; clean install and hosted operation still need verification. |
| Qloo API integration and cultural grounding | The backend uses the Qloo MCP harness to call `find_tags`, `describe` or `recommend`, and `rank`. It stores query context, Qloo IDs, status, and source rows. Missing evidence does not become a fabricated option. | A longer MCP handshake succeeds locally and a fresh synthetic two-artist run produced complete ranks. Hosted readiness remains untested. |
| Agentic tool, framework, or existing agent | The workspace now invokes a bounded LLM review of a saved Qloo decision. It can inspect option and venue facts, request one operator-confirmed scenario rank, and produce a validated proposal or abstain. | Implemented and exercised locally with live Qloo and a model. The reviewer must still see it on a hosted build before calling the submission ready. |
| Qloo as the differentiator | The option names and ranks depend on Qloo-resolved artist IDs and responses; the same saved shortlist can change order under a new audience or region. The illustrative example is explicitly invented and makes no Qloo call. | Strong product rationale, but a judge needs a reliable live path and a clear explanation of what Qloo changed. |
| Judge-accessible submission | The [hackathon page](https://qloo.devpost.com/) requires an externally hosted, fully published functional demo, a public repository, description, and visible open-source license. | **Blocked.** This checkout is local only; no hosted smoke test or submission exists. `git remote -v` currently returns no configured remote. `LICENSE` exists locally, but a public repository and visible license have not been verified. |

The official [rules](https://qloo.devpost.com/rules) also permit a private test site when judges receive credentials, while the overview says private-access-only demos do not qualify. Resolve that discrepancy before relying on the prepared Basic Auth preview. An externally reachable demo with safe sample data is the clearest route.

## Product that exists now

Tastewell helps a venue operator choose an artist-led programming pilot: enter one to ten venues, a concept, target audience, objective, and optional artist shortlist; resolve ambiguous Qloo matches; review up to three artist options and their evidence; compare the same artists under a changed audience or region; select a venue and pilot plan; and later record an aggregate outcome. It supports saved history, JSON export, and replay from a saved evidence snapshot. A clearly labeled read-only illustrative decision opens instantly from the landing state. It is synthetic and is never presented as live Qloo evidence.

The active routes are `/` and `/decision`. The former `/compare` frontend route and its UI have been removed. The old `/api/agent/*` backend routes remain for an explicit dependency audit; the product frontend calls the separate bounded `/api/decisions/{id}/agent-reviews` path.

The app treats Qloo outputs as aggregate cultural signals. It does not infer individual preferences or claim booking availability, fees, staffing, licensing, ticket demand, revenue, or causal impact. Known costs above a selected venue's operator-supplied budget are rejected; many other operational constraints remain unverified. Current options cover artist-led live music, not film, fashion, travel, or the full set of Qloo domains.

## Architecture and proof points

| Component | Current role |
| --- | --- |
| `frontend/app/decision/page.tsx` | Main decision journey and API requests. |
| `frontend/app/decision/sampleDecision.ts` | Invented, read-only example; no backend or Qloo call. |
| `backend/app/api/routes.py` and `engine.py` | Decision jobs, cancellation, resolution, scenario, selection, outcome, persistence, and legacy agent endpoints. |
| `backend/app/api/decisions.py` | Deterministic Qloo-backed concept/artist resolution, discovery, ranking, evidence ledger, and pilot-option construction. |
| `backend/app/qloo/mcp_client.py` | Qloo MCP harness connection and typed tool-call normalization. |
| `backend/app/agent/decision_review.py` | Four-turn model review with saved-evidence tools, one optional fixed-ID Qloo comparison, and strict output validation. |
| `backend/app/agent/loop.py` | Existing LLM tool-calling agent; currently accessible only through the legacy API. |
| `backend/app/api/decision_store.py` | SQLite decision records. No per-user ownership. |
| `deploy/` | Prepared Compose/Caddy deployment package, not yet built or hosted. |

Previous local live browser checks completed a Qloo-backed decision with three artist options, an audience rerank, a pilot plan, and evidence inspection. On 2026-10-29, a fresh synthetic live browser journey resolved an ambiguous concept, ranked two public artists within one venue call, and the bounded model review inspected the option and venue before proposing a cited pilot. The saved review reopened with its action record. These are developer tests, not operator validation or proof of hosted reliability. The non-live backend suite passed 95 tests with 3 deselected; frontend lint, production build, and five mocked decision browser tests passed.

**Runtime check on 2026-10-29:** The installed Qloo MCP harness initialized with a longer handshake and exposed ten expected tools. The readiness timeout was increased from 15 to 45 seconds. The local sandbox required explicit access to the installed CLI; a hosted process remains untested.

## Immediate priorities

1. Run a fresh Qloo decision and agent review through the visible UI with the final local backend and then the hosted build. Keep the illustrative fixture clearly separate.
2. Confirm the review's grounding and failure paths with B1–B3 and an independent operator walkthrough. Preserve the focused venue-decision product.
3. Complete the three synthetic benchmark briefs in [docs/VALIDATION.md](docs/VALIDATION.md), including sparse evidence and operational constraints. Seek an independent operator walkthrough; no buyer or impact validation is claimed.
4. Publish and smoke-test a judge-accessible external demo with safe data, then connect and verify a public repository and visible license. This checkout has no Git remote configured. Keep saved decisions protected or isolated; there is no user-level access control.
5. Prepare the Devpost description around a specific Qloo-dependent decision, exact tool calls, visible provenance, known limits, and truthful demo behavior. Submit before the published October 30, 2026 deadline (11:45 p.m. Eastern Time).

Until the live Qloo path and external demo work, the project should be described as a **promising local Qloo-powered prototype**, not an eligible completed submission or a validated business.
