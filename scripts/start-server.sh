#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "$(readlink -f -- "$0")")/.." && pwd)
exec "$project_root/.venv/bin/python" "$project_root/server_entry.py" "$@"
