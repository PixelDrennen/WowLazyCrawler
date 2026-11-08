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
