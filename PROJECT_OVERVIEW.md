# Tastewell — current project status

Updated 2026-10-29. This is the root status for the Qloo Agentic Hackathon submission. See [README.md](README.md) for local setup, [HANDOFF.md](HANDOFF.md) for the latest work log, and [docs/PRODUCT_IMPLEMENTATION_PLAN.md](docs/PRODUCT_IMPLEMENTATION_PLAN.md) for the remaining product work.

## Verdict against the hackathon requirement

**Working hosted Qloo integration and a visible bounded agent review: yes. Submission-ready: not yet.** The [hackathon overview](https://qloo.devpost.com/) asks for a working Qloo-powered application that is an agentic tool, uses an agent framework, or connects Qloo to an existing agent. Those are alternatives; the app does not need to recommend across every cultural category. Tastewell focuses on live-music programming, with place/concept tags and optional brand affinities.

| Requirement | Current evidence | Assessment |
| --- | --- | --- |
| Working software application | Next.js/FastAPI/SQLite on a 2 GB Lightsail host; three running services, valid HTTPS, live public-browser decision, and persisted review after backend restart. | Hosted technical path verified on a synthetic brief. Independent operator validation remains open. |
| Qloo API integration and cultural grounding | The backend uses Qloo MCP `find_tags`, `recommend`/`describe`, and `rank`, storing IDs, queries, status, correlation, and retrieval times. | Hosted readiness was true. A public-browser run showed three artist options and a fixed-ID region comparison that changed two ranks. |
| Agentic tool, framework, or existing agent | A bounded LLM review inspects saved option and venue facts, can request one Qloo scenario, and proposes a cited pilot or abstains. | Hosted browser showed a proposal, source links, actions, alternatives, unknowns, and next check. The operator retains the pilot selection. |
| Qloo as the differentiator | Option names and ordinal ranks depend on Qloo-resolved IDs and responses. The illustrative example is explicitly invented. | Brooklyn-to-Los Angeles comparison moved two of three artists on the same shortlist; source queries were inspectable. |
| Judge-accessible submission | [Hosted preview](https://tastewell.35-154-50-144.sslip.io/decision), [public repository](https://github.com/Spark960/TasteWell), MIT license detected by GitHub, and tested Basic Auth sign-in. | Devpost entry and testing instructions are not submitted. Overview and official rules conflict on whether a password-protected demo qualifies. |

The official [rules](https://qloo.devpost.com/rules) permit a private test site when judges receive credentials, while the [overview](https://qloo.devpost.com/) says private-access-only demos do not qualify. The current preview uses Basic Auth to protect API quota and decision data. Resolve that eligibility risk in the final submission path.

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
| `backend/app/api/decision_store.py` | SQLite decision records with signed production browser-session ownership. |
| `deploy/` | Running Compose/Caddy package, public HTTPS, Basic Auth, and repeatable cloud smoke checks. |

On 2026-10-29, the public browser completed a fresh synthetic Qloo decision, agent review, saved-history reopen, and changed-region scenario. The scenario moved Braxton Cook from rank 2 to 3 and Jesse Boykins III from 3 to 2, while Ibeyi stayed at 1; the earlier review became stale. The backend's 98 non-live tests passed with 3 live tests deselected. Frontend lint, production build, and five mocked decision browser tests had passed before deployment. These are developer checks, not real operator validation.

**Runtime check on 2026-10-29:** The hosted Qloo MCP harness reported `ready: true` with ten expected tools. A live decision and review ran on the 2 GB host, which had about 1.2 GiB available afterward. The $24 4 GB plan is not needed by the measured small demo workload.

## Immediate priorities

1. Resolve the private-demo eligibility ambiguity in the [overview](https://qloo.devpost.com/) versus [rules](https://qloo.devpost.com/rules); if keeping Basic Auth, put the username and password in Devpost testing instructions, not the public repository.
2. Check the hosted UI on a narrow mobile viewport and with keyboard navigation. Run B2/B3 sparse and unsupported-input cases from [docs/VALIDATION.md](docs/VALIDATION.md), then seek an independent walkthrough.
3. Prepare the Devpost description around the specific rank-changing decision, exact Qloo calls, visible provenance, and known limits. Submit before October 30, 2026 at 11:45 p.m. Eastern Time, then verify the receipt.
4. Tighten SSH access after confirming how Lightsail browser SSH will continue to work, and arrange an off-instance backup if the demo retains real data.

The app is a **hosted, technically verified Qloo-powered pilot tool**. It is not a validated business or a completed Devpost submission yet.
