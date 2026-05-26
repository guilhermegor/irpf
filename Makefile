-include .env
export APP_NAME TAXPAYER DB_USER DB_PASSWORD DB_HOST DB_PORT DB_NAME BACKUP_STORE_PATH

# -------------------
# VIRTUAL ENVIRONMENT
# -------------------
.PHONY: init venv update_venv precommit

init: venv precommit

venv:
	@bash bin/venv.sh

update_venv:
	@poetry update
	@echo "Poetry project updated"

precommit:
	@poetry run pre-commit install
	@poetry run pre-commit install --hook-type commit-msg

# -------------------
# TESTING
# -------------------
.PHONY: unit_tests integration_tests test_cov test_slowest test_feat test_urls_docstrings fix_playwright

unit_tests:
	@poetry run pytest tests/unit/

integration_tests:
	@poetry run pytest tests/integration/

test_cov:
	@poetry run pytest tests/unit/ --cov=src
	@poetry run coverage report -m
	@poetry run coverage-badge -o coverage.svg -f

test_slowest:
	@echo "Running tests to identify the 20 slowest tests..."
	@poetry run pytest tests/unit/ --durations=20 --tb=short

test_feat:
	@poetry run pytest tests/unit/ -k "$(FEAT)"

test_urls_docstrings:
	@bash bin/test_urls_docstrings.sh

fix_playwright:
	@bash bin/fix_playwright.sh

# -------------------
# LINTING
# -------------------
.PHONY: lint check_consistency

lint:
	@poetry run ruff check --fix .
	@poetry run ruff format .
	@poetry run codespell .
	@poetry run pydocstyle .
	@poetry run python bin/check_consistency.py

check_consistency:
	@poetry run python bin/check_consistency.py

# -------------------
# RUN
# -------------------
.PHONY: run

run:
	@bash bin/run.sh

# -------------------
# DATABASE
# -------------------
.PHONY: db_setup_schema db_backup db_restore

db_setup_schema:
	@[ -n "$(TAXPAYER)" ] || \
		{ echo "Error: TAXPAYER is not set — add it to .env"; exit 1; }
	@docker compose exec -T \
		-e PGPASSWORD="$(DB_PASSWORD)" \
		postgresql \
		psql -U "$(DB_USER)" -d "$(DB_NAME)" \
		-c "CREATE SCHEMA IF NOT EXISTS $(TAXPAYER)"
	@TAXPAYER=$(TAXPAYER) poetry run alembic upgrade head
	@echo "Schema '$(TAXPAYER)' is ready."

db_backup:
	@[ -n "$(BACKUP_STORE_PATH)" ] || \
		{ echo "Error: BACKUP_STORE_PATH is not set — add it to .env"; exit 1; }
	@mkdir -p "$(BACKUP_STORE_PATH)/dbs_bkp/$(APP_NAME)"
	@TIMESTAMP=$$(date +"%Y%m%d_%H%M%S"); \
	DUMP_FILE="$(BACKUP_STORE_PATH)/dbs_bkp/$(APP_NAME)/$(DB_NAME)_$${TIMESTAMP}.dump"; \
	docker compose exec -T \
		-e PGPASSWORD="$(DB_PASSWORD)" \
		postgresql \
		pg_dump -U "$(DB_USER)" -Fc "$(DB_NAME)" > "$${DUMP_FILE}" && \
	echo "Backup saved: $${DUMP_FILE}"

db_restore:
	@[ -n "$(DUMP)" ] || \
		{ echo "Usage: make db_restore DUMP=<path/to/file.dump>"; exit 1; }
	@[ -f "$(DUMP)" ] || \
		{ echo "Dump file not found: $(DUMP)"; exit 1; }
	@docker compose exec -T \
		-e PGPASSWORD="$(DB_PASSWORD)" \
		postgresql \
		pg_restore -U "$(DB_USER)" -d "$(DB_NAME)" \
			--clean --if-exists --no-owner -Fc \
		< "$(DUMP)"
	@echo "Restore complete from: $(DUMP)"

# -------------------
# DOCS
# -------------------
.PHONY: docs_server

docs_server:
	@poetry run mkdocs serve -a 0.0.0.0:8000 --livereload

# -------------------
# HELP
# -------------------
.PHONY: help

help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Virtual Environment"
	@echo "  init                 Bootstrap venv + install pre-commit hooks"
	@echo "  venv                 Create Poetry venv and install Playwright"
	@echo "  update_venv          Update all Poetry dependencies"
	@echo "  precommit            Install pre-commit hooks (push + commit-msg)"
	@echo ""
	@echo "Testing"
	@echo "  unit_tests           Run unit tests with pytest"
	@echo "  integration_tests    Run integration tests with pytest"
	@echo "  test_cov             Run unit tests with coverage report and badge"
	@echo "  test_slowest         Report the 20 slowest unit tests"
	@echo "  test_feat FEAT=<kw>  Run unit tests matching keyword <kw>"
	@echo "  test_urls_docstrings Check all URLs inside docstrings"
	@echo "  fix_playwright       Reinstall Playwright browsers"
	@echo ""
	@echo "Linting"
	@echo "  lint                 Run ruff, codespell, pydocstyle, check_consistency"
	@echo "  check_consistency    Check docstring type/raises consistency"
	@echo ""
	@echo "Docs"
	@echo "  docs_server          Serve MkDocs site locally at http://0.0.0.0:8000"
	@echo ""
	@echo "Run"
	@echo "  run                  Start services, apply migrations, run src/main.py"
	@echo ""
	@echo "Database"
	@echo "  db_setup_schema      Create TAXPAYER schema in DB and run Alembic migrations"
	@echo "  db_backup            Dump DB to BACKUP_STORE_PATH/dbs_bkp/APP_NAME/ (set in .env)"
	@echo "  db_restore DUMP=<f>  Restore a custom-format .dump file into DB"
	@echo ""
	@echo "Git Diff (offline sync — only present when scaffolded without GitHub)"
	@echo "  git_diff_export              Export commits (DIFF_RANGE, default main..HEAD) to git_diffs/"
	@echo "  git_diff_check FILE=<path>   Check whether a .diff applies cleanly"
	@echo "  git_diff_apply FILE=<path>   Apply a .diff to the working tree (no commit)"
	@echo ""

# Offline git-diff sync targets — present only when scaffolded without GitHub.
# The leading '-' makes this silently skipped when the fragment is absent.
-include make/git_diff.mk
