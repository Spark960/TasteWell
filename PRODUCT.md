# Tastewell product context

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
The first intended user is a marketing or experience lead managing several hospitality venues. This is a design hypothesis, not a validated customer segment.

## Product Purpose
Help an operator decide which live-music concept or act to pilot, at which eligible venue, why, and what to measure. The useful output is a saved, revisitable decision record.

## Positioning
Tastewell combines Qloo's aggregate cultural signals with venue-specific operational inputs. It keeps source evidence, unresolved constraints, a selected pilot, and later aggregate outcomes together instead of returning a one-off recommendation.

## Operating Context
An operator supplies a venue concept, audience, objective, one or more venues, permission and budget constraints, and optionally an artist shortlist. They compare a small set of pilot options, inspect evidence and unknowns, test an audience or region change, choose a pilot, then record the plan and outcome from their own records.

## Capabilities and Constraints
- The programming decision workspace is the primary experience. The earlier grounded-versus-generic brief comparison remains accessible as a secondary demo.
- The current decision slice covers artist-led live music, up to ten venues and five supplied artist names.
- Ranks are comparable only within each venue's Qloo shortlist call. Qloo does not establish availability, fees, staffing, licensing, sales forecasts, or causal impact.
- Known costs above a venue's budget ceiling are rejected. Unknown costs remain unverified.
- Decisions persist in SQLite. In-flight work is in memory. The product has no per-user accounts or retention policy yet.

## Brand Commitments
The name is Tastewell. Product language should be direct, careful about evidence, and useful to an operator making a practical decision.

## Evidence on Hand
The repository has a working prototype and mocked browser journeys. It has no confirmed operator interviews, measured pilot uplift, or public deployment; the interface must not imply otherwise.

## Product Principles
- Make the next decision and its required inputs clear.
- Keep source evidence and unresolved operational facts visible.
- Preserve comparability limits when showing ranks.
- Make a decision easy to revisit after the pilot.
