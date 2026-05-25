#!/usr/bin/env bash
# venv.sh — Create / refresh the Poetry virtual environment.
# Invoked by: make venv  |  ./tasks.sh venv  |  directly in CI

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PY_VERSION=$(cat "$PROJECT_ROOT/.python-version" 2>/dev/null || echo "3.11.12")
pyenv install "$PY_VERSION" -s
pyenv local "$PY_VERSION"

python -m pip install --upgrade pip
python -m pip install -r "$PROJECT_ROOT/requirements.txt"

poetry config virtualenvs.in-project true --local
poetry install --with dev,docs

echo "Virtual environment created in ./.venv"
echo "Poetry project installed (groups: main, dev, docs)"

poetry run playwright install
echo "Playwright installed"
