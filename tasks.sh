#!/usr/bin/env bash
# tasks.sh — Bash alternative to Makefile (no make required)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -------------------
# VIRTUAL ENVIRONMENT
# -------------------

venv() {
    bash "$SCRIPT_DIR/bin/venv.sh"
}

update_venv() {
    poetry update
    echo "Poetry project updated"
}

precommit() {
    poetry run pre-commit install
    poetry run pre-commit install --hook-type commit-msg
}

init() {
    venv
    precommit
}

# -------------------
# TESTING
# -------------------

unit_tests() {
    poetry run pytest tests/unit/
}

integration_tests() {
    poetry run pytest tests/integration/
}

test_cov() {
    poetry run pytest tests/unit/ --cov=src
    poetry run coverage report -m
    poetry run coverage-badge -o coverage.svg -f
}

test_slowest() {
    echo "Running tests to identify the 20 slowest tests..."
    poetry run pytest tests/unit/ --durations=20 --tb=short
}

test_feat() {
    if [[ -z "${FEAT:-}" ]]; then
        echo "Usage: FEAT=<keyword> ./tasks.sh test_feat"
        exit 1
    fi
    poetry run pytest tests/unit/ -k "$FEAT"
}

test_urls_docstrings() {
    bash "$SCRIPT_DIR/bin/test_urls_docstrings.sh"
}

fix_playwright() {
    bash "$SCRIPT_DIR/bin/fix_playwright.sh"
}

# -------------------
# LINTING
# -------------------

lint() {
    poetry run ruff check --fix .
    poetry run ruff format .
    poetry run codespell .
    poetry run pydocstyle .
    poetry run python bin/check_consistency.py
}

check_consistency() {
    poetry run python bin/check_consistency.py
}

# -------------------
# RUN
# -------------------

run() {
    bash "$SCRIPT_DIR/bin/run.sh"
}

# -------------------
# DATABASE
# -------------------

db_setup_schema() {
    if [[ -z "${TAXPAYER:-}" ]]; then
        echo "Error: TAXPAYER is not set — add it to .env" >&2
        exit 1
    fi
    docker compose exec -T \
        -e PGPASSWORD="${DB_PASSWORD}" \
        postgresql \
        psql -U "${DB_USER}" -d "${DB_NAME}" \
        -c "CREATE SCHEMA IF NOT EXISTS ${TAXPAYER}"
    TAXPAYER="${TAXPAYER}" poetry run alembic upgrade head
    echo "Schema '${TAXPAYER}' is ready."
}

db_backup() {
    if [[ -z "${BACKUP_STORE_PATH:-}" ]]; then
        echo "Error: BACKUP_STORE_PATH is not set — add it to .env" >&2
        exit 1
    fi
    mkdir -p "${BACKUP_STORE_PATH}/dbs_bkp/${APP_NAME}"
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    local dump_file="${BACKUP_STORE_PATH}/dbs_bkp/${APP_NAME}/${DB_NAME}_${timestamp}.dump"
    docker compose exec -T \
        -e PGPASSWORD="${DB_PASSWORD}" \
        postgresql \
        pg_dump -U "${DB_USER}" -Fc "${DB_NAME}" > "${dump_file}"
    echo "Backup saved: ${dump_file}"
}

db_restore() {
    local dump="${DUMP:-}"
    if [[ -z "${dump}" ]]; then
        echo "Usage: DUMP=<path/to/file.dump> ./tasks.sh db_restore" >&2
        exit 1
    fi
    if [[ ! -f "${dump}" ]]; then
        echo "Dump file not found: ${dump}" >&2
        exit 1
    fi
    docker compose exec -T \
        -e PGPASSWORD="${DB_PASSWORD}" \
        postgresql \
        pg_restore -U "${DB_USER}" -d "${DB_NAME}" \
            --clean --if-exists --no-owner -Fc \
        < "${dump}"
    echo "Restore complete from: ${dump}"
}

# -------------------
# GIT DIFF (offline sync — defined only when scaffolded without GitHub)
# -------------------

if [ -f "$SCRIPT_DIR/bin/git_diff_export.sh" ]; then
    git_diff_export() { bash "$SCRIPT_DIR/bin/git_diff_export.sh"; }
    git_diff_check() { bash "$SCRIPT_DIR/bin/git_diff_check.sh" "${1:-}"; }
    git_diff_apply() { bash "$SCRIPT_DIR/bin/git_diff_apply.sh" "${1:-}"; }
fi

# -------------------
# DOCS
# -------------------

docs_server() {
    poetry run mkdocs serve -a 0.0.0.0:8000 --livereload
}

# -------------------
# HELP
# -------------------

show_help() {
    cat <<EOF

Usage: ./tasks.sh <command>

Virtual Environment
  init                 Bootstrap venv + install pre-commit hooks
  venv                 Create Poetry venv and install Playwright
  update_venv          Update all Poetry dependencies
  precommit            Install pre-commit hooks (push + commit-msg)

Testing
  unit_tests           Run unit tests with pytest
  integration_tests    Run integration tests with pytest
  test_cov             Run unit tests with coverage report and badge
  test_slowest         Report the 20 slowest unit tests
  FEAT=<kw> test_feat  Run unit tests matching keyword <kw>
  test_urls_docstrings Check all URLs inside docstrings
  fix_playwright       Reinstall Playwright browsers

Linting
  lint                 Run ruff, codespell, pydocstyle, check_consistency
  check_consistency    Check docstring type/raises consistency

Docs
  docs_server          Serve MkDocs site locally at http://0.0.0.0:8000

Run
  run                  Start services, apply migrations, run src/main.py

Database
  db_setup_schema      Create TAXPAYER schema in DB and run Alembic migrations
  db_backup            Dump DB to BACKUP_STORE_PATH/dbs_bkp/APP_NAME/ (set in .env)
  DUMP=<f> db_restore  Restore a custom-format .dump file into DB

Git Diff (offline sync — only present when scaffolded without GitHub)
  git_diff_export             Export commits (DIFF_RANGE, default main..HEAD) to git_diffs/
  git_diff_check <path>       Check whether a .diff applies cleanly
  git_diff_apply <path>       Apply a .diff to the working tree (no commit)

EOF
}

# -------------------
# MAIN
# -------------------

case "${1:-help}" in
    init)                init ;;
    venv)                venv ;;
    update_venv)         update_venv ;;
    precommit)           precommit ;;
    unit_tests)          unit_tests ;;
    integration_tests)   integration_tests ;;
    test_cov)            test_cov ;;
    test_slowest)        test_slowest ;;
    test_feat)           test_feat ;;
    test_urls_docstrings) test_urls_docstrings ;;
    fix_playwright)      fix_playwright ;;
    lint)                lint ;;
    check_consistency)   check_consistency ;;
    docs_server)         docs_server ;;
    run)                 run ;;
    db_setup_schema)     db_setup_schema ;;
    db_backup)           db_backup ;;
    db_restore)          db_restore ;;
    git_diff_export)     git_diff_export ;;
    git_diff_check)      git_diff_check "${2:-}" ;;
    git_diff_apply)      git_diff_apply "${2:-}" ;;
    help|--help|-h)      show_help ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
