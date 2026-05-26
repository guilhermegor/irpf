#!/usr/bin/env bash
# Creates TAXPAYER PostgreSQL schema (if absent) and applies Alembic migrations.
# Idempotent — safe to call on every startup or run standalone.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1
source "$SCRIPT_DIR/lib/common.sh"

export PYTHONPATH="${SCRIPT_DIR}/..:${SCRIPT_DIR}/../src${PYTHONPATH:+:${PYTHONPATH}}"

_read_env_var() {
    grep -m1 "^${1}=" .env 2>/dev/null | cut -d'=' -f2- | tr -d "'\""
}

load_env() {
    str_taxpayer=$(_read_env_var TAXPAYER)
    str_db_user=$(_read_env_var DB_USER)
    str_db_name=$(_read_env_var DB_NAME)
    if [[ -z "${str_taxpayer}" ]]; then
        print_status "error" "TAXPAYER is not set in .env"
        exit 1
    fi
    print_status "config" "Taxpayer schema: ${str_taxpayer}"
}

start_services() {
    print_status "info" "Bringing up services"
    docker compose up -d
    print_status "success" "Services healthy"
}

ensure_schema() {
    local str_exists
    str_exists=$(docker compose exec -T postgresql \
        psql -U "${str_db_user}" -d "${str_db_name}" \
        -tAc "SELECT 1 FROM information_schema.schemata WHERE schema_name = '${str_taxpayer}'" \
        2>/dev/null || true)
    if [[ "${str_exists}" != "1" ]]; then
        print_status "info" "Creating schema '${str_taxpayer}'"
        docker compose exec -T postgresql \
            psql -U "${str_db_user}" -d "${str_db_name}" \
            -c "CREATE SCHEMA IF NOT EXISTS ${str_taxpayer}"
        print_status "success" "Schema '${str_taxpayer}' created"
    else
        print_status "config" "Schema '${str_taxpayer}' already exists — skipping"
    fi
}

apply_migrations() {
    print_status "info" "Applying Alembic migrations"
    poetry run alembic upgrade head
    print_status "success" "Schema '${str_taxpayer}' is ready"
}

main() {
    load_env
    start_services
    ensure_schema
    apply_migrations
}

main
