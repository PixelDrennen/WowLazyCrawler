#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")/.."
if [[ ! -f /etc/fedora-release ]]; then
  echo 'This build helper targets Fedora. See docs/installation.md for other Linux hosts.' >&2
  exit 1
fi
sudo dnf install -y nodejs npm python3 python3-pip python3-devel gcc binutils rpm-build libxcrypt-compat gtk3 nss alsa-lib libXScrnSaver libXdamage libXrandr mesa-libgbm libdrm libxkbcommon at-spi2-atk xdg-utils
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
npm ci
npm ci --prefix web
.venv/bin/python -m pytest -q
npm run package:linux
echo 'Built installers in release/. Install the RPM with scripts/install-rpm.sh release/<filename>.rpm --shortcut'
