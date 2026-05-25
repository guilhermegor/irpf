#!/usr/bin/env bash
# Start services, apply pending migrations, then run src/main.py via Poetry.
# Falls back to direct Python if Poetry is absent.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure all commands run from the project root (parent of bin/).
cd "$SCRIPT_DIR/.."

# 1. Bring up PostgreSQL + pgAdmin (idempotent — safe on every run).
docker compose up -d

# 2. Apply any pending Alembic migrations (idempotent).
poetry run alembic upgrade head

# 3. Run the application.
find_python() {
    command -v python3 2>/dev/null || \
    command -v python  2>/dev/null || \
    command -v py      2>/dev/null || \
    true
}

str_py=$(find_python)

if [[ -z "$str_py" ]]; then
    echo "Error: no Python interpreter found (tried python3, python, py)" >&2
    exit 1
fi

if command -v poetry >/dev/null 2>&1; then
    poetry run python -m src.main
    exit $?
fi

echo "Poetry not found — installing via $str_py -m pip ..."
if "$str_py" -m pip install "poetry>=2.2.1"; then
    if command -v poetry >/dev/null 2>&1; then
        poetry run python -m src.main
    else
        echo "Poetry installed but not in PATH — running directly"
        "$str_py" -m src.main
    fi
else
    echo "pip install failed — falling back to direct execution"
    "$str_py" -m src.main
fi
