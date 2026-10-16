# Qloo Contract — live-verified workflow shapes

> Status: TEMPLATE awaiting Phase 0 probes. Every entry must come from a real
> captured response, not documentation memory. When the harness CLI differs
> from IMPLEMENTATION.md §2.3, trust the CLI and update both.

Capture method: `qloo exec <workflow> --input-file <json> --json` from `probe/`,
outputs saved to `probe/out/<workflow>.<concept>.json` (gitignored; summarized
shapes get pasted here — redact nothing sensitive, there is nothing sensitive).

## Harness facts (fill during P0)
- Harness version installed: ``
- Exact CLI invocation syntax verified: ``
- Envelope statuses observed: ok / empty / needs_input / partial / degraded / error
- Error codes observed: ``
- Rate limits / quota signals observed: ``

## Workflows (one section per name from `qloo exec --help`)
### 1. find_tags
- real invocation: ``
- input schema (from a captured request): ```json
```
- output shape (field list only):
- jazz-probe result: 5 candidates, types = [ ]
- empty-result behavior: ``

### 2. describe
### 3. recommend
### 4. rank
### 5. where_popular
### 6. compare_audiences
### 7. audience_demographics
### 8. entity_tags
### 9. trends

## Open questions for P0 probes
- [ ] Do workflows accept stdin or only --input-file?
- [ ] What does `degraded` look like in practice?
- [ ] Do any workflows take demographic/audience URNs? Where do we get them?
