# Architecture and contracts

## Decisions

- **FastAPI + SQLite WAL:** one lightweight process, transaction-scoped connections and a single worker; portable personal deployment. SQLite has an online backup API and no daemon configuration. PostgreSQL/Redis remain a future option for multi-user/all-region workloads. Do not run multiple uvicorn workers.
- **React + TypeScript + Vite:** local assets, original reusable components, Lucide icons. No runtime CDN or network font dependency. A restrained green/cyan dark palette, rounded panels, accessible labels, keyboard Escape dismissal, responsive columns and reduced-motion support form the initial design system.
- **Electron:** isolated sandboxed renderer with Node integration off. Main process owns backend lifecycle, authenticates using a private token, installs an HTTP-only session cookie, prevents cross-origin navigation, and allows only specific HTTPS documentation destinations to open externally. No renderer filesystem bridge or unrestricted IPC.
- **Bundled backend:** PyInstaller onedir includes Python dependencies and web assets. electron-builder includes that tree as resources and emits RPM/AppImage. Data lives in a stable XDG directory; it is never written into the installed app.
- **Worker:** async scheduler checks every 15 seconds; one non-overlapping ingestion task, serial feeds, retry/backoff, HTTP ETag/Last-Modified validators, transactional snapshot replacement and historical deduplication. Cancelled jobs are recovered as interrupted on startup. A process file lock guards each data folder.

## Schema v1

| Table | Identity and purpose |
| --- | --- |
| migrations | Numbered schema versions and application times |
| settings | JSON configuration values; no Blizzard secrets |
| sources | Source ID, HTTP validators, latest attempt/success, status, row count and sanitized errors |
| observations | Current `(region,scope,realm,item_key,source)`; copper prices, optional demand, quantity, upstream/fetch timestamps |
| history | Unique source observation by region, scope, realm, item identity and upstream time; indexed item/time |
| realms | Dynamic region/slug → connected-realm ID mapping |
| jobs | Latest 100 ingestion jobs, timestamps, state and error summaries |
| recipes | Validated version-1 manual recipe plan JSON |
| metadata | Reserved transfer-eligibility facts; no automatic assumptions or UI editor yet |
| sessions | SHA-256 hashes of 24-hour session credentials |

Scopes: `realm`, `commodity`, `region`. TSM item IDs are base IDs and cannot safely resolve gear variants. Blizzard non-commodity identity preserves the complete item object including modifiers, bonuses and battle-pet fields. Pet species CSV ingestion is deferred; pets from base item feeds must not be treated as species-level trading evidence. The initial candidate engine uses only TSM base-item observations; Blizzard auctions are collected independently for later exact-identity analysis. This prevents unsafe joins between base IDs and distinct variants.

Money is stored in copper, not floating-point gold. User inputs and crafting estimates use gold and are explicitly labeled estimates. Unknown metrics remain null. Source replacement and history inserts are one transaction, so malformed/changed upstream files leave the previous snapshot intact.

Retention removes historical rows older than configured days after each scan; current snapshots persist and are filtered for staleness. Source records from disabled feeds remain visible for diagnostics but cannot supply active calculations. Changing region filters the analysis immediately.

## API v1

The same-origin dashboard is served at `/`. APIs are under `/api`; management routes require an HTTP-only, SameSite=strict cookie. Mutations reject a different Origin, login is limited to 10 attempts/IP/minute, secrets are never returned. There is no default public management binding. `/openapi.json` is the generated shape reference; authenticated `/api/contract` provides the same schema from within the workspace.

| Endpoint | Method | Contract |
| --- | --- | --- |
| health | GET | Public status/version/database liveness |
| login / logout | POST | Local token → session cookie; session invalidation |
| settings | GET, PUT | Validated complete config; PUT fills omitted defaults |
| credentials | PUT | Replace Blizzard client credentials; blank values clear them |
| status | GET | Service, memory/disk/database, feeds and jobs; no secrets |
| scan | POST | 202 job scheduled; 409 overlap; 422 no source enabled |
| realms | GET | Cached selected-region discovery catalogue |
| opportunities | GET | Top 500 ranked estimates with assumptions, risks and oldest evidence timestamp |
| history/{item_id} | GET | Latest 500 base-item observations for selected region |
| recipes | GET | Stored recipe plans |
| recipes/{id} | PUT, DELETE | Validated plan upsert/delete; request path and payload ID must match |
| crafting | GET | Manual recipe estimates and missing-material plans |
| export | GET | Download schema_version=1 planning JSON; not an addon payload |
| backup | GET | Consistent SQLite attachment, excluding session rows |

Validation models in `server/models.py` define accepted bounds, field types and defaults. Region changes do not delete history. Recipe materials require unique quality-specific item IDs and explicit quantities. Each recipe independently deducts its owned quantities; **do not reuse the same inventory ownership across multiple plans**. Shared inventory allocation is deferred until authoritative addon snapshots exist.

## Initial analysis

Entry: observed TSM realm minimum buyout. Exit: 90% of the lowest positive destination buyout/market/history and regional market/history/average-sale value. Net subtracts entry, configured auction cut and a configurable deposit reserve. Require fresh realm evidence and separately fresh daily regional context, minimum sold/day, inverse regional-demand cap, ROI, budget and per-item limits. Exclude known same-connected-realm pairs. Rank by net × min(regional sold/day,1) ÷ (1 + risk count).

This is a heuristic, not a calibrated sale probability, time-to-sale model, actionable order or portfolio allocation. Every transfer remains unverified until an authoritative in-game capability check. No purchase queue implies quantities can be bought from a snapshot. Candidate rankings do not jointly enforce a total portfolio budget.

Crafting cost values all materials including owned stock. Cash required uses missing quantities. Estimated yield, sell price and concentration come from an explicit user simulation; no expansion mechanics are invented. Incremental profit per concentration requires a baseline **total profit for the entire plan**, not baseline per craft. Missing/zero reagent prices suppress profit rather than assuming free ingredients. Non-commodity reagent prices must be entered manually until realm-specific material lookup is added.

## Future addon/companion boundary

Server remains the analysis source of truth. A versioned companion exchanges bounded, validated inventory/simulation snapshots and recommendation bundles. A WoW addon cannot make arbitrary HTTP calls. No live SavedVariables rewriting, filesystem injection, or unattended purchases/posting will be implemented. Prefer explicit user import for initial transport, then an offline-safe companion with atomic writes, WoW process checks, checksums and schema migrations. CraftSim integrations must use documented APIs at a tested version; unsupported fields are unavailable, not inferred.
