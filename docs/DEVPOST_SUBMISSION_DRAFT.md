# Tastewell — Devpost submission record and copy

Prepared and submitted 2026-10-29. The Devpost project is at
https://devpost.com/software/tastewell-yi3k57. Devpost displayed “Project
submitted!” and “Submitted to Qloo Agentic Hackathon.”
The password belongs only in Devpost's judge-only Additional info field;
never add it to this file or the repository. The user reports entering it
directly in Devpost; this file intentionally does not record it.

## Project name

Tastewell

## Tagline

Choose venue programming pilots with inspectable Qloo cultural evidence.

## Short description

Tastewell helps a hospitality operator turn a venue, audience, and artist
shortlist into a small, traceable live-music pilot decision. Qloo resolves the
concept and artists, discovers candidates, and ranks the same artist IDs for
each venue. A bounded agent reviews the saved evidence, proposes a pilot or
abstains, and leaves the final choice to the operator.

## Inspiration

Programming a weak weekday night involves more than asking a model for event
ideas. An operator needs to compare a plausible artist shortlist across rooms,
see why each candidate appeared, and separate cultural fit from booking facts
such as fees, availability, licensing, and staffing. Tastewell explores whether
Qloo's aggregate cultural signals can make that choice more informed and
auditable. It is a technical pilot, not a claim of proven commercial impact.

## What it does

1. An operator enters one to ten venues, a concept, target audience, region,
   objective, and optionally up to five artist names or a venue CSV.
2. Tastewell asks the operator to resolve ambiguous Qloo concept or artist
   matches. It then creates up to three artist-led pilot options, each with
   inspectable source rows, Qloo IDs, query context, and explicit unknowns.
3. The same resolved artist IDs are ranked separately for each eligible venue.
   A changed-audience or changed-region scenario reranks those fixed IDs and
   shows ordinal movement without treating affinity values from different
   calls as one universal score.
4. A bounded agent inspects the saved shortlist and venue facts. It can request
   at most one operator-confirmed Qloo scenario, propose a cited pilot, ask for
   a missing fact, or abstain. The operator records the actual pilot choice and
   can later add an aggregate outcome.
5. Decisions, evidence, review actions, plans, and outcomes are saved. The
   operator can reopen a decision, export JSON, or replay a labeled snapshot.
   An instant illustrative example uses invented names and IDs and makes no
   Qloo call.

## How we built it

The frontend is Next.js. FastAPI runs the decision jobs and bounded review;
SQLite persists decision snapshots. The backend connects to the Qloo harness
over MCP. `find_tags` resolves a concept, `recommend` discovers artists and an
optional partner, `describe` resolves supplied artist names, and `rank`
compares a fixed shortlist. The agent's tool access and output are validated
against saved evidence, allowed actions, and a decision fingerprint. A model
cannot silently choose or record the operator's pilot. The hosted demo uses
Docker Compose and Caddy on AWS Lightsail with HTTPS and a shared demo gate.

## Challenges and lessons

- The word “jazz” can map to several Qloo tags. A visible human choice avoids
  silently grounding a decision in the wrong ID.
- A rank is meaningful inside its query context. A region change can change
  the order of the same artists, but the raw affinities across calls are not a
  common performance or revenue score.
- Qloo does not supply artist fees, booking availability, staffing, licensing,
  attendance, or sales forecasts. These remain operator checks, and the agent
  must identify them rather than invent them.
- A public-browser synthetic Brooklyn jazz run produced three saved options
  and a cited agent recommendation. A separate Los Angeles scenario moved
  Braxton Cook from rank 2 to 3 and Jesse Boykins III from 3 to 2; Ibeyi
  stayed at 1. This verifies a working technical path, not the quality of a
  real booking decision.

## What's next

Test the decision with venue operators, capture their pre-Tastewell choice,
and learn whether evidence changes their shortlist. Add stronger operational
constraints, recoverable accounts, measured capacity, and an outcome workflow
before treating this as production software.

## Links

- Demo: https://tastewell.35-154-50-144.sslip.io/decision
- Public source: https://github.com/Spark960/TasteWell
- License: MIT, detected on the repository page

## Private testing instructions for Devpost

Devpost's form has no separate testing-instructions field. Its optional
Additional info field is labeled for existing-project upgrades, but the form
says Additional info is visible only to judges and organizers. It has a
255-character limit. A concise access note is saved there with a password
placeholder. **Personally replace that placeholder with the existing demo
password in Devpost and save it.** Do not paste a password into this
repository, a chat, or the public project story.

The fuller path below can be used during judge support if requested:

> Open the live demo URL above. When the browser asks for HTTP Basic Auth, use
> username `judge` and the password supplied in Devpost's private Additional
> info field. Start with **See an illustrative decision** for an instant
> walkthrough; all names, IDs, and ranks in that example are invented. Click
> **Start your own decision** for live Qloo evidence. A synthetic brief can use
> venue “Judge test listening room”, concept “jazz”, region “Brooklyn, New
> York”, and audience “millennials”. If a Qloo match chooser appears, select
> the music-genre jazz tag. Explore the options, open **Inspect Qloo evidence**,
> then run **Review the pilot choice**. To try the fixed-shortlist comparison,
> change the scenario region to “Los Angeles, California” and click **Compare
> scenario**. This creates synthetic saved decisions; please do not record a
> real-world outcome from the test.

The shared password must stay active through the judging period. The official
[rules](https://qloo.devpost.com/rules) explicitly permit a private test site
when credentials are provided in testing instructions. The
[overview](https://qloo.devpost.com/) says demos that rely on private access
do not qualify. The rules state that they prevail over inconsistent hackathon
materials, but the organizer retains final eligibility discretion. Keep the
demo externally reachable and make the credentials easy for judges to find.

## Submission gate

- [x] Hosted HTTPS demo, Qloo readiness, synthetic live journey, saved review,
  and backend persistence verified on 2026-10-29.
- [x] Public repository with visible MIT license.
- [x] Latest frontend contrast fix deployed; mobile width and keyboard focus
  checked on 2026-10-29.
- [x] Create Devpost project and fill its required fields. The saved draft
  preview renders its story and both links correctly.
- [x] User entered the existing demo password privately in Devpost and
  confirmed private-window sign-in to the live demo.
- [x] Upload the two invented-sample screenshots from `out/submission/` with
  captions that identify them as invented and not Qloo-backed. Both appeared
  in the saved Devpost preview.
- [x] Submitted before 2026-10-30 11:45 p.m. EDT (2026-10-31 9:15 a.m. IST).
  Devpost's receipt and submitted status were verified on the entry page.
