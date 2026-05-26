#!/bin/bash
# Start services, ensure schema exists, apply pending migrations, then run src/main.py.
# Falls back to direct Python if Poetry is absent.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1
source "$SCRIPT_DIR/lib/common.sh"

export PYTHONPATH="${SCRIPT_DIR}/..:${SCRIPT_DIR}/../src${PYTHONPATH:+:${PYTHONPATH}}"

ensure_schema() {
    bash "${SCRIPT_DIR}/db_setup_schema.sh"
}

find_python() {
    command -v python3 2>/dev/null || \
    command -v python  2>/dev/null || \
    command -v py      2>/dev/null || \
    true
}

run_app() {
    local str_py
    str_py=$(find_python)
    if [[ -z "${str_py}" ]]; then
        print_status "error" "No Python interpreter found (tried python3, python, py)"
        exit 1
    fi
    if command -v poetry >/dev/null 2>&1; then
        poetry run python -m src.main
        return
    fi
    print_status "warning" "Poetry not found — installing via ${str_py} -m pip"
    if "${str_py}" -m pip install "poetry>=2.2.1"; then
        if command -v poetry >/dev/null 2>&1; then
            poetry run python -m src.main
        else
            print_status "warning" "Poetry installed but not in PATH — running directly"
            "${str_py}" -m src.main
        fi
    else
        print_status "warning" "pip install failed — falling back to direct execution"
        "${str_py}" -m src.main
    fi
}

ensure_schema
run_app
