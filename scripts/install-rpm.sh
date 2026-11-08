#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID} -eq 0 ]]; then
  echo 'Run as your normal desktop user. This script uses sudo only for the RPM install.' >&2
  exit 1
fi
if [[ $# -lt 1 || ! -f $1 || $1 != *.rpm ]]; then
  echo 'Usage: ./scripts/install-rpm.sh /path/to/lazycrawler.rpm [--shortcut]' >&2
  exit 1
fi
package_path=$(readlink -f -- "$1")
sudo dnf install -y "$package_path"
if [[ ${2:-} == --shortcut ]]; then
  desktop_dir=$(xdg-user-dir DESKTOP)
  if [[ -z $desktop_dir || $desktop_dir == "$HOME" ]]; then
    echo 'No dedicated desktop folder is configured. Use the Plasma application menu.' >&2
    exit 0
  fi
  mkdir -p -- "$desktop_dir"
  install -m 755 /usr/share/applications/wowlazycrawler.desktop "$desktop_dir/WoW-LazyCrawler.desktop"
  echo 'Desktop shortcut created. Plasma may ask you to confirm that this launcher is trusted on first use.'
fi
echo 'Installed. Launch WoW LazyCrawler from the application menu.'
