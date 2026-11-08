# WoW LazyCrawler

LazyCrawler is an **in-game economic workflow addon**, backed by a self-hosted market server. The Electron dashboard is its administrative companion: configure refreshes, inspect data health, and review what characters are doing in game.

## Install / upgrade on Fedora KDE Plasma

Download the `lazycrawler-linux-x64` artifact from a successful [Validate and package](https://github.com/PixelDrennen/WowLazyCrawler/actions) run and extract it:

```sh
sudo dnf install ./wowlazycrawler-0.3.1.x86_64.rpm
```

Open **WoW LazyCrawler** from Plasma's application menu. The backend and dashboard are bundled; no external browser, Python or Node installation is needed. AppImage is included as an alternative. Desktop shortcuts, source builds, headless service, migration, and recovery are covered in [installation](docs/installation.md).

The existing desktop identity and XDG data directory remain unchanged, so the RPM upgrades previous versions in place. SQLite schema v2 adds addon observations without discarding prices or configuration.

## Administrative workspace

- Region-wide discovery: all supported realms are grouped into distinct auction houses. One representative feed per cluster; no manual realm-selection list.
- Automatically discovered characters determine covered markets. Gurubashi and its connected realms are one auction market, excluded from comparisons with each other.
- Character wallets, banks, shared warbank, mailbox attachments/receivables, auctions, equipped items and viewed guild storage have separate capture timestamps and completeness.
- Opportunity radar and crafting views are **read-only reviews** of addon context. Manual recipe JSON entry has been removed from the UI.
- Dedicated housing production and lumber views, with time-weighted gathering estimates and source attribution.
- Service refresh intervals, concurrency, data retention, price freshness, credentials, health, diagnostics, charts and backups.
- Grove, Spectral and Ember palettes; the established desktop installation and visual language are preserved.

The dashboard displays live observations only, including after upgrading an older demo-enabled configuration. Missing captures, unknown balances, failed feeds and unpublished bundles are visible issues; no synthetic records replace them.

## Connect the addon

1. Close WoW. In **Addon connection**, choose your Retail folder (or its parent World of Warcraft folder) and save.
2. Click **Install / update addon files**. Alternatively extract `LazyCrawler-addon.zip` into `_retail_/Interface/AddOns/`. It contains `LazyCrawler` and `LazyCrawler_Data`.
3. Enable both addons on the Retail character screen. Run `/lc` in game.
4. Log into characters normally. Open bank, mailbox, auction house and professions when needed; accessible data is captured automatically. No character/inventory forms are required.
5. A reload/logout saves the addon export. The companion reads stable SavedVariables without executing Lua or overwriting those files.
6. Run or schedule a region refresh. Recommendations are written atomically into the separate data addon, including while WoW is running. Wait for **bundle ready**, then `/reload` to load them.

WoW addons cannot make arbitrary HTTP calls. This is an automatic file-based exchange with an explicit game-save boundary, not a false promise of live HTTP or live code injection. Only the separate data file can update while playing; installing executable addon files still requires WoW to be closed. SavedVariables are never written by the companion.

## In-game addon (early client-validation build)

Market readiness is separate from file transport: Radar and the dashboard identify missing/stale regional prices, uncovered character markets, disabled pricing, feed errors, and valid zero-match results. Addon connection compares the published bundle with the last identity acknowledged by the addon. Unchanged captures do not publish an identical bundle with a new timestamp.

The compact task window has a permanent character/warbank/mail gold header, rounded controls, native icon textures, neutral palettes and an overflow-only scrollbar. Start **Realm flip**, **Posting**, or **Craft available** sessions, with persistent elapsed time, pause/resume and stop controls. Time offline is excluded. Targets can change during a run: minimum stock defaults to 1, bulk acquisition to 3, and posting wallet to 500g. Bank actions move one stack per click; oversized withdrawals split into a free bag slot and wallet top-ups withdraw only the difference. Unavailable routes can be skipped.

Realm runs group queued routes by distinct market, guide buying and consolidation across source alts, then withdrawals, TSM posting and undercut review across destination alts. Missing characters are identified. Purchases and TSM posting remain player actions. Live auction-key undercut checks are available per posted variant; partial results never report a completed scan, and the TSM review is explicitly acknowledged by the player.

Craft available selects fresh profitable CraftSim observations from learned, enabled recipes on the current character, prepares minimum-stock quantities and materials, checks output stock, then guides warbank consolidation. **Explore crafting** has no timer: captured learned/unlearned recipes across characters are ranked by price-backed estimated profit and regional demand, with requirements detail and explicit unknowns. It does not invent an unseen global recipe catalog or choose reagent quality tiers.

Wallet gold and warbank gold are separate from mailbox receivables. COD attachments, guild storage, equipped items and auctions are excluded from usable crafting stock. Cross-character bound/unknown-transfer items are excluded, and stale stock is not silently considered available. Shared bank identity uses the Battle.net account identifier when available; unresolved accounts conservatively share one unknown-region bank group instead of multiplying its funds.

**This is not yet certified feature-complete.** The Lua code is tested in a Lua 5.1 harness, not a real WoW client. Native protected actions, actual layouts, profession integration versions and external lumber-adapter behavior need in-game verification. See [feature status](docs/feature-status.md) for implemented behavior and outstanding work, including full crafting simulation/quality optimization and multi-character production scheduling. No unsupported integration is advertised as working.

## Development

Python 3.12 and Node 24:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
npm ci
npm ci --prefix web
npm run desktop
```

Validation / packaging:

```sh
.venv/bin/python -m pytest -q
npm --prefix web run build
npm run package:linux
```

Use `feature/*`, `fix/*` and `patch/*` branches with PRs into main. CI produces development RPM, AppImage and addon ZIP artifacts. No release channel, auto-updater, billing system or paid addon lock is enabled.

## Reference

- [Architecture and contracts](docs/architecture.md)
- [Addon and transport](docs/addon.md)
- [Feature completeness and verification](docs/feature-status.md)
- [Installation and migration](docs/installation.md)
- [Research and source notes](docs/research.md)
- [Testing](docs/testing.md)
- [Roadmap](docs/roadmap.md)

Original code and visual assets; no proprietary addon implementations are bundled. Redistribution licensing is not selected (`UNLICENSED`).
