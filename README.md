# WoW LazyCrawler

A self-hosted WoW Retail auction and crafting workspace, with an Electron desktop application for Fedora KDE Plasma and an optional headless Linux server.

## Install on Fedora KDE

Download the `lazycrawler-linux-x64` artifact from a successful **Validate and package** run in [GitHub Actions](https://github.com/PixelDrennen/WowLazyCrawler/actions). Extract the artifact, then install the RPM:

```sh
sudo dnf install ./wowlazycrawler-*.rpm
```

Launch **WoW LazyCrawler** from Plasma's application menu. Python and the dashboard are bundled; no browser, Node.js, Python install, or Docker is needed on the target desktop. For an optional desktop shortcut, use `scripts/install-rpm.sh /path/to/package.rpm --shortcut` as your normal desktop user.

For a source build on Fedora:

```sh
./scripts/build-fedora.sh
./scripts/install-rpm.sh release/wowlazycrawler-*.rpm --shortcut
```

See [installation and migration](docs/installation.md) for exact build prerequisites, headless deployment, backups, Wayland/X11, and troubleshooting. Native Plasma validation is tracked explicitly in [testing](docs/testing.md).

## First session

1. In **Data sources**, add US realm slugs such as `area-52` and `stormrage`; mark your selling realms. Save.
2. Set a budget, per-item investment limit, minimum ROI, and freshness limits in **Settings**.
3. Click **Scan markets**. TSM public CSVs need no API key. Blizzard integration is optional and requires your own client credentials.
4. Review **Opportunity radar** and its evidence/risk details. Verify exact item variants, binding, live prices, and transfer eligibility in game.
5. Add a verified recipe simulation in **Crafting planner** to calculate material costs, missing reagents, estimated profit, and incremental concentration value.

No demonstration prices or fabricated sales are inserted. An empty candidate list can be the correct result.

## What this milestone does

- Persistent configuration and market history; conditional HTTP fetches, retries, daily realm mapping, scheduled/manual scans, error recovery and diagnostics.
- Separate realm, regional-context and commodity pipelines; a Blizzard snapshot adapter preserving item variants.
- Conservative, explainable **base-item TSM candidate** calculations with demand, age, fee, budget and connected-realm checks. Unknown transfer eligibility is flagged for review.
- Manual character-specific crafting estimates, material shopping plans, owned-material opportunity costs and incremental concentration analysis.
- Responsive React dashboard, replayable setup guide, authenticated management, secret redaction, consistent SQLite backup and versioned planning export.
- Electron starts and authenticates its backend, reuses an existing local headless instance, and manages its owned process. RPM and AppImage packaging; source and container headless modes.

## Scope still ahead

The WoW addon and companion sync are **not implemented**. Neither are live CraftSim/Auctionator integration, inventory capture, sale tracking, variant-level trade matching, transfer eligibility verification, crafting dependency graphs, Knowledge optimization, or a portfolio allocation solver. Those remain explicit milestones, not hidden mock features. See [roadmap](docs/roadmap.md).

## Develop

Python 3.12+ and Node 24 LTS:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
npm ci
npm ci --prefix web
npm run desktop
```

Run Electron as a normal user. Never disable its sandbox. On a headless machine, build the web assets and run `./scripts/start-server.sh`, then use `http://127.0.0.1:8765`. The browser login token is `~/.local/share/wowlazycrawler/admin-token`. Keep it private.

```sh
.venv/bin/python -m pytest -q
npm --prefix web run build
node --check desktop/main.cjs
npm run package:linux
```

Contribute through `feature/*`, `fix/*`, or `patch/*` branches and pull requests targeting `main`. CI validates code and builds installers as Actions artifacts; there is no automatic release publishing or desktop updater.

## Technical reference

- [Architecture, schema and API](docs/architecture.md)
- [Data sources and research](docs/research.md)
- [Installation, migration and recovery](docs/installation.md)
- [Tests and compatibility checklist](docs/testing.md)
- [Roadmap and acceptance criteria](docs/roadmap.md)

This original application is not affiliated with Blizzard or the addons it may integrate with. No proprietary addon assets are bundled. Redistribution licensing has not yet been selected (`UNLICENSED`).
