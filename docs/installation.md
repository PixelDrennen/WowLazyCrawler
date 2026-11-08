# Installation, updates and portability

## Fedora KDE Plasma desktop

Target: x86_64 Fedora KDE Plasma on Wayland, with XWayland fallback. The application uses Electron's normal native Wayland selection (Electron 38+); it does not force a display backend, require GNOME, disable SELinux, or disable Chromium's sandbox. Desktop identity is `wowlazycrawler.desktop`. The normal RPM dependency resolver installs the required GTK/NSS/GBM/audio libraries; GTK runtime libraries do not change your Plasma desktop.

1. Extract the `lazycrawler-linux-x64` Actions artifact from a successful build.
2. Run `sudo dnf install /absolute/path/to/wowlazycrawler-0.1.0.x86_64.rpm` (use the actual filename).
3. Open **WoW LazyCrawler** in Plasma's application menu. It starts the bundled backend and signs you in automatically.
4. Pin it to your task manager, or run `./scripts/install-rpm.sh /path/to/package.rpm --shortcut` to create a desktop launcher. On first launch, Plasma may ask you to mark the launcher trusted.

The AppImage is an alternative single executable. `chmod +x WoW-LazyCrawler-*.AppImage`, then double-click it in Dolphin. AppImage launch may need `fuse-libs`; `--appimage-extract-and-run` is an alternative when FUSE is unavailable. RPM is the preferred Fedora installation path because it provides menu integration and sandbox-helper installation through the system package manager.

Electron and Python are included in desktop packages. Build tools are needed only on the build machine. No privileged daemon is installed. The backend listens on loopback only. Closing Electron stops the backend it spawned; an independently running headless service is reused and left running.

**Validation boundary:** successful Linux builds and automated tests do not prove native Plasma behavior. Run the documented Fedora checklist before considering this version certified on a particular Fedora/Plasma release. No Fedora desktop session is available in the current build environment.

### Build on Fedora

Clone the repository and run `./scripts/build-fedora.sh`. The script installs build prerequisites with DNF, creates a local Python virtual environment, installs locked dependencies, runs tests and builds RPM/AppImage installers into `release/`. Python shared libraries and static web assets are bundled with PyInstaller. Node 24 is recommended; ensure `node --version` meets the Vite/Electron toolchain requirement.

CI builds on Ubuntu 24.04 (glibc 2.39). Target machines need glibc 2.39 or newer; modern Fedora meets that baseline. A locally built package inherits its build host's glibc minimum. Build on the oldest supported target rather than assuming a binary is portable to older Debian releases. ARM builds require a native ARM build runner and are not currently provided.

### Upgrade and uninstall

Install a newer RPM with `sudo dnf install ./new-package.rpm`. Rebuild/install from a branch only when its checks pass. Data lives outside `/opt` and is preserved across package upgrades. Version 1 schema is created idempotently; later schema changes must add explicit numbered migrations.

Uninstall with `sudo dnf remove wowlazycrawler`. User data is preserved. A manually created desktop shortcut can be removed separately. No auto updater or release channel is configured yet.

## Data location and migration

Default: `$XDG_DATA_HOME/wowlazycrawler`, or `~/.local/share/wowlazycrawler` when XDG_DATA_HOME is unset. `LAZYCRAWLER_DATA` can override it in desktop or headless mode. The data directory contains:

| File | Purpose |
| --- | --- |
| `crawler.sqlite`, `crawler.sqlite-wal`, `crawler.sqlite-shm` | SQLite database and live journal |
| `credentials.json` | Optional Blizzard client credentials; owner-only file |
| `admin-token` | Browser access credential; owner-only file |
| `server.lock`, `runtime.json` | Process ownership and loopback discovery; temporary runtime state |
| `backend.log`, `backend.log.old` | Desktop backend diagnostics; rotated at startup above 5 MB |

For a full migration, quit Electron and stop any headless service, then copy the entire data folder privately to the new machine. Do not copy a live SQLite database without its journal. Install the new RPM, put the data in the expected location, and launch. Copying program directories or Python virtual environments is unnecessary. Preserve directory ownership and mode 700, and credential/token modes 600. Stale runtime records are checked against process liveness and health; the file lock is released by the OS on exit.

