# Addon-first architecture

## Product boundary

The player experience lives in the WoW addon. The server discovers regional markets, stores observations, evaluates opportunities and produces compact planning data. Electron is the administration/control surface, with read-only reviews of characters, opportunities, crafting and workflow progress.

No realm-selection or manual inventory/crafting entry is needed in the dashboard. It configures server policies and connection settings, not the player's moment-to-moment buying, transferring, posting or crafting.

## Region coverage

The shipped catalog was extracted from TSM's public realm metadata on 2026-11-08: 246 US, 267 EU, 18 KR and 27 TW realms. Region scans group all realms by their auction-house identity and download one representative realm CSV per group. The public-page metadata parser is schema-checked, never executes JavaScript, refreshes daily, and retains the last known catalog if the page changes. It is not presented as a stable public TSM catalog API. The data source's URL and observation time remain visible.

TSM auction-house IDs use a **negative namespace** in `realms.connected_id`, distinct from positive Blizzard connected-realm IDs. Blizzard's authenticated discovery is stored separately in `blizzard_realms`; TSM IDs are never sent to Blizzard endpoints. The scanner ignores obsolete v1 realm-selection fields. Unknown character realm names are not guessed into a cluster.

Character observations determine covered clusters. Candidate routes compare owned clusters against other distinct clusters in both directions; at least one side must be owned. An uncovered source or destination is marked as requiring an alt. No same-cluster or regional-commodity arbitrage is generated. This is still a conservative candidate model, not a portfolio allocation solver or exact-variant execution guarantee.

## Storage and financial observations

Schema v2 preserves all v1 tables and adds:

| Table | Purpose |
| --- | --- |
| characters | Addon account/character identity, region, realm, class, professions and last synchronization |
| captures | Timestamped `(owner,scope)` snapshots; items, money, completeness and explanatory notes |
| addon_recipes | Known recipe observations and available simulations by character |
| addon_tasks | In-game workflow state by account and task |
| lumber_samples | Deduplicated, attributed session quantities and durations |
| sync_events | Recent transport/capture activity |
| telemetry | Ingestion counters over time |
| blizzard_realms | Separate authoritative endpoint identifiers for Blizzard calls |

Capture scopes include bags/wallet, character bank, reagent storage, mailbox, auctions, equipped items, viewed guild bank and shared warbank. An omitted source preserves its last observation; an older capture cannot replace a newer one. Unknown data is distinct from an observed empty container. Guild assets are outside the personal balance. Mail money is receivable, not spendable wallet gold. COD attachments are not usable stock.

Warbank uses a Battle.net-derived group identifier when available, once across characters/accounts in that group. If an account identity cannot be established, one conservative unresolved-region group is retained rather than summing potentially duplicate banks. The dashboard reports that unresolved group; this is not a claim to have identified unrelated accounts.

## Transport and safety

The addon writes a versioned JSON string inside its own SavedVariables. A reload/logout is the disk-save boundary. The companion waits for stable files, parses **only the escaped JSON string**, validates schema/size/time bounds and never evaluates Lua.

Outgoing plans use a separate `LazyCrawler_Data` addon. The companion atomically replaces only its generated `Data.lua`, even while WoW is running; the client loads it on its next reload/start. Executable addon installation still requires the client closed. SavedVariables are never modified by the server. Dashboard and transport both use real observations, regardless of a legacy demo setting.

The desktop's folder-picker IPC exposes one narrow operation, verifies the calling window's origin and retains sandbox/context isolation. Install/update rejects running WoW and unsafe symlinked targets, backs up the previous addon folder, and leaves user SavedVariables intact. The companion's file path setting is explicit; it does not search arbitrary personal directories.

There remains a small inherent process-start race around any file replacement. Users should keep the client closed while installing/updating; native in-game and process detection validation is required. The implementation does not claim an OS-level launch lock with Battle.net.

## Read models and API additions

All `/api/` management endpoints except health/login retain session authentication and same-origin mutation checks.

| Endpoint | Method | Behavior |
| --- | --- | --- |
| admin | GET | Demo/live review envelope, plus always-live service and companion diagnostics |
| addon/snapshot | POST | Validated schema-v2 observation import |
| addon/plan | GET | Always-real schema-v2 bundle; never demonstration records |
| companion | GET | Actual process, watcher, sync and pending-write status |
| companion/install | POST | Install/update first-party addon files with WoW closed |
| settings | GET/PUT | Region service, policy, theme and companion configuration |

Legacy recipe and inspection-export endpoints remain for v1 compatibility; the new UI does not use them for player workflow creation. `addon/plan` is the transport contract. Demo presentation has been removed. Missing inputs remain empty/unknown with diagnostics. Session state is saved in the addon and exported as a task record; elapsed play time is checkpointed and excludes offline gaps. Native auction-key scan results are session/realm bounded; a player acknowledgement covers the separate TSM review.
