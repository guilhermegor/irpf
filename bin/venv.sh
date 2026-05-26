#!/bin/bash
# Create / refresh the Poetry virtual environment.
# Invoked by: make venv  |  ./tasks.sh venv  |  directly in CI

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

setup_python() {
    local str_py_version
    str_py_version=$(cat "$PROJECT_ROOT/.python-version" 2>/dev/null || echo "3.11.12")
    print_status "config" "Using Python ${str_py_version}"
    pyenv install "${str_py_version}" -s
    pyenv local "${str_py_version}"
    print_status "success" "Python ${str_py_version} active"
}

install_deps() {
    print_status "info" "Upgrading pip"
    python -m pip install --upgrade pip
    print_status "info" "Installing base requirements"
    python -m pip install -r "$PROJECT_ROOT/requirements.txt"
    print_status "info" "Installing Poetry project (groups: main, dev, docs)"
    poetry config virtualenvs.in-project true --local
    poetry install --with dev,docs
    print_status "success" "Virtual environment ready in ./.venv"
}

install_playwright() {
    print_status "info" "Installing Playwright browsers"
    poetry run playwright install
    print_status "success" "Playwright installed"
}

setup_python
install_deps
install_playwright
