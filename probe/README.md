# probe/ — Phase 0 throwaway probe scripts

Purpose: run each of the nine `qloo exec` workflows live once, capture raw
stdout JSON to `probe/out/<workflow>.<concept>.json` (gitignored), then paste
compact shape summaries into `../docs/qloo-contract.md`.

## Setup (prereqs)
- Node 22.19+ installed
- `npm install --global @qloo/qloo-harness` (>= 0.1.26)
- Shell env: QLOO_BASE_URL + QLOO_TRUSTED_BASE_URL set (see IMPLEMENTATION.md §2.1)
- `qloo setup --qloo` completed → `qloo setup --status` shows "Qloo data: ready"
- Real key in ../.env (QLOO_API_KEY line)

## Run order (after P0 task 4 is done)
1. `qloo exec --help > probe/out/help.txt` — record exact names/flags
2. `probe/find_tags jazz` (kit canonical case), then `probe/find_tags "natural wine"`, `"tacos"`, `"listening bar"`
3. `describe`, `recommend`, `rank`, `where_popular`, `compare_audiences`, `audience_demographics`, `entity_tags`, `trends` — one concept each, input built from find_tags outputs of step 2
4. One deliberately obscure concept for the empty/needs_input envelope case
5. Update `../docs/qloo-contract.md` in the same session

Conventions:
- probe scripts are thin cmd/ps shims around `qloo exec`; nothing smart here
- never run probes in a loop; quota hygiene (IMPLEMENTATION.md §10)