### Backup and restore

**Settings → Download database backup** uses SQLite's online backup API and strips login sessions. The result contains configuration, recipes, history and observations. It excludes `credentials.json` and `admin-token`.

To restore, stop every LazyCrawler process. Move the existing data directory aside so its database and journals remain recoverable. Create a fresh data directory, copy the backup as `crawler.sqlite`, and start the application. Re-enter Blizzard credentials. A new admin token is generated. Do not leave old `-wal`/`-shm` files beside a restored database.

## Headless Linux server

For a source installation, create the virtual environment, install `requirements-runtime-lock.txt`, run `npm ci --prefix web` and `npm --prefix web run build`, then `./scripts/start-server.sh`. The default address is `127.0.0.1:8765`. Read the local `admin-token` file to sign in. Do not put this token in a URL or Git.

For a persistent user service: `./scripts/install-headless-service.sh`. Manage it using `systemctl --user {start,stop,status,restart} wowlazycrawler`; logs are in `journalctl --user -u wowlazycrawler`. Enable lingering with `loginctl enable-linger "$USER"` if it should continue after logout. It remains loopback-only. A file lock prevents multiple workers writing the same data folder; desktop can attach to the local service.

Optional Docker Compose: `docker compose up -d --build`. On Fedora, install Docker or a Compose-compatible Podman setup according to that vendor's documentation. The named volume avoids bind-mount SELinux labeling problems. Container listens on all interfaces internally, but the published host port binds only to `127.0.0.1`. Obtain the browser token with `docker compose exec lazycrawler cat /data/admin-token`. Container and desktop data folders are independent unless explicitly migrated. A host desktop does not auto-discover the container's separate volume.

Remote management: prefer an SSH tunnel, e.g. `ssh -L 8765:127.0.0.1:8765 user@server`. Public HTTPS reverse-proxy hosting is not preconfigured. Do not expose port 8765 publicly. For a custom HTTPS proxy, forwarded scheme/host must remain consistent for the same-origin check and secure session cookies.

## Troubleshooting

- **Blank/failed startup:** inspect `backend.log` and run the app from a terminal. Keep normal user ownership on the data directory.
- **Already running:** open the existing app; it is a single-instance desktop application. If another process owns the same data directory, stop it or use a separate directory.
- **Wayland issue:** launch `wowlazycrawler --ozone-platform=x11` to test XWayland. No system-wide display changes are needed.
- **Sandbox helper errors:** use the RPM installed through DNF and normal user launch. Do not use `--no-sandbox`, run Electron as root, or disable SELinux. Report the full error and distro version.
- **No candidates:** confirm different auction markets, at least one selling realm, valid slugs, healthy feeds, and age/ROI/demand limits. Region context has its own 72-hour age allowance; realm prices default to 12 hours.

## Upgrade to 0.3.0 and connect the addon

The 0.3.0 RPM upgrades the same package and retains the same XDG data directory. Schema v2 adds capture/character/telemetry tables alongside existing data. No old market history or user configuration is deleted. Realm selections in old settings are deprecated and no longer restrict coverage. Legacy demo configuration is ignored; all normal views show real observations and missing-data issues.

Open **Addon connection**, choose the `_retail_` folder (or the parent World of Warcraft folder), save, and close WoW before clicking **Install / update addon files**. A native folder chooser is available in Electron. The app verifies a Retail executable and safe paths before copying only its own addon directories. Existing first-party addon folders are retained as `.previous` rollback copies; SavedVariables are untouched.

Enable `LazyCrawler` and `LazyCrawler Data` in the character-screen addon list and run `/lc`. The standalone `LazyCrawler-addon.zip` is included beside desktop installers if manual installation is preferred. Bank/mail/profession observations happen in game; a reload/logout flushes the export. The companion atomically publishes the separate data file while playing. Wait for bundle publication, then /reload to load it. If the first reload just exported new captures, allow about 20 seconds for import/publication, then reload again.

All views show actual connected data; no demonstration characters, graphs or prices are substituted. Capture completeness and age remain visible, including unopened mailboxes and banks. The addon is an early client-validation build; run the native tests before relying on purchases, bank movement or posting with valuable items.
