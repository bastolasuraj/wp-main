#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p automation/logs
python3 automation/cybersecurity_autopost.py --post-status publish --codex-timeout-seconds 900
