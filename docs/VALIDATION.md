# Tastewell Phase 0 validation pack

Status: desk-research hypotheses and synthetic evaluation, 2026-10-28. The
user has chosen not to interview operators. This document records external
evidence and explicit assumptions; it is **not customer or revenue validation**.
The `/decision` workspace implements part of the workflow below. Synthetic
briefs and source-backed desk research are the evaluation method for now.

## Published proxy evidence (not interviews)

- The [National Restaurant Association's 2026 industry report](https://www.restaurant.org/research-and-media/research/research-reports/state-of-the-industry/)
  reports uneven traffic, cost pressure, and operator interest in technology
  for efficiency and guest connections. Its [August 2026 operator tracking](https://www.restaurant.org/research-and-media/research/restaurant-economic-insights/economic-indicators/same-store-sales-and-customer-traffic/)
  found 43% reporting higher year-over-year traffic and 46% reporting lower
  traffic. This supports testing a weak-slot decision, not a claim that
  programming software improves traffic.
- [SevenRooms' 2025 U.S. survey](https://sevenrooms.com/press/2025-US-data-report/)
  reports that 35% of operators cited tracking the success of their efforts
  and 31% cited consistency across locations as personalization challenges.
  It also reports consumer interest in special experiences and live music.
  SevenRooms sells hospitality software, so its survey is useful context,
  not independent proof of a buyer or a willingness to pay for Tastewell.
- The [National Restaurant Association's 2026 staffing research](https://go.restaurant.org/rs/078-ZLA-461/images/2026-Research-Insight_Hiring-and-Staffing.pdf?version=0)
  reports that 60% of surveyed operators said technology had a significant
  impact on marketing/advertising over the prior 2–3 years. That suggests a
  relevant workflow but does not show that Qloo-backed programming is a
  budget priority.
- [Toast's 2026 Voice of the Restaurant Industry](https://pos.toasttab.com/th-us/blog/data/voice-of-the-restaurant-industry-2026)
  surveyed 676 operators; 47% named increasing guest demand as a top goal.
  Toast sells restaurant software. The result supports attention to demand,
  not any specific program or purchase of Tastewell.
- [SevenRooms' 2025 U.S. research](https://sevenrooms.com/research/2025-US-restaurant-trends/)
  reports that 54% of surveyed operators planned brand collaborations. This
  makes partner exploration a plausible use case; it does not establish a
  brand partner's willingness, availability, or price.

**Educated assumption:** a group operator may value a repeatable, measurable
programming choice across venues. None of these sources identifies the
actual decision owner, procurement path, frequency, or acceptable price.
Tastewell must not present this assumption as an interviewed finding.

### Decisions made from the desk research

| Product choice | Grounding | Remaining uncertainty |
| --- | --- | --- |
| Lead with a weak weekday programming decision for a multi-venue group. | [NRA traffic tracking](https://www.restaurant.org/research-and-media/research/restaurant-economic-insights/economic-indicators/same-store-sales-and-customer-traffic/) shows uneven traffic; [Toast's survey](https://pos.toasttab.com/th-us/blog/data/voice-of-the-restaurant-industry-2026) shows demand growth is a common priority. | We assume the group makes this choice regularly. No source measures this exact cadence or Tastewell's value. |
| Make venue consistency and measurement visible in the decision record. | [SevenRooms' survey](https://sevenrooms.com/press/2025-US-data-report/) reports multi-location consistency and performance tracking challenges. | Vendor survey responses do not prove these are the highest priority for our intended buyer. |
| Offer an optional brand partner idea, separate from artist ranking. | [SevenRooms' trend report](https://sevenrooms.com/research/2025-US-restaurant-trends/) reports interest in brand collaborations. | A specific partner's interest, contract, and cost must be verified outside Qloo. |
| Default to a low-risk, single-location pilot before expansion. | This is an **engineering and product judgment** to limit unverified operational and financial assumptions. | No observed pilot outcomes or measured uplift exist. |

The working buyer is a marketing or experience lead for a 3–30 venue group.
The range, decision cadence, and budget authority are **design assumptions**,
not figures in the cited reports. The current app can support an independent
venue too; it should not claim market fit for either segment.

## Decision and buyer hypotheses

**First decision to test:** A hospitality group chooses one weekly programming pilot, a venue, and a small measurement plan for a weak weekday slot. The operator can bring a shortlist of acts, themes, and brands, or ask for discovery. A useful result contains feasible alternatives, traceable cultural evidence, explicit unknowns, and a chosen next action.

| Hypothesis | What would support it | What would challenge it |
| --- | --- | --- |
| A marketing or experience lead for 3–30 venues owns this recurring choice. | They describe a recent choice, a calendar cadence, and authority to commission or recommend a pilot. | Decisions are made ad hoc by each venue or entirely by outside promoters. |
| Cultural fit evidence can change a real shortlist or site choice. | The lead names a decision they would revise after inspecting a credible signal. | Booking price, availability, existing relationships, or capacity always dominate. |
| A decision record is worth maintaining. | The team already compares plans and outcomes across venues, or asks to revisit a prior rationale. | Each event is treated as unique and no one reviews results. |
| A buyer can pay for the workflow. | They identify a budget owner, current spend, and a plausible buying process. | They value an occasional free report but cannot name an owner or recurring budget. |

Alternative buyers to test: regional operations managers, agencies managing venue clients, and independent owners. Do not count interest in a demo as buying intent. Record the person's role, organization size, current tools, decision frequency, approval path, and willingness to review a live pilot.

**Current gate:** evaluate B1–B3 using disclosed synthetic inputs and saved
Qloo evidence, score the rubric below, and inspect any unsupported claims.
This gate can establish technical behavior and decision clarity only. Buyer,
purchase, and real-world outcome claims stay unverified without primary data.

## Three benchmark decisions

These are **synthetic test briefs**. Operators should replace the assumptions with their own facts. Record the pre-Tastewell choice before running any Qloo call; the suggested choice below is a test expectation, not a Qloo result.

### B1 — Eight-bar group, weak Wednesday

- **Operator input:** Eight bars in New York; compare a 120-capacity Williamsburg listening bar and a 90-capacity East Village cocktail bar for four Wednesdays next month. Objective: a feasible program that gives a reason to visit midweek. Audience: young professionals. Maximum pilot spend $2,500 per night. Both close at midnight; Williamsburg has a 10 p.m. amplified-sound cutoff. Shortlist: a local jazz trio, a vinyl DJ, a listening session; possible nonalcoholic beverage brand partner. Artist availability and fees are unknown.
- **Pre-Tastewell decision to record:** Which concept and site would the operator choose today, using their own knowledge?
- **Expected acceptable output:** Three distinct concepts, such as an early seated jazz set, a low-volume vinyl listening session, and a partner-led tasting. At least one option must work within the sound cutoff or state its required verification. Every named artist or brand proposed as Qloo-backed has an ID and evidence row. The selected pilot names a venue, date window, owner, budget assumptions, and baseline/success metric. It can say no artist is bookable until availability and fee are checked.
- **Unacceptable:** Claiming Qloo predicts attendance or sales; assigning a real act a fee or availability without operator evidence; treating artist and brand affinity as one universal score; citing an entity absent from the run.

### B2 — Ambiguous jazz concept and audience wording

- **Operator input:** Three Harlem/East Village venues need one Sunday afternoon program. The request says “jazz for families”; one site excludes amplified music, one has a $1,200 cap, and a third requires an all-ages format. The operator has two locally known acts but only their names, which may resolve ambiguously. Exact venue capacities and availability are supplied later.
- **Pre-Tastewell decision to record:** What would the operator book or reject without Tastewell?
- **Expected acceptable output:** The system stops on ambiguous “jazz” tag or act names until an ID is selected. It distinguishes the unsupported demographic word “families” from the live-verified “young families”; it asks for confirmation before substituting terms. It can still compare feasibility using operator facts while clearly marking cultural evidence missing. The three alternatives differ in format or audience approach, not just wording.
- **Unacceptable:** Silently selecting one of several jazz tags, silently rewriting “families,” using tag URNs where an entity is required, or presenting a grounded rank after a zero-candidate resolution.

### B3 — Sparse geographic evidence

- **Synthetic input:** A hypothetical four-venue group near a smaller regional city wants a Thursday collaboration with a local maker, a singer-songwriter, or a film club. Audience: millennials. Location and shortlist must be selected from public, verifiable entities before a live Qloo run; no venue coordinates, capacity, or operating rules are represented as real operator facts.
- **Pre-Tastewell decision to record:** Which site and theme would the operator try using current information?
- **Expected acceptable output:** Resolve the specific location and candidates, show any missing or weak Qloo result, and allow an operationally feasible pilot recommendation with an explicit “cultural fit unverified” label if necessary. A map is optional and cannot add unsupported detail. The plan names the smallest credible test and what evidence would change the choice.
- **Unacceptable:** Borrowing scores from a nearby large city without disclosure, coloring a geographic heatmap without validated cells, or labeling an empty response as demand.

## Quality rubric

Score each benchmark independently from 0 to 2 per criterion: **0** absent/wrong, **1** partially useful or requires builder explanation, **2** useful and independently inspectable. A reviewer should see the saved input, Qloo evidence snapshot, output, and trace. Record elapsed time and the pre-Tastewell choice alongside the scores.

| Criterion | Score 2 requires |
| --- | --- |
| Option distinctness | Three meaningfully different, decision-ready pilots, or an explicit reason fewer are supportable. |
| Evidence validity | Every grounded entity and material claim opens a matching ID, query context, status, and source row; no fabricated measurements. |
| Decision usefulness | A clear choice or honest no-choice, comparison with alternatives, and one next action an operator can take. |
| Constraint fit | Hard constraints filter choices before preference ranking; unknown fee, availability, staffing, and licensing stay unknown. |
| Uncertainty honesty | Ambiguity, sparse results, degraded/error states, and non-comparable calls are visible in plain language. |
| Speed | First useful, inspectable alternative appears within a time target agreed with operators; log actual seconds. |
| Independent completion | A new operator can choose or reject a pilot and explain the evidence without the builder. |

**Provisional technical acceptance:** no zero in evidence validity, constraint fit, or uncertainty honesty; total at least 11/14; and an independent reviewer can complete a choice in under five minutes after results appear. With builder-only synthetic evaluation, these are uncalibrated targets, not proven usability. Log whether Qloo changed the pre-recorded synthetic choice and why; a changed choice is not automatically better. Buyer and impact gates are outside this desk-research run.

### Current benchmark gap assessment

This is a code-path assessment, not a scored operator evaluation. No real
operator has run these briefs end to end.

| Brief | Supported now | Gap before the benchmark can pass |
| --- | --- | --- |
| B1 | Multiple venues, artist shortlist resolution, per-venue rank, pilot selection, outcome record. | Capacity, amplified-sound cutoff, event time, known fee, and partner availability are not hard constraints. Budget remains unverified. |
| B2 | Ambiguous tag and artist matches stop for a human choice; no-live-music venues are excluded. | The wording “families” is not confirmed or changed to “young families”; unsupported demographics can yield no evidence. All-ages and cost constraints are not modeled. |
| B3 | Empty/failed Qloo calls exit without a fabricated cultural recommendation. | The current wedge is artist-led live programming; maker and film-club alternatives, operator coordinates, and a geographic evidence view are outside it. |

The current implementation therefore does **not** pass the three-benchmark
Phase 2 gate. Published proxy research cannot supply the missing operational
facts or the operator review needed to revise these benchmarks.

### 2026-10-29 agent review verification

- A synthetic live `jazz club` brief in Brooklyn with two public artist
  names required a human concept-tag choice, then produced two options and a
  complete Qloo artist rank (positions 1 and 2 within one venue call).
  The bounded model review inspected the proposed option and venue, then
  returned a cited recommendation. This verifies the local model/Qloo path,
  not a real venue's suitability or artist availability.
- A separate synthetic cocktail-bar run reached `needs_input` during artist
  discovery and produced no options. This is the expected honest stop for
  that input; it is not evidence that the discovery path is reliable for all
  audiences.
- Automated checks cover invalid citations, stale snapshots, replay without
  new Qloo calls, the one-comparison limit, cancellation, model unavailability,
  and no selection side effect. The mocked browser journey covers review,
  sources, and the operator plan handoff at desktop and mobile widths.
- A fresh visible browser journey on the local build completed concept
  selection, two-artist Qloo ranking, agent review, source inspection, and
  reopening the persisted review. Its synthetic jazz-club case produced a
  cited pilot proposal after inspecting the option and venue. The journey
  used an isolated temporary SQLite database and did not test hosting.
- B1 still lacks sound-cutoff, capacity, timing, and fee constraints. B2 still
  needs exact audience-wording confirmation. B3 remains outside the current
  artist-led wedge. No independent operator scored these briefs, and no
  hosted agent journey has been tested.

## First-decision Qloo probe matrix

Existing contract facts are from `qloo-contract.md`; proposed combinations remain unverified. Use one resolved, consent-safe shortlist and a fixed location/audience for comparisons. Run bounded calls sequentially with spacing, save redacted envelopes, and record status, correlation ID, result IDs, and retrieval time. Never submit private venue or customer records.

| Input | Workflow and exact contract | Ambiguity / failure handling | Output field and defensible claim | State |
| --- | --- | --- | --- | --- |
| Venue theme, e.g. “listening bar” | `find_tags`: `{query, semantic, limit}` | Inspect tag type and semantic fuzziness; ask for selection when several meanings fit. | Selected tag URN supports a concept anchor, not a venue-performance claim. | Verified shape; selection policy to test. |
| Chosen tag, region, confirmed audience | `recommend`: `{target_type:"artist", signal_tags:[tag_urn], signal_location, demographic, limit, explain?}` | `needs_input` with no candidates stops that audience path; no silent synonym. | Returned artist IDs and within-call affinity support candidate discovery. | Basic call verified; `explain` usefulness untested. |
| Same context for brands | `recommend` with `target_type:"brand"` | Keep brand evidence separate from artist evidence. | Returned brand IDs support partner discovery, not a combined artist/brand score. | Basic call verified. |
| Operator's ≤10 resolved artist IDs and one fixed signal context | `rank`: `{options:[ids], option_type:"artist", signals?, signal_location?, demographic?}` | Resolve names first; if any ambiguity or missing ID, hold the rank. Do not compare scores across calls. | Relative order of the **same shortlist in one call** supports artist comparison. | Shape verified; exact signal combination and ID-list behavior need a bounded probe. |
| One selected artist ID | `describe`: `{entity:id, type?:entity_type}` and `entity_tags`: `{entities:[id], entity_type?, limit?}` | Check subtype and empty/partial status; avoid inferring booking facts. | Identity and related tags may help explain differentiation. | Shapes verified; usefulness for these candidates untested. |
| Resolved artist ID and candidate area | `where_popular`: `{entity:id, entity_type?, within:area, limit?}` | Verify geohash resolution, coverage, and meaning before any map overlay. | Aggregate geographic affinity for that entity in that area only. | Shape verified; map semantics and decision value untested. |
| Changed audience or area with **fixed candidate IDs** | Repeat `rank` under one changed context per call | Show call contexts side by side; ordinal changes only, no score subtraction across calls. | Sensitivity of shortlist order to the changed context. | Proposed use; needs contract and usefulness probe. |

### Bounded unanswered probes

1. With one resolved artist shortlist, test `rank` using IDs, a single verified concept signal, region, and supported demographic. Save the returned option order and query context. A schema rejection is a result; do not broaden into repeated guesses.
2. Test one `recommend(..., explain:true)` on the same concept context to see whether explanation fields add traceable evidence or only prose.
3. Test `where_popular` for one resolved artist and the B1 area. Inspect geohash size, spatial coverage, and field definitions before planning any overlay. Do not call it demand or traffic.

Add observed calls and redacted field shapes to `qloo-contract.md`. Stop after these questions are answered. The Phase 1 schema and Phase 2 slice should be based on observed fields and the synthetic benchmarks, with real-world value unverified.

## Interview and run record template

Copy this block for each person or benchmark run; keep personal details outside the repository.

```text
Record ID / date:
Role and venue count (anonymized):
Decision frequency and current tool:
Pre-Tastewell choice and rationale:
Hard constraints / unknowns:
Evidence supplied by operator:
Qloo calls and statuses (redacted snapshot paths):
Tastewell choice / no-choice:
Rubric scores (7 values) and elapsed seconds:
Did the choice change? Why or why not?
Outcome metric and baseline source (if available):
Buyer / pilot follow-up and purchase authority:
Observed facts:
Remaining assumptions and questions:
```
