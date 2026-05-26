# CLAUDE.md — `bin/`

Guidance for Claude Code when working with shell scripts in this directory.

## Purpose

`bin/` contains every operational shell script invoked by `Makefile` and `tasks.sh`.
Scripts are not meant to be imported or sourced by each other except via `lib/`.

## Directory layout

```
bin/
  lib/
    common.sh           # Shared utilities — source this, never execute it
  db_setup_schema.sh    # Idempotent schema creation + Alembic migrations
  run.sh                # Full startup: schema → migrations → app
  venv.sh               # Bootstrap Poetry virtual environment
  fix_playwright.sh     # Reinstall Playwright browsers
  check_unix_filenames.sh  # Pre-commit: validate filenames are ASCII-safe
  test_urls_docstrings.sh  # Pre-commit: verify URLs inside Python docstrings
```

## Shared library — `bin/lib/common.sh`

Every script sources this file for colour variables and status helpers.
Never inline these definitions in a script — add them here instead.

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
```

`common.sh` guards against direct execution with a `BASH_SOURCE` check and is
idempotent (safe to source multiple times if scripts ever call each other).

### `print_status` levels

| Level | Symbol | Routing | When to use |
|-------|--------|---------|-------------|
| `success` | `[✓]` | stdout | Completed action |
| `error` | `[✗]` | **stderr** | Failure the user must see |
| `warning` | `[!]` | stdout | Recoverable / skipped condition |
| `info` | `[i]` | stdout | Progress narration |
| `config` | `[→]` | stdout | A setting or value being applied |
| `debug` | `[»]` | stdout | Verbose diagnostics |

`print_section "title"` prints a magenta banner — use it to separate major phases.

## Script conventions

### Boilerplate order

```bash
#!/usr/bin/env bash          # db_setup_schema.sh (user-facing, $PATH-portable)
#!/bin/bash                  # all other scripts  (shellcheck dialect target)

set -euo pipefail            # most scripts
set -e                       # db_setup_schema.sh (caller-friendly subset)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1          # only when project root is needed
source "$SCRIPT_DIR/lib/common.sh"
```

### Structure: functions + `main()`

All logic lives in named functions. `main()` wires them in order and is called
at the bottom of the file. This makes every script readable top-down and
individually testable.

```bash
step_one() { ... }
step_two() { ... }

main() {
    step_one
    step_two
}

main
```

Scripts that accept arguments pass `"$@"` to `main`: `main "$@"`.

### Reading `.env` directly — `_read_env_var`

`make` expands `.env` values before passing them to subprocesses, mangling
passwords that contain `$` or `#`. Scripts that need env vars at runtime
(e.g. DB credentials) bypass this by reading `.env` directly:

```bash
_read_env_var() {
    grep -m1 "^${1}=" .env 2>/dev/null | cut -d'=' -f2- | tr -d "'\""
}

str_taxpayer=$(_read_env_var TAXPAYER)
```

Never pass `$(DB_PASSWORD)` through Make for docker/psql commands — the value
will be silently truncated.

### SC2155 — split `local` from command substitution

```bash
# bad — local swallows the exit code
local str_py=$(find_python)

# good
local str_py
str_py=$(find_python)
```

This applies to every `local x=$(...)` inside a function.

## Key script: `db_setup_schema.sh`

Idempotent — safe on every startup. Called by `run.sh` and directly by
`make db_setup_schema`. Sequence:

1. `load_env` — reads `TAXPAYER`, `DB_USER`, `DB_NAME` from `.env`
2. `start_services` — `docker compose up -d`
3. `ensure_schema` — queries `information_schema.schemata`; creates schema only if absent
4. `apply_migrations` — `poetry run alembic upgrade head`

The schema existence check avoids the `InvalidSchemaName` error Alembic raises
when the schema has never been created (e.g. first run with a new `TAXPAYER`).

## Key script: `run.sh`

Thin orchestrator — delegates setup to `db_setup_schema.sh`, then starts the app:

```
ensure_schema()  →  bash db_setup_schema.sh   (starts services + schema + migrations)
run_app()        →  poetry run python -m src.main
```

`run.sh` sets `PYTHONPATH` to expose `src/` so `chassis.*` imports resolve
without a package install step.

## Makefile ↔ tasks.sh sync

Both `Makefile` and `tasks.sh` delegate to these scripts — they contain no
inline shell logic of their own for database or run operations. When a script's
behaviour changes, only the script needs updating; the Makefile/tasks.sh
wrappers stay the same.

## Linting gate

All scripts must pass:

```bash
shellcheck --severity=warning --exclude=SC1091 bin/*.sh bin/lib/*.sh
bash -n bin/<script>.sh
```

`SC1091` is globally excluded (can't follow `$SCRIPT_DIR`-relative sources).
Any other `shellcheck disable` must be line-scoped with a one-line reason comment.
