#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "$(readlink -f -- "$0")")/.." && pwd)
if [[ $project_root == *'%'* || $project_root == *$'\n'* || $project_root == *'"'* || $project_root == *'\\'* ]]; then
  echo 'Move the checkout to a path without percent signs, quotes, backslashes, or newlines.' >&2
  exit 1
fi
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/wowlazycrawler.service" <<EOF
[Unit]
Description=WoW LazyCrawler market server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart="$project_root/.venv/bin/python" "$project_root/server_entry.py"
WorkingDirectory="$project_root"
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now wowlazycrawler.service
echo 'User service installed at http://127.0.0.1:8765. Use loginctl enable-linger for operation after logout if desired.'
