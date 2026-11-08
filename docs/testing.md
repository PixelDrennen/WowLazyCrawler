# Verification and compatibility

## Automated checks

Run `python -m pytest -q` in the project virtual environment. The initial suite covers CSV schemas and copper values; region-demand parsing; malformed/future snapshots; commodity exclusion; missing demand; stale data; conservative caps, budget and same-AH exclusions; variant preservation and bid-only handling; crafting opportunity cost and incremental concentration; missing prices; authentication, rate limit, same-origin rejection, logout, secret redaction and file permissions; configuration bounds; backup integrity/session stripping; snapshot/history deduplication; changed-feed recovery; HTTP 304 observation-age preservation; retry, scan overlap, persistent walkthrough state and interruption-safe shutdown.

`npm --prefix web run build` performs strict TypeScript checking and a production build. `node --check desktop/main.cjs` and `bash -n scripts/*.sh` verify launcher syntax. Dependency manifests and lockfiles pin both toolchains. CI runs these and produces RPM/AppImage development artifacts. It never publishes a GitHub release.

After bundling, `.venv/bin/python scripts/smoke-bundle.py build/backend/lazycrawler-server` copies the backend into a different directory with spaces in its name, starts it, verifies HTML and APIs, signs in, checks the attachment export and verifies duplicate-worker rejection. It stops the process afterward. This is a relocation test, not a cross-distro or desktop UI test.

The Linux build environment has no Fedora Plasma session. Browser-based visual inspection could not connect to the workspace's loopback preview; therefore renderer interaction/layout, Electron window lifecycle, native Wayland, Dolphin shortcut trust and DNF integration remain manual checks. No passing claim should be inferred for those rows below.

## Fedora KDE acceptance checklist (pending native testing)

| Area | Required check |
| --- | --- |
| RPM install | DNF resolves dependencies, creates one menu entry, uses bundled Python, no root app launch |
| Wayland | Login to Plasma Wayland, open via menu/desktop/pinned icon, correct icon grouping, no extra browser |
| Scaling | Check 100%, 150%, 200% scaling and mixed-DPI monitors; minimum-size window controls remain usable |
| XWayland | Launch with `--ozone-platform=x11` and confirm fallback without system changes |
| First run | Walkthrough continues/skips/replays; completion persists; no invisible overlay blocks controls |
| Market settings | Add/remove realms, mark selling realms, reject malformed slugs, save and restart |
| Scanning | Manual and scheduled runs, network offline/restore, upstream 429/5xx, restart mid-scan |
| Tables and drawers | Search, scrolling, candidate details, timestamp readability, Escape and focus behavior |
| Crafting | Import/edit/delete valid estimates; show validation errors; missing prices suppress profit |
| Backup | Download consistent snapshot, restore into a fresh data folder, verify settings/history/recipes |
| Upgrade | Install newer RPM; data survives and no duplicate menu entry appears |
| Migration | Move data to another Fedora machine; new install reads existing history and plans |
| Lifecycle | Second launch focuses existing window; close kills owned backend; existing headless service survives |
| Privacy | No secrets in API payloads, screenshots, exports, Git or diagnostic summaries |

Blizzard ingestion still requires the user's client credentials and a live authenticated endpoint test. CraftSim/Auctionator APIs and in-game addon compatibility have not been integrated or tested in this milestone.

## 0.2.0 addon/control-plane validation

The expanded suite runs actual addon Lua in a Lua 5.1 runtime with a mocked WoW API surface. It checks server-valid JSON exports, combat deferral, partial mailbox and COD semantics, bank snapshots surviving unavailable tabs, shared stock counted once, bound/unknown stock on other characters excluded, observed-recipe/decor/material capture, same-cluster/expired-route rejection, matching sale-money collection, page construction and pooled row reuse.

Backend tests cover all-region catalog grouping and Gurubashi connections; characters determining owned markets; demo/live isolation through the outgoing bundle; per-source older/omitted observations; warbank identity/deduplication; unknown identity conservatism; snapshot version/time validation; time-weighted session rates and sample deduplication; safe Lua-string decoding including UTF-8 decimal byte escapes; installer/write rejection while WoW runs; stable export reading; obsolete realm settings ignored by scans; catalog schema-failure recovery; and preserving v1 settings during schema-v2 upgrade.

`smoke-bundle.py` also checks the bundled catalog/admin view, demo/live separation and embedded addon source after relocating the executable. CI packages the addon ZIP beside RPM/AppImage and verifies RPM desktop/backend entries. The GUI renderer and real WoW protected API/layout behavior are **not** certified by these tests. No native feature-complete claim is made. Validate the workflow using low-value items before relying on posting or transfer actions.

## 0.3.0 session and capture regression coverage

New Lua tests exercise pause/resume and restart timing, exclusion of offline time, timer-free discovery, observed-stock/gold phase gates, partial-stack withdrawals, 500g wallet top-up arithmetic, paused action rejection, stale CraftSim rejection, minimum-stock planning, unavailable bank-money/mail-header preservation, compact-window bounds, conditional scrollbar visibility and full-result-only undercut checks excluding owned listings. Backend tests cover live-only defaults and legacy demo settings, running-client data publication with executable-install rejection, and real-price crafting discovery with unresolved reagent quality left unknown.

Native WoW visual rendering, protected bank actions, the user's installed TSM/CraftSim versions and Fedora KDE installation remain manual acceptance checks. Automated Lua frames are mocks, not an in-game screenshot or certification.

## 0.3.1 market readiness and bundle acknowledgement

Regression tests separate a loaded empty bundle from missing transport, distinguish missing/stale prices and uncovered character markets from filtered zero matches, preserve feed errors and refresh guidance, and verify that unchanged captures do not rewrite the data file. The addon exports its loaded bundle identity; the desktop distinguishes publication from an acknowledgement saved by the client. Changed data files are repaired even when the semantic planning payload is unchanged. Expired routes are hidden from actionable Radar results.

## 0.4.0 automatic updates and live transfer

Node tests exercise update readiness gating, automatic-check preferences, progress, retained downloaded state and errors. Python/Lua regressions cover automatic installation while WoW runs, two-directory rollback, disabled auto-install, SavedVariables preservation, live market import and persistence, immediate capture export, malformed/code-text/region/older-bundle rejection and Unicode JSON decoding. CI verifies both RPM/AppImage entries in latest-linux.yml and the pinned GitHub app-update.yml provider, then publishes stable assets only after successful main packaging. Native KDE polkit/package-manager behavior, next-release replacement and WoW clipboard/protected-action acceptance require manual checks.
