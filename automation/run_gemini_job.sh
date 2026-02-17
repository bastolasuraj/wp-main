#!/usr/bin/env bash
set -euo pipefail

# Define your API key here or in the cron environment
# export GEMINI_API_KEY="AIzaSy..."

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p automation/logs

# Install requirement if missing (optional check)
# pip install google-generativeai --quiet

python3 automation/gemini_autopost.py \
  --post-status publish \
  --model gemini-2.0-flash \
  --min-sources 8