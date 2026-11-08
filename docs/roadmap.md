# Roadmap and acceptance criteria

## Milestone 1: local server and desktop management (this branch)

Deliver a runnable backend and Electron dashboard, TSM ingestion, optional Blizzard adapter, persistent settings and observations, manual crafting estimates, conservative trade candidates, backup/export and installable Linux packaging.

Acceptance: authenticated configuration; source failure preserves previous data; duplicate scans are blocked; commodities never cross realm boundaries; stale observations excluded; unknown demand not fabricated; owned stock has a cost; backup is consistent; bundled backend serves assets from a moved installation path. Fedora RPM/Wayland/desktop checks are recorded separately from host automation.

## Milestone 2: addon and safe transport

- Modular Lua foundation, reusable UI, lifecycle and SavedVariables migrations.
- Versioned manual import/export transport before automatic file sync.
- Linux companion with atomic writes, explicit WoW-closed detection, interrupted-sync recovery and diagnostics.
- Authoritative inventory/binding and transfer-eligibility evidence.

Acceptance: malformed/oversized/unsupported-version imports rejected without destroying state; inventory freshness and ownership explicit; no live SavedVariables overwrites; no prohibited automated gameplay.

## Milestone 3: first-class crafting integration

- Verify installed CraftSim and Auctionator supported APIs and licenses; capability-detected adapters and graceful absence behavior.
- Import character-specific recipes, quality, yield, equipment, concentration and simulations.
- Consolidate material requirements across queues and deduct one shared inventory snapshot exactly once.
- Produce an isolated Auctionator shopping list; preserve unrelated lists and internal quantities.
- Dependency DAG with cycle detection, craft-versus-buy intermediate analysis and production budgets.

Acceptance: Hanami/Noraxei plans can be compared with CraftSim at matched inputs; missing character information disables unsupported estimates; output quality and reagents remain exact; shared inventory is not double counted.

## Milestone 4: executable market evidence and unified planning

- Join exact item variants to authoritative metadata; special handling for battle-pet species/level/breed.
- Current listing verification in game, shared AH cluster exclusion and quantity-aware acquisition costs.
- Inventory-aware destination allocation, per-realm exposure, duplicate caps and a portfolio budget solver.
- Compare crafting and buying the same exact output through the same fee/risk model.

Acceptance: the entire selected portfolio stays within available capital, stock and realm constraints; every action exposes source/time/uncertainty; no per-realm commodity arbitrage.

## Milestone 5: analytics and polish

Realized sales and inventory aging; concentration scheduling and Knowledge investment comparisons; optional alerts; backtesting/calibration; tutorial anchors and recovery; addon compatibility testing with TSM, Auctionator, Syndicator and bank interfaces. Add animations only within measured frame budgets. Predictive features must demonstrate value against deterministic baselines.

## Workflow

Use `feature/*` for new features, `fix/*` for bugs and `patch/*` for maintenance. Open a PR, validate, merge into `main`. CI uploads development installers only; releases and automatic updating require a later deliberate setup. Keep documentation describing the final behavior rather than abandoned designs.
