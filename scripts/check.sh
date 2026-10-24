#!/usr/bin/env bash
# Full local gate; run before every commit (same steps as CI).
set -euo pipefail
cd "$(dirname "$0")/.."
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -m "not golden"
