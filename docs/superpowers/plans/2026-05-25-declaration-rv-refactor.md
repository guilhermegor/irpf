# Declaration RV Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port `declaracao_rv` into the DDD/hexagonal skeleton at `/home/guilhermegor/github/irpf`, making the solution generic (any user), in English, driven by `src/config/inputs.yaml`, backed by dockerised PostgreSQL + pgAdmin, using the Poetry-installed stpstone 3.1.1 API.

**Architecture:** Two capabilities — `import_trades` (Excel → PostgreSQL via stpstone `PostgreSQLDB`) and `declaration_rv` (PostgreSQL views → IRPF text report). Output files land in `daily_infos/<yyyy-mm-dd>/` under the path defined in `inputs.yaml`. Default path: `~/daily_infos` (expands to `/home/<USER>/daily_infos` on Linux). Credentials come from `.env`; all user-specific data (name, CPF, database, paths) lives in `inputs.yaml`.

**Tech Stack:** Python 3.12, Poetry, stpstone 3.1.1, SQLAlchemy ≥ 2.0, Alembic ≥ 1.13, PostgreSQL 16 (Docker), pgAdmin4 (Docker), python-dotenv, pandas, openpyxl, psycopg (v3), requests, lxml, pyyaml.

**Branch:** `feat/declaration-rv` (main is protected — all work on this branch, PR at the end).

---

## stpstone API migration cheat-sheet (reference for all tasks)

| Old (vendored) | New (installed 3.1.1) |
|---|---|
| `stpstone.pool_conn.postgre.PostgreSQL` | `stpstone.utils.connections.databases.sql.postgresql_db.PostgreSQLDB` |
| `stpstone.cals.handling_dates.DatesBR` | `stpstone.utils.calendars.calendar_br.DatesBRAnbima` |
| `stpstone.loggs.create_logs.CreateLog` | `stpstone.utils.loggs.create_logs.CreateLog` |
| `stpstone.loggs.init_setup` → `iniciating_logging` | `stpstone.utils.loggs.init_setup.initiate_logging` |
| `stpstone.directories_files_manag.managing_ff.DirFilesManagement` | `stpstone.utils.parsers.folders.DirFilesManagement` |
| `stpstone.handling_data.json.JsonFiles` | `stpstone.utils.parsers.json.JsonFiles` |
| `stpstone.handling_data.txt.HandlingTXTFiles` | `stpstone.utils.parsers.txt.HandlingTXTFiles` |
| `stpstone.handling_data.html_parser.HtmlHndler` | `stpstone.utils.parsers.html.HtmlHandler` |
| `stpstone.handling_data.dict.HandlingDicts` | `stpstone.utils.parsers.dicts.HandlingDicts` |
| `stpstone.handling_data.lists.HandlingLists` | `stpstone.utils.parsers.lists.HandlingLists` |
| `stpstone.opening_config.setup.reading_yaml` | `stpstone.utils.parsers.yaml.reading_yaml` |
| `PostgreSQL().read_sql(host, port, db, user, pw, query, timeout)` | `PostgreSQLDB(dbname, user, pw, host, int(port)).read(query)` |
| `PostgreSQL().engine(..., bl_insert_db=True)` | `PostgreSQLDB(...).insert(list_dicts, table_name, bool_insert_or_ignore=True)` |
| `DatesBR().curr_date` (property) | `DatesBRAnbima().curr_date()` (method) |
| `DatesBR().curr_time` (property) | `DatesBRAnbima().curr_time()` (method) |
| `DatesBR().year_number(date)` | `DatesBRAnbima().year_number(date)` |
| `DatesBR().build_date(y, m, d)` | `DatesBRAnbima().build_date(y, m, d)` |
| `CreateLog().infos(logger, msg)` | `CreateLog().log_message(logger, msg, "info")` |
| `CreateLog().basic_conf(path)` | `CreateLog().basic_conf(complete_path=path, basic_level="info")` |
| `HtmlHndler().html_lxml_parser(url, "GET", ...)` | `requests.get(url, headers=...)` then `HtmlHandler().lxml_parser(resp)` |
| `HtmlHndler().html_lxml_xpath(root, xpath)` | `HtmlHandler().lxml_xpath(root, xpath)` |

---

## Task 1: Branch setup

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- No new files

- [ ] **Step 1: Create branch and carry over any uncommitted changes**

```bash
cd /home/guilhermegor/github/irpf
git stash                          # save any uncommitted work; no-op if already clean
git checkout -b feat/declaration-rv
git stash pop                      # replay the stash onto the new branch (no-op if stash was empty)
```

Expected: new branch `feat/declaration-rv` checked out, and any previously uncommitted changes are now present on the new branch (not left behind on `main`).

- [ ] **Step 2: Add explicit dependencies to `pyproject.toml`**

Add under `[tool.poetry.dependencies]`:
```toml
pandas = ">=2.1.0"
psycopg = {extras = ["binary"], version = ">=3.2.4"}
openpyxl = ">=3.1.0"
pyyaml = ">=6.0.2"
requests = ">=2.31.0"
lxml = ">=5.3.0"
numpy = ">=2.0.0"
alembic = ">=1.13.0"
```

Run: `poetry install`
Expected: no install errors.

- [ ] **Step 3: Update `.env.example`**

Replace contents with:
```dotenv
ENV=development
APP_NAME=irpf

# PostgreSQL
DB_BACKEND=postgresql
DB_USER=irpf_user
DB_PASSWORD=irpf_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wealth_db
DB_DSN=

SQL_ECHO=false
RUN_DEMO=false

# pgAdmin
PGADMIN_EMAIL=admin@irpf.local
PGADMIN_PASSWORD=admin
PGADMIN_PORT=5050
```

- [ ] **Step 4: Create `CONTRIBUTING.md`**

```markdown
# Contributing

## Commit messages — Conventional Commits

Format: `<type>: <short description>`

| Type | When to use |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `chore` | Tooling, deps, config — no production code change |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `ci` | CI/CD pipeline changes |

Body (optional): one blank line after the subject, then bullet points explaining **why**, not what.

## Branch naming

`<type>/<short-slug>` — e.g. `feat/declaration-rv`, `fix/pm-patr-view`, `chore/update-deps`

## Alembic migration messages

Alembic `-m` messages become the migration **filename suffix** — keep them readable as a path segment.

Convention: `verb_subject_detail` in `snake_case`

| Action | Message |
|---|---|
| New table(s) | `create_b3_tables` |
| Add column | `add_cnpj_to_posicao_acoes` |
| Drop object | `drop_deprecated_movimentacao_view` |
| New view(s) | `create_irpf_views` |
| Index | `add_index_on_negociacao_ticker` |
| Backfill | `backfill_posicao_acoes_data_pregao` |

**Never put `feat:` or Conventional Commit prefixes in the Alembic message** — that belongs in the git commit that ships the migration file.

Example pairing:
```
alembic revision -m "create_irpf_views"
git commit -m "feat: add alembic migration — irpf views with sum aggregators"
```

## Running locally

```bash
# Start database
docker compose up -d

# Apply all migrations
poetry run alembic upgrade head

# Roll back all migrations
poetry run alembic downgrade base

# Run tests
poetry run python -m pytest tests/unit/ -v

# Lint
poetry run ruff check src/
```

## Code style

- Ruff (linter + formatter): `poetry run ruff check src/` — must pass before committing
- NumPy-style docstrings on all public methods
- Variable naming prefix convention: see `CLAUDE.md`
- One public class per file
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example CONTRIBUTING.md
git commit -m "chore: add explicit dependencies, update env example, and add contributing guide"
```

---

## Task 2: Docker infrastructure + Alembic setup

**Why Alembic instead of `container/init.sql`:**  
`init.sql` runs only once on first Docker volume creation — to re-run it you must destroy the volume and lose data. Alembic migrations are versioned Python files tracked in git; you run `alembic upgrade head` any time. Views are written as `op.execute()` in a dedicated migration file, giving them the same version history as tables.

**Files:**
- Create: `docker-compose.yml`
- Create: `alembic.ini`
- Create: `alembic/env.py`

- [ ] **Step 1: Write `docker-compose.yml`** (no `init.sql` volume mount — Alembic handles all DDL)

```yaml
services:
  postgresql:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME:-wealth_db}
      POSTGRES_USER: ${DB_USER:-irpf_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-irpf_password}
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-irpf_user} -d ${DB_NAME:-wealth_db}"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgadmin:
    image: dpage/pgadmin4:latest
    restart: unless-stopped
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL:-admin@irpf.local}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD:-admin}
    ports:
      - "${PGADMIN_PORT:-5050}:80"
    depends_on:
      postgresql:
        condition: service_healthy
    volumes:
      - pgadmin_data:/var/lib/pgadmin

volumes:
  pgdata:
  pgadmin_data:
```

- [ ] **Step 2: Initialise Alembic**

```bash
cd /home/guilhermegor/github/irpf
poetry run alembic init alembic
```

Expected: `alembic/` directory created with `env.py`, `versions/`, `script.py.mako`; `alembic.ini` in project root.

- [ ] **Step 2b: Create `alembic/CLAUDE.md`**

```markdown
# CLAUDE.md — `alembic/`

Guidance for Claude Code when working with Alembic migrations in this project.

## Naming migrations

`alembic revision -m "<message>"` — the message becomes the filename suffix.
Convention: `verb_subject_detail` in `snake_case`. See `CONTRIBUTING.md` for the full table.

## When to use --autogenerate vs manual

| Scenario | Command |
|---|---|
| Adding / changing ORM models (`models.py`) | `alembic revision --autogenerate -m "..."` |
| Creating or replacing views | `alembic revision -m "..."` (manual `op.execute()`) |
| Indexes, constraints, sequences | Either — prefer autogenerate if the ORM model reflects it |
| Data backfills | Always manual |

## Views must always be manual

Views cannot be detected by `--autogenerate`. Create them with `op.execute()` and always
implement `downgrade()` with `DROP VIEW IF EXISTS`.

```python
def upgrade() -> None:
    op.execute("CREATE OR REPLACE VIEW vw_example AS SELECT ...")

def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_example")
```

## Rules

- **Never edit a migration that has already been applied** to any environment. Create a new
  migration instead.
- **Always implement `downgrade()`** — even a simple `pass` is acceptable only for
  irreversible data migrations; prefer `DROP`/`ALTER` reversals wherever possible.
- **`upgrade()` and `downgrade()` must be inverses** — running both in sequence should
  leave the schema unchanged.
- Migration files live in `alembic/versions/` and are committed to git alongside the code
  change that requires them.

## Common commands

```bash
# Apply all pending migrations
poetry run alembic upgrade head

# Roll back one step
poetry run alembic downgrade -1

# Roll back everything
poetry run alembic downgrade base

# Show current revision
poetry run alembic current

# Show migration history
poetry run alembic history --verbose

# Generate autogenerate migration (run after editing models.py)
poetry run alembic revision --autogenerate -m "describe_the_change"
```
```

- [ ] **Step 3: Configure `alembic.ini`**

Edit the generated `alembic.ini` — change the `sqlalchemy.url` line to use the env-var DSN:

```ini
# Leave everything else as generated; only change this line:
sqlalchemy.url = %(DB_DSN)s
```

- [ ] **Step 4: Rewrite `alembic/env.py`**

```python
"""Alembic migration environment — loads metadata from SQLAlchemy Base."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from src.chassis.db_schema.infrastructure.base import Base
import src.chassis.db_schema.infrastructure.models  # noqa: F401 — registers all ORM models


load_dotenv()

_cfg = context.config
if _cfg.config_file_name is not None:
    fileConfig(_cfg.config_file_name)

_DB_DSN = (
    f"postgresql+psycopg://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
    f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
)
_cfg.set_main_option("sqlalchemy.url", _DB_DSN)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script without DB connection)."""
    context.configure(
        url=_DB_DSN,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (applies to live DB)."""
    connectable = engine_from_config(
        _cfg.get_section(_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml alembic.ini alembic/ CONTRIBUTING.md
git commit -m "feat: add docker-compose with postgresql and pgadmin, and alembic migration setup"
```

---

## Task 2b: Alembic migrations — tables

> **Note:** Run this task AFTER Task 4 (ORM models are defined). Alembic `--autogenerate` reads `Base.metadata` to produce the table DDL.

**Files:**
- Create: `alembic/versions/0001_create_b3_tables.py` (auto-generated, then committed)

- [ ] **Step 1: Start docker and wait for healthy**

```bash
docker compose up -d
```

Wait ~10 s for the `pg_isready` healthcheck to pass.

- [ ] **Step 2: Generate autogenerate migration**

```bash
poetry run alembic revision --autogenerate -m "create_b3_tables"
```

Expected: `alembic/versions/<hash>_create_b3_tables.py` created with `op.create_table(...)` calls for all 8 ORM models (`RecordModel` + 7 B3 models).

- [ ] **Step 3: Apply migration**

```bash
poetry run alembic upgrade head
```

Expected: All tables created in `wealth_db`. No errors.

- [ ] **Step 4: Verify tables exist**

```bash
docker exec -it irpf-postgresql-1 psql -U irpf_user -d wealth_db -c "\dt"
```

Expected: `movimentacao`, `negociacao`, `posicao_acoes`, `posicao_emprestimos`, `proventos_recebidos`, `reembolso_emprestimos`, `bonificacao_acoes` all listed.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: add alembic migration 0001 — create b3 tables"
```

---

## Task 2c: Alembic migrations — views

**Views are created with `op.execute()` (views can't be auto-generated).** The SQL is adapted from the source project's `bkp/create-tables-irpf_20250528_1308.txt` with proper `SUM`/`GROUP BY`/`HAVING` aggregators. `DADOS_PUBLICOS_RV` is replaced by joining `posicao_acoes.cnpj` (most recent position per ticker via `DISTINCT ON`).

**Files:**
- Create: `alembic/versions/0002_create_irpf_views.py`

- [ ] **Step 1: Create manual migration file**

```bash
poetry run alembic revision -m "create_irpf_views"
```

Expected: `alembic/versions/<hash>_create_irpf_views.py` created (empty upgrade/downgrade stubs).

- [ ] **Step 2: Fill in the migration**

Replace the generated file's `upgrade()` and `downgrade()` with:

```python
"""Create IRPF PostgreSQL views."""

from __future__ import annotations

from alembic import op


revision = "<hash from generated file>"
down_revision = "<hash of 0001 migration>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW b3_vw_bonificacoes AS
        SELECT
            EXTRACT(YEAR FROM b.data_pregao)::int       AS ano_base,
            SPLIT_PART(b.produto, ' - ', 1)             AS ticker,
            COALESCE(pa.cnpj, '')                       AS cnpj,
            SPLIT_PART(b.produto, ' - ', 2)             AS nome_compania,
            SUM(b.valor_operacao)                       AS valor_operacao
        FROM b3_bonificacao_acoes b
        LEFT JOIN (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao, cnpj
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        ) pa ON SPLIT_PART(b.produto, ' - ', 1) = pa.codigo_negociacao
        WHERE b.movimentacao = 'Bonificação em Ativos'
        GROUP BY 1, 2, 3, 4
        ORDER BY ticker, ano_base DESC
    """)

    op.execute("""
        CREATE OR REPLACE VIEW b3_vw_proventos AS
        SELECT
            EXTRACT(YEAR FROM pr.data_pregao)::int  AS ano_base,
            SPLIT_PART(pr.produto, ' - ', 1)        AS ticker,
            COALESCE(pa.cnpj, '')                   AS cnpj,
            SPLIT_PART(pr.produto, ' - ', 2)        AS nome_compania,
            pr.tipo_evento                          AS movimentacao,
            SUM(pr.valor_liquido)                   AS valor_operacao
        FROM b3_proventos_recebidos pr
        LEFT JOIN (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao, cnpj
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        ) pa ON SPLIT_PART(pr.produto, ' - ', 1) = pa.codigo_negociacao
        GROUP BY 1, 2, 3, 4, 5
        HAVING SUM(pr.valor_liquido) <> 0

        UNION ALL

        SELECT
            EXTRACT(YEAR FROM re.data_pregao)::int  AS ano_base,
            SPLIT_PART(re.produto, ' - ', 1)        AS ticker,
            COALESCE(pa.cnpj, '')                   AS cnpj,
            SPLIT_PART(re.produto, ' - ', 2)        AS nome_compania,
            re.tipo_evento                          AS movimentacao,
            SUM(re.valor_liquido)                   AS valor_operacao
        FROM b3_reembolso_emprestimos re
        LEFT JOIN (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao, cnpj
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        ) pa ON SPLIT_PART(re.produto, ' - ', 1) = pa.codigo_negociacao
        GROUP BY 1, 2, 3, 4, 5
        HAVING SUM(re.valor_liquido) <> 0
    """)

    op.execute("""
        CREATE OR REPLACE VIEW b3_vw_pm_patr AS
        WITH buy_totals AS (
            SELECT
                CASE
                    WHEN RIGHT(ticker, 1) = 'F'
                    THEN LEFT(ticker, CHAR_LENGTH(ticker) - 1)
                    ELSE ticker
                END                                                                AS instrumento,
                SUM(CASE WHEN tipo_movimentacao = 'Compra' THEN quantidade ELSE 0 END)
                                                                                   AS total_bought,
                SUM(CASE WHEN tipo_movimentacao = 'Compra' THEN quantidade * preco ELSE 0 END)
                                                                                   AS total_cost,
                SUM(CASE WHEN tipo_movimentacao = 'Compra' THEN quantidade ELSE 0 END)
                    - SUM(CASE WHEN tipo_movimentacao = 'Venda' THEN quantidade ELSE 0 END)
                                                                                   AS qtd_lado
            FROM b3_negociacao
            GROUP BY 1
        ),
        last_position AS (
            SELECT DISTINCT ON (codigo_negociacao)
                codigo_negociacao,
                cnpj,
                SPLIT_PART(produto, ' - ', 2) AS nome_compania
            FROM b3_posicao_acoes
            ORDER BY codigo_negociacao, data_pregao DESC
        )
        SELECT
            bt.instrumento,
            CASE WHEN bt.total_bought > 0 THEN bt.total_cost / bt.total_bought
                 ELSE 0 END                                                        AS preco_medio_compra,
            bt.qtd_lado,
            bt.qtd_lado * CASE WHEN bt.total_bought > 0
                               THEN bt.total_cost / bt.total_bought ELSE 0 END    AS posicao_fin,
            COALESCE(lp.cnpj, '')                                                  AS cnpj,
            COALESCE(lp.nome_compania, bt.instrumento)                             AS nome_compania
        FROM buy_totals bt
        LEFT JOIN last_position lp ON bt.instrumento = lp.codigo_negociacao
        WHERE bt.qtd_lado > 0
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS b3_vw_pm_patr")
    op.execute("DROP VIEW IF EXISTS b3_vw_proventos")
    op.execute("DROP VIEW IF EXISTS b3_vw_bonificacoes")
```

**Important:** Keep the `revision` and `down_revision` hashes exactly as Alembic generated them — only replace the `upgrade()` and `downgrade()` function bodies.

- [ ] **Step 3: Apply the view migration**

```bash
poetry run alembic upgrade head
```

Expected: 3 views created. No errors.

- [ ] **Step 4: Verify views exist**

```bash
docker exec -it irpf-postgresql-1 psql -U irpf_user -d wealth_db -c "\dv"
```

Expected: `b3_vw_bonificacoes`, `b3_vw_proventos`, `b3_vw_pm_patr` all listed.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: add alembic migration 0002 — create irpf views with sum aggregators"
```

---

## Task 3: Config layer update

**Files:**
- Modify: `src/config/inputs.yaml`
- Modify: `src/config/outputs.yaml`
- Modify: `src/config/startup.py`

- [ ] **Step 1: Rewrite `src/config/inputs.yaml`**

```yaml
# Cross-platform paths — ~ expands to the user's home directory on Linux/macOS/Windows
daily_infos_base_path: "~/daily_infos"

import_trades:
  data_path: "~/daily_infos"
  bonificacoes_xpath: "//div[@class='card p-2 p-xs-3'][.//h3[@class][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), \"bonifica\")]]//strong[@class='d-block lh-3 fs-3 fw-700']"

declaration_rv:
  base_year_offset: 1       # declaration year = current_year - base_year_offset
  decimal_places: 2
  month_ref: 12
  day_ref: 31
  timeout_seconds: 7200
  contributor:
    full_name: "FILL_IN_YOUR_FULL_NAME"
    cpf: "FILL_IN_YOUR_CPF"
  assets_and_rights:
    group:
      key: "Group: "
      value: "03 - Corporate Holdings"
    code:
      key: "Code: "
      value: "01 - Stocks (including exchange-listed)"
    location:
      key: "Location (Country): "
      value: "105 - Brazil"
    cnpj:
      key: "CNPJ: "
    description:
      key: "Description: "
      value: "{} {} SHARES ACQUIRED AT AN AVERAGE PRICE OF BRL {}"
    traded_on_exchange:
      key: "Traded on Exchange? "
      value: "Yes"
    trading_code:
      key: "Trading Code: "
    year_end_balance:
      key: "Balance on {} (BRL): "
  exempt_non_taxable_income:
    income_type:
      key: "Income Type: "
      value: "09 - Dividends received"
    payer_cnpj:
      key: "Payer CNPJ: "
    payer_name:
      key: "Payer Name: "
    amount:
      key: "Amount: "
  taxable_income_jcp:
    income_type:
      key: "Income Type: "
      value: "10 - Interest on equity (JCP)"
    payer_cnpj:
      key: "Payer CNPJ: "
    payer_name:
      key: "Payer Name: "
    amount:
      key: "Amount: "
  taxable_income_monetary_update:
    income_type:
      key: "Income Type: "
      value: "06 - Financial investment income"
    payer_cnpj:
      key: "Payer CNPJ: "
    payer_name:
      key: "Payer Name: "
    amount:
      key: "Amount: "
  taxable_income_stock_lending:
    income_type:
      key: "Income Type: "
      value: "06 - Financial investment income"
    payer_cnpj:
      key: "Payer CNPJ: "
      value: "09346601000125"
    payer_name:
      key: "Payer Name: "
      value: "B3 S.A. - BRASIL. BOLSA. BALCAO"
    amount:
      key: "Amount: "
  exempt_non_taxable_reimbursement:
    income_type:
      key: "Income Type: "
      value: "99 - Other"
    payer_cnpj:
      key: "Payer CNPJ: "
      value: "09346601000125"
    payer_name:
      key: "Payer Name: "
      value: "B3 S.A. - BRASIL. BOLSA. BALCAO"
    description:
      key: "Description: "
      value: "REIMBURSEMENT OF INCOME FROM LENT SHARES"
    amount:
      key: "Amount: "
  exempt_non_taxable_fraction_auction:
    income_type:
      key: "Income Type: "
      value: "99 - Other"
    payer_cnpj:
      key: "Payer CNPJ: "
    payer_name:
      key: "Payer Name: "
    description:
      key: "Description: "
      value: "SALE OF FRACTIONAL SHARE AT AUCTION - {}"
    amount:
      key: "Amount: "
  exempt_non_taxable_bonus_shares:
    income_type:
      key: "Income Type: "
      value: "18 - Capitalisation of reserves / Bonus shares"
    payer_cnpj:
      key: "Payer CNPJ: "
    payer_name:
      key: "Payer Name: "
    amount:
      key: "Amount: "

db:
  database: "wealth_db"
  col_year_base: "ano_base"
  col_ticker: "ticker"
  col_instrument: "instrumento"
  col_cnpj: "cnpj"
  col_company_name: "nome_compania"
  col_position_side: "qtd_lado"
  col_avg_buy_price: "preco_medio_compra"
  col_financial_position: "posicao_fin"
  col_movement_type: "movimentacao"
  col_operation_value: "valor_operacao"
  query_active_tickers_base_year: >
    SELECT
        DISTINCT(CODIGO_NEGOCIACAO) AS ticker
      FROM b3_posicao_acoes
      WHERE EXTRACT('Year' FROM data_pregao) = '{}'
    UNION
    SELECT
        DISTINCT(SPLIT_PART(produto, ' - ', 1)) AS ticker
      FROM b3_posicao_emprestimos
      WHERE EXTRACT('Year' FROM data_pregao) = '{}';
  query_bonus_shares: >
    SELECT
        ANO_BASE,
        TICKER,
        CNPJ,
        NOME_COMPANIA,
        SUM(VALOR_OPERACAO) AS valor_operacao
      FROM B3_VW_BONIFICACOES
        WHERE ANO_BASE = '{}'
      GROUP BY 1, 2, 3, 4
      ORDER BY TICKER, ANO_BASE DESC;
  query_stock_lending_income: >
    SELECT
        SUM(VALOR_OPERACAO) AS valor_operacao
      FROM B3_VW_PROVENTOS
      WHERE
        MOVIMENTACAO = 'Empréstimo'
        AND ANO_BASE = '{}';
  query_exempt_dividends: >
    SELECT
        TICKER,
        CNPJ,
        NOME_COMPANIA,
        MOVIMENTACAO,
        SUM(VALOR_OPERACAO) AS valor_operacao
      FROM B3_VW_PROVENTOS
      WHERE
        ANO_BASE = '{}'
        AND MOVIMENTACAO = 'Dividendo'
      GROUP BY 1, 2, 3, 4;
  query_taxable_jcp: >
    SELECT
        TICKER,
        CNPJ,
        NOME_COMPANIA,
        MOVIMENTACAO,
        SUM(VALOR_OPERACAO) AS valor_operacao
      FROM B3_VW_PROVENTOS
      WHERE
        ANO_BASE = '{}'
        AND MOVIMENTACAO = 'Juros Sobre Capital Próprio'
      GROUP BY 1, 2, 3, 4;
  query_monetary_update_income: >
    SELECT
        ANO_BASE,
        TICKER,
        CNPJ,
        NOME_COMPANIA,
        MOVIMENTACAO,
        SUM(VALOR_OPERACAO) AS valor_operacao
      FROM B3_VW_PROVENTOS
      WHERE
        MOVIMENTACAO = 'Rendimento'
        AND ANO_BASE = '{}'
      GROUP BY 1, 2, 3, 4, 5;
  query_fraction_auction: >
    SELECT
        ANO_BASE,
        TICKER,
        CNPJ,
        NOME_COMPANIA,
        MOVIMENTACAO,
        SUM(VALOR_OPERACAO) AS valor_operacao
      FROM B3_VW_PROVENTOS
      WHERE
        MOVIMENTACAO = 'Leilão de Fração'
        AND ANO_BASE = '{}'
      GROUP BY 1, 2, 3, 4, 5
      ORDER BY TICKER;
  query_lending_reimbursement: >
    SELECT
      SUM(VALOR_OPERACAO) AS valor_operacao
      FROM B3_VW_PROVENTOS
      WHERE
        MOVIMENTACAO = 'Reembolso'
        AND ANO_BASE = '{}';
  query_avg_price_portfolio: >
    SELECT * FROM B3_VW_PM_PATR;
```

- [ ] **Step 2: Update `src/config/outputs.yaml`**

```yaml
log_name: "{}-{}_{}_{}_{}.log"
json_name: "{}-{}_{}_{}_{}.json"
txt_name:  "{}-{}_{}_{}_{}.txt"
```

- [ ] **Step 3: Rewrite `src/config/startup.py`**

```python
"""Startup: logger, MS Teams webhook, and runtime constants."""

from __future__ import annotations

import os
from getpass import getuser
from pathlib import Path
from socket import gethostname

from dotenv import load_dotenv
from stpstone.utils.calendars.calendar_br import DatesBRAnbima
from stpstone.utils.loggs.create_logs import CreateLog
from stpstone.utils.parsers.yaml import reading_yaml
from stpstone.utils.webhooks.teams import WebhookTeams


load_dotenv()

cls_dates_br = DatesBRAnbima()
cls_create_log = CreateLog()

_CONFIG_DIR = Path(__file__).parent

USER: str = getuser()
HOSTNAME: str = gethostname()
ENVIRONMENT: str = os.getenv("ENV", "development").lower()
APP_NAME: str = os.getenv("APP_NAME", "irpf")

YAML_OUTPUTS: dict = reading_yaml(str(_CONFIG_DIR / "outputs.yaml"))
YAML_WEBHOOKS: dict = reading_yaml(str(_CONFIG_DIR / "webhooks.yaml"))
YAML_INPUTS: dict = reading_yaml(str(_CONFIG_DIR / "inputs.yaml"))

CLS_MS_TEAMS = WebhookTeams(YAML_WEBHOOKS["ms_teams"]["url"])

_dt_run = cls_dates_br.curr_date()
_dt_run_time = cls_dates_br.curr_time()

# daily_infos/<yyyy-mm-dd>/ — created from inputs.yaml (cross-platform)
_daily_infos_root: Path = Path(YAML_INPUTS["daily_infos_base_path"]).expanduser()
_daily_infos_dir: Path = _daily_infos_root / str(_dt_run)
_daily_infos_dir.mkdir(parents=True, exist_ok=True)

_dt_str: str = _dt_run.strftime("%Y%m%d")
_time_str: str = _dt_run_time.strftime("%H%M%S")

PATH_LOG: Path = _daily_infos_dir / YAML_OUTPUTS["log_name"].format(
    APP_NAME, ENVIRONMENT, USER, _dt_str, _time_str
)
PATH_JSON: Path = _daily_infos_dir / YAML_OUTPUTS["json_name"].format(
    APP_NAME, ENVIRONMENT, USER, _dt_str, _time_str
)
PATH_TXT: Path = _daily_infos_dir / YAML_OUTPUTS["txt_name"].format(
    APP_NAME, ENVIRONMENT, USER, _dt_str, _time_str
)

DIR_PARENT = str(_daily_infos_dir)
LOGGER = cls_create_log.basic_conf(complete_path=str(PATH_LOG), basic_level="info")

MSG_MS_TEAMS: str = YAML_WEBHOOKS["ms_teams"]["message"].format(
    YAML_WEBHOOKS["ms_teams"]["title"],
    cls_dates_br.curr_date(),
    HOSTNAME,
    USER,
    str(PATH_JSON),
    str(PATH_LOG),
)
```

- [ ] **Step 4: Commit**

```bash
git add src/config/inputs.yaml src/config/outputs.yaml src/config/startup.py
git commit -m "feat: update config layer with daily_infos path management and irpf inputs"
```

---

## Task 4: ORM models for B3 data

**Files:**
- Modify: `src/chassis/db_schema/infrastructure/models.py`

- [ ] **Step 1: Append 7 new ORM models to `models.py`**

Add at the bottom of the existing file (keep `RecordModel`):

```python
from sqlalchemy import Date, Integer, Numeric


class MovimentacaoModel(Base):
    """ORM model for B3 trade movement records."""

    __tablename__ = "b3_movimentacao"

    pk_movimentacao: Mapped[str] = mapped_column(String(600), primary_key=True)
    entrada_saida: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    movimentacao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantidade: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    preco_unitario: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_operacao: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)


class NegociacaoModel(Base):
    """ORM model for B3 trade negotiation records."""

    __tablename__ = "b3_negociacao"

    pk_negociacao: Mapped[str] = mapped_column(String(600), primary_key=True)
    data_negocio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tipo_movimentacao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mercado: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prazo_vencimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    quantidade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preco: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)


class PosicaoAcoesModel(Base):
    """ORM model for B3 year-end stock positions."""

    __tablename__ = "b3_posicao_acoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    conta: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    codigo_negociacao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    codigo_isin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    escriturador: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantidade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quantidade_disp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quantidade_indisp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    motivo: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    preco_fechamento: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_atualizado: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class PosicaoEmprestimosModel(Base):
    """ORM model for B3 year-end lending positions."""

    __tablename__ = "b3_posicao_emprestimos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    natureza: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    num_contrato: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    modalidade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    opa: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    liquidacao_antecipada: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    taxa: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    comissao: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    data_registro: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_vencimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantidade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preco_fechamento: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_atualizado: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class ProventosRecebidosModel(Base):
    """ORM model for B3 received dividends and income."""

    __tablename__ = "b3_proventos_recebidos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tipo_evento: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    valor_liquido: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class ReembolsoEmprestimosModel(Base):
    """ORM model for B3 lending reimbursement records."""

    __tablename__ = "b3_reembolso_emprestimos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tipo_evento: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    valor_liquido: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class BonificacaoAcoesModel(Base):
    """ORM model for B3 bonus share records."""

    __tablename__ = "b3_bonificacao_acoes"

    pk_movimentacao: Mapped[str] = mapped_column(String(600), primary_key=True)
    entrada_saida: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    data_pregao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    movimentacao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    produto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instituicao: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantidade: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    preco_unitario: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    valor_operacao: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
```

Note: add `from datetime import date` to the imports at the top of the file.

- [ ] **Step 2: Commit ORM models**

```bash
git add src/chassis/db_schema/infrastructure/models.py
git commit -m "feat: add b3 trade and position orm models"
```

- [ ] **Step 3: Run Alembic migrations (Task 2b + 2c)**

Now that ORM models exist, go back and execute Tasks 2b and 2c in order:

```bash
# Task 2b — auto-generate table migration
poetry run alembic revision --autogenerate -m "create_b3_tables"
poetry run alembic upgrade head

# Task 2c — manually write view migration (see Task 2c for full file content)
poetry run alembic revision -m "create_irpf_views"
# Edit the generated file with the view SQL from Task 2c, then:
poetry run alembic upgrade head
```

Verify: `docker exec -it irpf-postgresql-1 psql -U irpf_user -d wealth_db -c "\dt; \dv"`

- [ ] **Step 4: Commit migrations**

```bash
git add alembic/versions/
git commit -m "feat: add alembic migrations for b3 tables and irpf views"
```

---

## Task 5: `import_trades` capability

**Files to create:**
- `src/capabilities/import_trades/__init__.py`
- `src/capabilities/import_trades/domain/__init__.py`
- `src/capabilities/import_trades/domain/enums.py`
- `src/capabilities/import_trades/domain/entities.py`
- `src/capabilities/import_trades/domain/dto.py`
- `src/capabilities/import_trades/domain/ports.py`
- `src/capabilities/import_trades/application/__init__.py`
- `src/capabilities/import_trades/application/use_cases.py`
- `src/capabilities/import_trades/infrastructure/__init__.py`
- `src/capabilities/import_trades/infrastructure/bonus_shares_scraper.py`
- `src/capabilities/import_trades/infrastructure/repositories.py`

- [ ] **Step 1: Write domain layer**

`src/capabilities/import_trades/domain/enums.py`:
```python
"""Domain enums for the import_trades capability."""

from __future__ import annotations

from enum import Enum


class TradeTable(str, Enum):
    """Target PostgreSQL table for each file type."""

    MOVIMENTACAO = "b3_movimentacao"
    NEGOCIACAO = "b3_negociacao"
    POSICAO_ACOES = "b3_posicao_acoes"
    POSICAO_EMPRESTIMOS = "b3_posicao_emprestimos"
    PROVENTOS_RECEBIDOS = "b3_proventos_recebidos"
    REEMBOLSO_EMPRESTIMOS = "b3_reembolso_emprestimos"
    BONIFICACAO_ACOES = "b3_bonificacao_acoes"
```

`src/capabilities/import_trades/domain/entities.py`:
```python
"""Persistence entities for the import_trades capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class TradeImportJob:
    """Describes a single import job: one xlsx file → one DB table."""

    file_name_like: str
    dict_dtypes: dict[str, Any]
    table_name: str
    dt_date_ref: date | None = field(default=None)
```

`src/capabilities/import_trades/domain/dto.py`:
```python
"""DTOs for the import_trades capability."""

from __future__ import annotations

from typing import TypedDict


class ImportResultDTO(TypedDict):
    """Result of a single trade import job."""

    table_name: str
    rows_processed: int
    status: str
```

`src/capabilities/import_trades/domain/ports.py`:
```python
"""Ports for the import_trades capability."""

from __future__ import annotations

from typing import Protocol

from .dto import ImportResultDTO
from .entities import TradeImportJob


class TradeImportRepository(Protocol):
    """Outbound port: persist one import job."""

    def import_job(self, cls_job: TradeImportJob) -> ImportResultDTO: ...
```

- [ ] **Step 2: Write `application/use_cases.py`**

```python
"""Use cases for the import_trades capability."""

from __future__ import annotations

from ..domain.dto import ImportResultDTO
from ..domain.entities import TradeImportJob
from ..domain.ports import TradeImportRepository


class ImportTrades:
    """Import a batch of B3 Excel files into PostgreSQL."""

    def __init__(self, cls_repo: TradeImportRepository) -> None:
        self._cls_repo = cls_repo

    def execute(self, list_jobs: list[TradeImportJob]) -> list[ImportResultDTO]:
        """Run every import job in order and return results.

        Parameters
        ----------
        list_jobs : list[TradeImportJob]
            Ordered list of import jobs to process.

        Returns
        -------
        list[ImportResultDTO]
            One result per job.
        """
        return [self._cls_repo.import_job(cls_job) for cls_job in list_jobs]
```

- [ ] **Step 3: Write `infrastructure/bonus_shares_scraper.py`**

```python
"""Scrape bonus share data from StatusInvest."""

from __future__ import annotations

import requests
import pandas as pd
from stpstone.utils.parsers.html import HtmlHandler
from stpstone.utils.parsers.dicts import HandlingDicts
from stpstone.utils.calendars.calendar_br import DatesBRAnbima


_cls_dates = DatesBRAnbima()
_cls_html = HtmlHandler()
_XPATH = (
    "//div[@class='card p-2 p-xs-3']"
    "[.//h3[@class][contains(translate(., "
    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'bonifica')]]"
    "//strong[@class='d-block lh-3 fs-3 fw-700']"
)
_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
}


def fetch_bonus_shares(str_ticker: str, str_xpath: str = _XPATH) -> pd.DataFrame:
    """Fetch bonus share history for a ticker from StatusInvest.

    Parameters
    ----------
    str_ticker : str
        B3 ticker symbol (e.g. "PETR4").
    str_xpath : str
        XPath to extract bonus share rows from the page.

    Returns
    -------
    pd.DataFrame
        Columns: data_anuncio, data_com, data_ex, data_incorporacao,
                 valor_base (float), proporcao (float), TICKER, ano_ref.
    """
    list_cols = [
        "data_anuncio", "data_com", "data_ex",
        "data_incorporacao", "valor_base", "proporcao",
    ]
    str_url = f"https://statusinvest.com.br/acoes/{str_ticker.lower()}"
    cls_resp = requests.get(str_url, headers=_HEADERS, verify=False, timeout=30)
    cls_root = _cls_html.lxml_parser(cls_resp)
    list_spans = _cls_html.lxml_xpath(cls_root, str_xpath)
    list_text = [
        _cls_html.lxml_xpath(el_, "./text()")[0].strip().replace("\n", " ")
        for el_ in list_spans
    ]
    list_text = [x for x in list_text if len(x) > 0]
    list_ser = HandlingDicts().pair_headers_with_data(list_cols, list_text)
    df_ = pd.DataFrame(list_ser)
    df_["TICKER"] = str_ticker

    # clean valor_base
    df_["valor_base"] = (
        df_["valor_base"].str.replace("R$", "").str.replace(".", "")
        .str.replace(",", ".").astype(float)
    )
    # clean proporcao
    df_["proporcao"] = (
        df_["proporcao"].str.replace("%", "").str.replace(",", ".")
        .astype(float) / 100.0
    )
    # parse dates
    for str_col in ["data_anuncio", "data_com", "data_ex", "data_incorporacao"]:
        df_[str_col] = pd.to_datetime(df_[str_col], format="%d/%m/%Y", errors="coerce")

    df_["ano_ref"] = [_cls_dates.year_number(d) for d in df_["data_ex"]]
    return df_
```

- [ ] **Step 4: Write `infrastructure/repositories.py`**

```python
"""Infrastructure repository for the import_trades capability."""

from __future__ import annotations

import os
from datetime import date
from numbers import Number
from pathlib import Path
from typing import Any

import pandas as pd
from stpstone.utils.calendars.calendar_br import DatesBRAnbima
from stpstone.utils.connections.databases.sql.postgresql_db import PostgreSQLDB
from stpstone.utils.parsers.folders import DirFilesManagement

from ..domain.dto import ImportResultDTO
from ..domain.entities import TradeImportJob
from .bonus_shares_scraper import fetch_bonus_shares


_cls_dates = DatesBRAnbima()
_cls_dir = DirFilesManagement()


class PostgresTradeImportRepository:
    """Reads B3 Excel files and inserts them into PostgreSQL.

    Parameters
    ----------
    str_data_path : str
        Directory that contains the B3 Excel files (cross-platform ~ supported).
    str_host : str
        PostgreSQL host.
    int_port : int
        PostgreSQL port.
    str_dbname : str
        PostgreSQL database name.
    str_user : str
        PostgreSQL username.
    str_password : str
        PostgreSQL password.
    """

    def __init__(
        self,
        str_data_path: str,
        str_host: str,
        int_port: int,
        str_dbname: str,
        str_user: str,
        str_password: str,
    ) -> None:
        self._path_data = Path(str_data_path).expanduser()
        self._str_host = str_host
        self._int_port = int_port
        self._str_dbname = str_dbname
        self._str_user = str_user
        self._str_password = str_password

    def _db(self) -> PostgreSQLDB:
        return PostgreSQLDB(
            dbname=self._str_dbname,
            user=self._str_user,
            password=self._str_password,
            host=self._str_host,
            port=self._int_port,
        )

    def _fetch_excel(
        self,
        str_file_name_like: str,
        dict_dtypes: dict[str, Any],
        str_table_name: str,
        dt_date_ref: date | None,
    ) -> pd.DataFrame:
        str_path_file = _cls_dir.choose_last_saved_file_w_rule(
            str(self._path_data), str_file_name_like
        )
        list_cols_dt = [k for k, v in dict_dtypes.items() if v == "date"]
        dict_load_dtypes = {k: v if str(v) != "date" else str for k, v in dict_dtypes.items()}

        if "relatorio-consolidado-anual" in str_file_name_like:
            dict_sheet = {
                "b3_posicao_acoes": "Posição - Ações",
                "b3_posicao_emprestimos": "Posição - Empréstimos",
                "b3_proventos_recebidos": "Proventos Recebidos",
                "b3_reembolso_emprestimos": "Reembolsos de Empréstimo",
            }
            str_sheet = dict_sheet.get(str_table_name)
            if str_sheet is None:
                raise ValueError(f"Unknown table name for annual report: {str_table_name}")
        else:
            str_sheet = 0

        try:
            df_ = pd.read_excel(
                str_path_file,
                skiprows=0,
                names=list(dict_dtypes.keys()),
                sheet_name=str_sheet,
                thousands=".",
                decimal=",",
            )
        except ValueError:
            df_ = pd.read_excel(
                str_path_file,
                skiprows=0,
                names=list(dict_dtypes.keys())[:-1],
                sheet_name=str_sheet,
                thousands=".",
                decimal=",",
                engine="openpyxl",
            )

        df_ = _drop_sparse_rows(df_)

        if "relatorio-consolidado-anual" in str_file_name_like and dt_date_ref is not None:
            df_["data_pregao"] = dt_date_ref.strftime("%d/%m/%Y")

        for str_col, dtype in dict_load_dtypes.items():
            if issubclass(dtype, Number):
                df_[str_col] = [0.0 if x == "-" else x for x in df_[str_col]]
            elif dtype == str:
                df_[str_col] = [str(x).strip() for x in df_[str_col]]
            elif dtype in [float, int]:
                df_[str_col] = [0 if x == "-" else x for x in df_[str_col]]
            df_[str_col] = df_[str_col].astype(dtype)

        for str_col in list_cols_dt:
            df_[str_col] = ["01/01/2100" if x == "-" else x for x in df_[str_col]]
            df_[str_col] = [
                _cls_dates.str_date_to_date(d, "DD/MM/AAAA") for d in df_[str_col]
            ]

        df_ = _add_pk(df_, str_table_name)
        return df_

    def _fetch_bonus_shares(
        self,
        str_file_name_like: str,
        dict_dtypes: dict[str, Any],
        dt_date_ref: date | None,
    ) -> pd.DataFrame:
        df_mov = self._fetch_excel(
            str_file_name_like, dict_dtypes, "b3_movimentacao", dt_date_ref
        )
        list_cols = list(df_mov.columns)
        df_mov["ano_ref"] = [_cls_dates.year_number(d) for d in df_mov["data_pregao"]]
        df_mov = df_mov[df_mov["movimentacao"] == "Bonificação em Ativos"]
        df_mov["TICKER"] = [str(x.split("-")[0]).strip() for x in df_mov["produto"]]

        list_ser: list = []
        for str_ticker in df_mov["TICKER"].unique():
            df_bonif = fetch_bonus_shares(str_ticker)
            list_ser.extend(df_bonif.to_dict(orient="records"))

        df_bonif_all = pd.DataFrame(list_ser)
        df_mov = df_mov.merge(
            df_bonif_all, how="left", on=["TICKER", "ano_ref"], suffixes=("", "_")
        )
        df_mov["valor_operacao"] = (
            df_mov["quantidade"].astype(float) * df_mov["valor_base"].astype(float)
        )
        list_cols = [c for c in list_cols if c != "preco_unitario"]
        list_cols.append("valor_base")
        df_mov = df_mov[list_cols].rename(columns={"valor_base": "preco_unitario"})
        return df_mov

    def import_job(self, cls_job: TradeImportJob) -> ImportResultDTO:
        """Fetch the Excel file and insert its rows into PostgreSQL.

        Parameters
        ----------
        cls_job : TradeImportJob
            Describes the file and target table.

        Returns
        -------
        ImportResultDTO
            Rows processed and status.
        """
        if cls_job.table_name == "bonificacao_acoes":
            df_ = self._fetch_bonus_shares(
                cls_job.file_name_like, cls_job.dict_dtypes, cls_job.dt_date_ref
            )
        else:
            df_ = self._fetch_excel(
                cls_job.file_name_like,
                cls_job.dict_dtypes,
                cls_job.table_name,
                cls_job.dt_date_ref,
            )

        list_records = df_.to_dict("records")
        self._db().insert(list_records, cls_job.table_name, bool_insert_or_ignore=True)
        return ImportResultDTO(
            table_name=cls_job.table_name,
            rows_processed=len(list_records),
            status="ok",
        )


# ---------------------------------------------------------------------------
# Module-level helpers (no state, no lifecycle → plain functions)
# ---------------------------------------------------------------------------

def _drop_sparse_rows(df_: pd.DataFrame, int_max_missing: int = 3) -> pd.DataFrame:
    """Drop rows that have more than int_max_missing missing values."""
    bool_missing = (
        df_.isna() | (df_ == "-") | (df_ == "") | (df_ == " ")
    )
    int_max_missing = min(int(0.5 * len(df_.columns)), int_max_missing)
    return df_[bool_missing.sum(axis=1) <= int_max_missing].copy()


def _add_pk(df_: pd.DataFrame, str_table_name: str) -> pd.DataFrame:
    """Add a composite primary key column to the DataFrame."""
    if str_table_name in ("b3_movimentacao", "b3_bonificacao_acoes"):
        df_["pk_movimentacao"] = (
            df_["entrada_saida"].astype(str)
            + df_["data_pregao"].apply(lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d))
            + df_["movimentacao"].astype(str)
            + df_["produto"].astype(str)
            + df_["quantidade"].astype(str).str.replace(".", ",")
            + df_["preco_unitario"].astype(str).str.replace(".", ",")
            + df_["valor_operacao"].astype(str).str.replace(".", ",")
        )
    elif str_table_name == "b3_negociacao":
        df_["pk_negociacao"] = (
            df_["data_negocio"].apply(lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d))
            + df_["tipo_movimentacao"].astype(str)
            + df_["ticker"].astype(str)
            + df_["quantidade"].astype(str).str.replace(".", ",")
            + df_["preco"].astype(str).str.replace(".", ",")
        )
    return df_
```

- [ ] **Step 5: Write `__init__.py` files and factories**

`src/capabilities/import_trades/application/__init__.py`:
```python
"""Application layer for import_trades — exports factory function."""

from __future__ import annotations

from .use_cases import ImportTrades
from ..domain.entities import TradeImportJob


def import_trades(
    list_jobs: list[TradeImportJob],
    cls_repo: "import_trades.domain.ports.TradeImportRepository",
) -> list:
    """Factory: create use-case and execute."""
    return ImportTrades(cls_repo).execute(list_jobs)
```

Create empty `__init__.py` for: `src/capabilities/import_trades/__init__.py`, `src/capabilities/import_trades/domain/__init__.py`, `src/capabilities/import_trades/infrastructure/__init__.py`.

- [ ] **Step 6: Commit**

```bash
git add src/capabilities/import_trades/
git commit -m "feat: add import_trades ddd capability for b3 excel ingestion"
```

---

## Task 6: `declaration_rv` capability

**Files to create:**
- `src/capabilities/declaration_rv/__init__.py`
- `src/capabilities/declaration_rv/domain/__init__.py`
- `src/capabilities/declaration_rv/domain/enums.py`
- `src/capabilities/declaration_rv/domain/entities.py`
- `src/capabilities/declaration_rv/domain/dto.py`
- `src/capabilities/declaration_rv/domain/ports.py`
- `src/capabilities/declaration_rv/application/__init__.py`
- `src/capabilities/declaration_rv/application/use_cases.py`
- `src/capabilities/declaration_rv/infrastructure/__init__.py`
- `src/capabilities/declaration_rv/infrastructure/repositories.py`

- [ ] **Step 1: Write domain layer**

`src/capabilities/declaration_rv/domain/enums.py`:
```python
"""Domain enums for declaration_rv."""

from __future__ import annotations

from enum import Enum


class IncomeCategory(str, Enum):
    EXEMPT_DIVIDEND = "exempt_dividend"
    TAXABLE_JCP = "taxable_jcp"
    TAXABLE_MONETARY_UPDATE = "taxable_monetary_update"
    TAXABLE_LENDING = "taxable_lending"
    EXEMPT_REIMBURSEMENT = "exempt_reimbursement"
    EXEMPT_FRACTION_AUCTION = "exempt_fraction_auction"
    EXEMPT_BONUS_SHARES = "exempt_bonus_shares"
```

`src/capabilities/declaration_rv/domain/entities.py`:
```python
"""Domain entities for declaration_rv."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class PortfolioPosition:
    """Represents a ticker's year-end position for IRPF declaration."""

    str_ticker: str
    str_cnpj: str
    str_company_name: str
    int_quantity: int
    decimal_avg_buy_price: Decimal
    decimal_financial_position: Decimal


@dataclass
class TaxEvent:
    """Represents a single taxable or exempt income event."""

    str_ticker: str
    str_cnpj: str
    str_company_name: str
    str_event_type: str
    decimal_amount: Decimal


@dataclass
class DeclarationData:
    """Aggregated data for one IRPF declaration year."""

    int_year: int
    list_positions: list[PortfolioPosition] = field(default_factory=list)
    list_exempt_dividends: list[TaxEvent] = field(default_factory=list)
    list_taxable_jcp: list[TaxEvent] = field(default_factory=list)
    list_taxable_monetary_update: list[TaxEvent] = field(default_factory=list)
    decimal_lending_income: Decimal = field(default=Decimal("0"))
    decimal_reimbursement: Decimal = field(default=Decimal("0"))
    list_fraction_auction: list[TaxEvent] = field(default_factory=list)
    list_bonus_shares: list[TaxEvent] = field(default_factory=list)
```

`src/capabilities/declaration_rv/domain/dto.py`:
```python
"""DTOs for declaration_rv."""

from __future__ import annotations

from typing import TypedDict


class DeclarationReportDTO(TypedDict):
    """Output DTO: the declaration text and the underlying year."""

    int_year: int
    str_report: str
```

`src/capabilities/declaration_rv/domain/ports.py`:
```python
"""Ports for declaration_rv."""

from __future__ import annotations

from typing import Protocol

from .entities import DeclarationData


class DeclarationRepository(Protocol):
    """Outbound port: fetch all data needed for one IRPF year."""

    def fetch(self, int_year: int) -> DeclarationData: ...
```

- [ ] **Step 2: Write `application/use_cases.py`**

```python
"""Use cases for declaration_rv."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from ..domain.dto import DeclarationReportDTO
from ..domain.entities import DeclarationData, PortfolioPosition, TaxEvent
from ..domain.ports import DeclarationRepository


class GenerateDeclaration:
    """Build IRPF declaration report text from PostgreSQL data.

    Parameters
    ----------
    cls_repo : DeclarationRepository
        Data-fetching port.
    dict_cfg : dict
        Declaration config from inputs.yaml (the ``declaration_rv`` key).
    """

    def __init__(self, cls_repo: DeclarationRepository, dict_cfg: dict) -> None:
        self._cls_repo = cls_repo
        self._dict_cfg = dict_cfg

    def execute(self, int_year: int) -> DeclarationReportDTO:
        """Generate the declaration report for the given base year.

        Parameters
        ----------
        int_year : int
            IRPF base year (e.g. 2024).

        Returns
        -------
        DeclarationReportDTO
            Dict with int_year and str_report.
        """
        cls_data = self._cls_repo.fetch(int_year)
        str_report = _build_report(cls_data, self._dict_cfg)
        return DeclarationReportDTO(int_year=int_year, str_report=str_report)


def _fmt_decimal(decimal_val: Decimal, int_places: int = 2) -> str:
    """Format Decimal as Brazilian currency string (comma as decimal separator)."""
    str_quantize = "0." + "0" * int_places
    return str(decimal_val.quantize(Decimal(str_quantize), rounding=ROUND_DOWN)).replace(".", ",")


def _build_report(cls_data: DeclarationData, dict_cfg: dict) -> str:
    """Assemble all declaration sections into a single string."""
    int_places = dict_cfg.get("decimal_places", 2)
    dict_contrib = dict_cfg["contributor"]

    str_out = "**************** 0. CONTRIBUTOR DATA ****************\n\n"
    str_out += f"Full Name: {dict_contrib['full_name']}\n"
    str_out += f"CPF: {dict_contrib['cpf']}\n\n"

    str_out += "**************** 1. ASSETS AND RIGHTS ****************\n\n"
    for cls_pos in cls_data.list_positions:
        str_out += _section_position(cls_pos, cls_data.int_year, dict_cfg, int_places)

    str_out += "\n\n**************** 2. DIVIDENDS — EXEMPT NON-TAXABLE INCOME ****************\n\n"
    for cls_evt in cls_data.list_exempt_dividends:
        str_out += _section_income_event(cls_evt, dict_cfg["exempt_non_taxable_income"], int_places)

    str_out += "\n\n**************** 3. JCP — TAXABLE INCOME ****************\n\n"
    for cls_evt in cls_data.list_taxable_jcp:
        str_out += _section_income_event(cls_evt, dict_cfg["taxable_income_jcp"], int_places)

    str_out += "\n\n**************** 4. FRACTION AUCTION — EXEMPT NON-TAXABLE INCOME ****************\n\n"
    for cls_evt in cls_data.list_fraction_auction:
        str_out += _section_fraction_auction(cls_evt, dict_cfg["exempt_non_taxable_fraction_auction"], int_places)

    str_out += "\n\n**************** 5. BONUS SHARES — EXEMPT NON-TAXABLE INCOME ****************\n\n"
    for cls_evt in cls_data.list_bonus_shares:
        str_out += _section_income_event(cls_evt, dict_cfg["exempt_non_taxable_bonus_shares"], int_places)

    str_out += "\n\n**************** 6. MONETARY UPDATE INCOME — TAXABLE ****************\n\n"
    for cls_evt in cls_data.list_taxable_monetary_update:
        str_out += _section_income_event(cls_evt, dict_cfg["taxable_income_monetary_update"], int_places)

    str_out += "\n\n**************** 7. STOCK LENDING INCOME — TAXABLE ****************\n\n"
    str_out += _section_scalar(
        cls_data.decimal_lending_income, dict_cfg["taxable_income_stock_lending"], int_places
    )

    str_out += "\n\n**************** 8. LENDING REIMBURSEMENT — EXEMPT ****************\n\n"
    str_out += _section_reimbursement(
        cls_data.decimal_reimbursement, dict_cfg["exempt_non_taxable_reimbursement"], int_places
    )

    return str_out


def _section_position(
    cls_pos: PortfolioPosition,
    int_year: int,
    dict_cfg: dict,
    int_places: int,
) -> str:
    dict_c = dict_cfg["assets_and_rights"]
    str_out = f"\\\\ TICKER: {cls_pos.str_ticker}\n"
    str_out += f"{dict_c['group']['key']}{dict_c['group']['value']}\n"
    str_out += f"{dict_c['code']['key']}{dict_c['code']['value']}\n"
    str_out += f"{dict_c['location']['key']}{dict_c['location']['value']}\n"
    str_out += f"{dict_c['cnpj']['key']}{cls_pos.str_cnpj}\n"
    str_out += (
        f"{dict_c['description']['key']}"
        + dict_c["description"]["value"].format(
            cls_pos.str_ticker,
            cls_pos.int_quantity,
            _fmt_decimal(cls_pos.decimal_avg_buy_price, int_places),
        )
        + "\n"
    )
    str_out += f"{dict_c['traded_on_exchange']['key']}{dict_c['traded_on_exchange']['value']}\n"
    str_out += f"{dict_c['trading_code']['key']}{cls_pos.str_ticker}\n"
    str_out += (
        f"{dict_c['year_end_balance']['key'].format(f'31/12/{int_year}')}"
        f"{_fmt_decimal(cls_pos.decimal_financial_position, int_places)}\n\n"
    )
    return str_out


def _section_income_event(cls_evt: TaxEvent, dict_c: dict, int_places: int) -> str:
    str_out = f"\\\\ TICKER: {cls_evt.str_ticker}\n"
    str_out += f"{dict_c['income_type']['key']}{dict_c['income_type']['value']}\n"
    str_out += f"{dict_c['payer_cnpj']['key']}{cls_evt.str_cnpj}\n"
    str_out += f"{dict_c['payer_name']['key']}{cls_evt.str_company_name}\n"
    str_out += f"{dict_c['amount']['key']}{_fmt_decimal(cls_evt.decimal_amount, int_places)}\n\n"
    return str_out


def _section_fraction_auction(cls_evt: TaxEvent, dict_c: dict, int_places: int) -> str:
    str_out = _section_income_event(cls_evt, dict_c, int_places)
    # insert description line before amount
    str_desc = f"{dict_c['description']['key']}{dict_c['description']['value'].format(cls_evt.str_ticker.upper())}\n"
    str_out = str_out.replace(f"{dict_c['amount']['key']}", str_desc + f"{dict_c['amount']['key']}")
    return str_out


def _section_scalar(decimal_val: Decimal, dict_c: dict, int_places: int) -> str:
    str_out = f"{dict_c['income_type']['key']}{dict_c['income_type']['value']}\n"
    str_out += f"{dict_c['payer_cnpj']['key']}{dict_c['payer_cnpj']['value']}\n"
    str_out += f"{dict_c['payer_name']['key']}{dict_c['payer_name']['value']}\n"
    str_out += f"{dict_c['amount']['key']}{_fmt_decimal(decimal_val, int_places)}\n\n"
    return str_out


def _section_reimbursement(decimal_val: Decimal, dict_c: dict, int_places: int) -> str:
    str_out = _section_scalar(decimal_val, dict_c, int_places)
    str_desc = f"{dict_c['description']['key']}{dict_c['description']['value']}\n"
    str_out = str_out.replace(f"{dict_c['amount']['key']}", str_desc + f"{dict_c['amount']['key']}")
    return str_out
```

- [ ] **Step 3: Write `infrastructure/repositories.py`**

```python
"""Infrastructure repository for declaration_rv."""

from __future__ import annotations

import os
from decimal import Decimal

import pandas as pd
from stpstone.utils.connections.databases.sql.postgresql_db import PostgreSQLDB

from ..domain.entities import DeclarationData, PortfolioPosition, TaxEvent
from ..domain.ports import DeclarationRepository


class PostgresDeclarationRepository:
    """Fetch declaration data from PostgreSQL views.

    Parameters
    ----------
    str_host : str
    int_port : int
    str_dbname : str
    str_user : str
    str_password : str
    dict_cfg : dict
        The ``db`` key from inputs.yaml.
    """

    def __init__(
        self,
        str_host: str,
        int_port: int,
        str_dbname: str,
        str_user: str,
        str_password: str,
        dict_cfg: dict,
    ) -> None:
        self._str_host = str_host
        self._int_port = int_port
        self._str_dbname = str_dbname
        self._str_user = str_user
        self._str_password = str_password
        self._dict_cfg = dict_cfg

    def _db(self) -> PostgreSQLDB:
        return PostgreSQLDB(
            dbname=self._str_dbname,
            user=self._str_user,
            password=self._str_password,
            host=self._str_host,
            port=self._int_port,
        )

    def _read(self, str_query: str) -> pd.DataFrame:
        return self._db().read(str_query)

    def fetch(self, int_year: int) -> DeclarationData:
        """Query all PostgreSQL views and return a DeclarationData entity."""
        dict_q = self._dict_cfg
        str_col_op = dict_q["col_operation_value"]
        str_col_ticker = dict_q["col_ticker"]
        str_col_inst = dict_q["col_instrument"]
        str_col_cnpj = dict_q["col_cnpj"]
        str_col_company = dict_q["col_company_name"]
        str_col_qty = dict_q["col_position_side"]
        str_col_avg = dict_q["col_avg_buy_price"]
        str_col_fin = dict_q["col_financial_position"]

        df_active = self._read(dict_q["query_active_tickers_base_year"].format(int_year, int_year))
        df_avg_price = self._read(dict_q["query_avg_price_portfolio"])
        df_exempt_div = self._read(dict_q["query_exempt_dividends"].format(int_year))
        df_taxable_jcp = self._read(dict_q["query_taxable_jcp"].format(int_year))
        df_monetary = self._read(dict_q["query_monetary_update_income"].format(int_year))
        df_lending = self._read(dict_q["query_stock_lending_income"].format(int_year))
        df_reimbursement = self._read(dict_q["query_lending_reimbursement"].format(int_year))
        df_fraction = self._read(dict_q["query_fraction_auction"].format(int_year))
        df_bonus = self._read(dict_q["query_bonus_shares"].format(int_year))

        list_tickers = df_active[str_col_ticker].dropna().unique().tolist()

        list_positions: list[PortfolioPosition] = []
        for str_ticker in list_tickers:
            df_row = df_avg_price[df_avg_price[str_col_inst] == str_ticker]
            if df_row.empty:
                continue
            row = df_row.iloc[0]
            list_positions.append(PortfolioPosition(
                str_ticker=str_ticker,
                str_cnpj=str(row[str_col_cnpj]),
                str_company_name=str(row[str_col_company]),
                int_quantity=int(row[str_col_qty]),
                decimal_avg_buy_price=Decimal(str(row[str_col_avg])),
                decimal_financial_position=Decimal(str(row[str_col_fin])),
            ))

        def _evt(df_: pd.DataFrame, str_ticker: str) -> TaxEvent | None:
            df_row = df_[df_[str_col_ticker] == str_ticker]
            if df_row.empty:
                return None
            row = df_row.iloc[0]
            return TaxEvent(
                str_ticker=str_ticker,
                str_cnpj=str(row[str_col_cnpj]),
                str_company_name=str(row[str_col_company]),
                str_event_type=str(row.get(dict_q["col_movement_type"], "")),
                decimal_amount=Decimal(str(row[str_col_op])),
            )

        list_exempt_dividends = [e for t in list_tickers if (e := _evt(df_exempt_div, t))]
        list_taxable_jcp = [e for t in list_tickers if (e := _evt(df_taxable_jcp, t))]
        list_monetary = [e for t in list_tickers if (e := _evt(df_monetary, t))]
        list_fraction = [e for t in list_tickers if (e := _evt(df_fraction, t))]
        list_bonus = [e for t in list_tickers if (e := _evt(df_bonus, t))]

        decimal_lending = (
            Decimal(str(df_lending[str_col_op].iloc[0]))
            if not df_lending.empty else Decimal("0")
        )
        decimal_reimbursement = (
            Decimal(str(df_reimbursement[str_col_op].iloc[0]))
            if not df_reimbursement.empty else Decimal("0")
        )

        return DeclarationData(
            int_year=int_year,
            list_positions=list_positions,
            list_exempt_dividends=list_exempt_dividends,
            list_taxable_jcp=list_taxable_jcp,
            list_taxable_monetary_update=list_monetary,
            decimal_lending_income=decimal_lending,
            decimal_reimbursement=decimal_reimbursement,
            list_fraction_auction=list_fraction,
            list_bonus_shares=list_bonus,
        )
```

- [ ] **Step 4: Write `__init__.py` files**

Create empty `__init__.py` for: `src/capabilities/declaration_rv/__init__.py`, `src/capabilities/declaration_rv/domain/__init__.py`, `src/capabilities/declaration_rv/application/__init__.py`, `src/capabilities/declaration_rv/infrastructure/__init__.py`.

`src/capabilities/declaration_rv/application/__init__.py`:
```python
"""Application layer for declaration_rv — exports factory function."""

from __future__ import annotations

from .use_cases import GenerateDeclaration
from ..domain.dto import DeclarationReportDTO
from ..domain.ports import DeclarationRepository


def generate_declaration(
    int_year: int,
    cls_repo: DeclarationRepository,
    dict_cfg: dict,
) -> DeclarationReportDTO:
    """Factory: create use-case and execute."""
    return GenerateDeclaration(cls_repo, dict_cfg).execute(int_year)
```

- [ ] **Step 5: Commit**

```bash
git add src/capabilities/declaration_rv/
git commit -m "feat: add declaration_rv ddd capability for irpf report generation"
```

---

## Task 7: Wiring and orchestration

**Files:**
- Modify: `src/app/container.py`
- Modify: `src/main.py`

- [ ] **Step 1: Rewrite `src/app/container.py`**

```python
"""Composition root: wire infrastructure to application factories."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from stpstone.utils.calendars.calendar_br import DatesBRAnbima

from capabilities.declaration_rv.application import generate_declaration
from capabilities.declaration_rv.domain.dto import DeclarationReportDTO
from capabilities.declaration_rv.infrastructure.repositories import PostgresDeclarationRepository
from capabilities.import_trades.application import import_trades
from capabilities.import_trades.domain.entities import TradeImportJob
from capabilities.import_trades.domain.dto import ImportResultDTO
from capabilities.import_trades.infrastructure.repositories import PostgresTradeImportRepository
from chassis.db_schema.application import build_database_handler
from src.config.startup import YAML_INPUTS


_cls_dates = DatesBRAnbima()


@dataclass(frozen=True)
class AppContainer:
    """Pre-wired application entry points."""

    fn_import_trades: Callable[[list[TradeImportJob]], list[ImportResultDTO]]
    fn_generate_declaration: Callable[[int], DeclarationReportDTO]


def _build_jobs() -> list[TradeImportJob]:
    """Build the ordered list of import jobs from config."""
    int_year_ref = _cls_dates.year_number(_cls_dates.curr_date())
    dt_date_ref: date = _cls_dates.build_date(int_year_ref, 1, 1)
    int_year_prev = int_year_ref - 1

    return [
        TradeImportJob(
            file_name_like=f"movimentacao-{int_year_ref}*.xlsx",
            dict_dtypes={
                "entrada_saida": str, "data_pregao": "date", "movimentacao": str,
                "produto": str, "instituicao": str, "quantidade": float,
                "preco_unitario": float, "valor_operacao": float,
            },
            table_name="b3_movimentacao",
            dt_date_ref=dt_date_ref,
        ),
        TradeImportJob(
            file_name_like=f"negociacao-{int_year_ref}*.xlsx",
            dict_dtypes={
                "data_negocio": "date", "tipo_movimentacao": str, "mercado": str,
                "prazo_vencimento": "date", "instituicao": str, "ticker": str,
                "quantidade": int, "preco": float, "valor": float,
            },
            table_name="b3_negociacao",
            dt_date_ref=dt_date_ref,
        ),
        TradeImportJob(
            file_name_like=f"relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str, "instituicao": str, "conta": int,
                "codigo_negociacao": str, "cnpj": str, "codigo_isin": str,
                "tipo": str, "escriturador": str, "quantidade": int,
                "quantidade_disp": int, "quantidade_indisp": int, "motivo": str,
                "preco_fechamento": float, "valor_atualizado": float, "data_pregao": "date",
            },
            table_name="b3_posicao_acoes",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str, "instituicao": str, "natureza": str,
                "num_contrato": str, "modalidade": str, "opa": str,
                "liquidacao_antecipada": str, "taxa": float, "comissao": float,
                "data_registro": "date", "data_vencimento": "date",
                "quantidade": int, "preco_fechamento": float,
                "valor_atualizado": float, "data_pregao": "date",
            },
            table_name="b3_posicao_emprestimos",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str, "tipo_evento": str,
                "valor_liquido": float, "data_pregao": "date",
            },
            table_name="b3_proventos_recebidos",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"relatorio-consolidado-anual-{int_year_prev}.xlsx",
            dict_dtypes={
                "produto": str, "tipo_evento": str,
                "valor_liquido": float, "data_pregao": "date",
            },
            table_name="b3_reembolso_emprestimos",
            dt_date_ref=_cls_dates.build_date(int_year_prev, 12, 31),
        ),
        TradeImportJob(
            file_name_like=f"movimentacao-{int_year_ref}*.xlsx",
            dict_dtypes={
                "entrada_saida": str, "data_pregao": "date", "movimentacao": str,
                "produto": str, "instituicao": str, "quantidade": float,
                "preco_unitario": float, "valor_operacao": float,
            },
            table_name="b3_bonificacao_acoes",
            dt_date_ref=dt_date_ref,
        ),
    ]


def build() -> AppContainer:
    """Instantiate infrastructure and bind to application factories.

    Reads credentials from environment variables set via .env.
    """
    str_host = os.environ["DB_HOST"]
    int_port = int(os.environ["DB_PORT"])
    str_dbname = os.environ["DB_NAME"]
    str_user = os.environ["DB_USER"]
    str_password = os.environ["DB_PASSWORD"]

    # B3 files live in ~/daily_infos/<YYYY-MM-DD>/ — same folder as today's outputs
    str_data_path = str(
        Path(YAML_INPUTS["import_trades"]["data_path"]).expanduser()
        / str(_cls_dates.curr_date())
    )

    cls_import_repo = PostgresTradeImportRepository(
        str_data_path=str_data_path,
        str_host=str_host,
        int_port=int_port,
        str_dbname=str_dbname,
        str_user=str_user,
        str_password=str_password,
    )
    cls_decl_repo = PostgresDeclarationRepository(
        str_host=str_host,
        int_port=int_port,
        str_dbname=str_dbname,
        str_user=str_user,
        str_password=str_password,
        dict_cfg=YAML_INPUTS["db"],
    )

    int_year_decl = (
        _cls_dates.year_number(_cls_dates.curr_date())
        - YAML_INPUTS["declaration_rv"]["base_year_offset"]
    )

    return AppContainer(
        fn_import_trades=lambda list_jobs: import_trades(list_jobs, cls_import_repo),
        fn_generate_declaration=lambda: generate_declaration(
            int_year_decl, cls_decl_repo, YAML_INPUTS["declaration_rv"]
        ),
    )
```

- [ ] **Step 2: Rewrite `src/main.py`**

```python
"""Service entrypoint: bootstrap → wire → run → teardown."""

from __future__ import annotations

from stpstone.utils.parsers.json import JsonFiles
from stpstone.utils.parsers.txt import HandlingTXTFiles

from app.bootstrap import cls_create_log, init, teardown
from app.container import build, _build_jobs
from src.config.startup import (
    CLS_MS_TEAMS,
    ENVIRONMENT,
    LOGGER,
    MSG_MS_TEAMS,
    PATH_JSON,
    PATH_TXT,
    YAML_INPUTS,
    YAML_WEBHOOKS,
)


float_start_time = init()
cls_container = build()

# 1. Import B3 Excel files into PostgreSQL (only if enabled in inputs.yaml)
if YAML_INPUTS.get("run_import_trades", True):
    cls_create_log.log_message(LOGGER, "Starting import_trades pipeline", "info")
    list_results = cls_container.fn_import_trades(_build_jobs())
    for dict_result in list_results:
        cls_create_log.log_message(
            LOGGER,
            f"Imported {dict_result['rows_processed']} rows into {dict_result['table_name']}",
            "info",
        )
    JsonFiles().dump_message({"import_results": list_results}, str(PATH_JSON))

# 2. Generate IRPF declaration report
if YAML_INPUTS.get("run_declaration_rv", True):
    cls_create_log.log_message(LOGGER, "Starting declaration_rv pipeline", "info")
    dict_report = cls_container.fn_generate_declaration()
    cls_create_log.log_message(LOGGER, f"Declaration year: {dict_report['int_year']}", "info")
    HandlingTXTFiles().write_file(str(PATH_TXT), dict_report["str_report"])
    cls_create_log.log_message(LOGGER, f"Report written to {PATH_TXT}", "info")

# 3. Notify MS Teams in production
if ENVIRONMENT == "production":
    CLS_MS_TEAMS.send_message(str_msg=MSG_MS_TEAMS, str_title=YAML_WEBHOOKS["ms_teams"]["title"])

teardown(float_start_time)
```

- [ ] **Step 3: Add run flags to `inputs.yaml`** (top-level, before the paths):

```yaml
run_import_trades: true
run_declaration_rv: true
```

- [ ] **Step 4: Commit**

```bash
git add src/app/container.py src/main.py src/config/inputs.yaml
git commit -m "feat: wire import_trades and declaration_rv into app container and main"
```

---

## Task 8: Tests

**Files:**
- Create: `tests/unit/test_generate_declaration.py`
- Create: `tests/unit/test_import_trades.py`

- [ ] **Step 1: Write failing test for `GenerateDeclaration`**

`tests/unit/test_generate_declaration.py`:
```python
"""Unit tests for GenerateDeclaration use case."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from capabilities.declaration_rv.application.use_cases import GenerateDeclaration
from capabilities.declaration_rv.domain.entities import (
    DeclarationData,
    PortfolioPosition,
    TaxEvent,
)

_MOCK_CFG = {
    "decimal_places": 2,
    "contributor": {"full_name": "Test User", "cpf": "000.000.000-00"},
    "assets_and_rights": {
        "group": {"key": "Group: ", "value": "03"},
        "code": {"key": "Code: ", "value": "01"},
        "location": {"key": "Location: ", "value": "105"},
        "cnpj": {"key": "CNPJ: "},
        "description": {"key": "Desc: ", "value": "{} {} {} shares"},
        "traded_on_exchange": {"key": "Exchange: ", "value": "Yes"},
        "trading_code": {"key": "Code: "},
        "year_end_balance": {"key": "Balance {}: "},
    },
    "exempt_non_taxable_income": {
        "income_type": {"key": "Type: ", "value": "09"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
    "taxable_income_jcp": {
        "income_type": {"key": "Type: ", "value": "10"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
    "taxable_income_monetary_update": {
        "income_type": {"key": "Type: ", "value": "06"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
    "taxable_income_stock_lending": {
        "income_type": {"key": "Type: ", "value": "06"},
        "payer_cnpj": {"key": "CNPJ: ", "value": "09346601000125"},
        "payer_name": {"key": "Name: ", "value": "B3 S.A."},
        "amount": {"key": "Amount: "},
    },
    "exempt_non_taxable_reimbursement": {
        "income_type": {"key": "Type: ", "value": "99"},
        "payer_cnpj": {"key": "CNPJ: ", "value": "09346601000125"},
        "payer_name": {"key": "Name: ", "value": "B3 S.A."},
        "description": {"key": "Desc: ", "value": "REIMBURSEMENT"},
        "amount": {"key": "Amount: "},
    },
    "exempt_non_taxable_fraction_auction": {
        "income_type": {"key": "Type: ", "value": "99"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "description": {"key": "Desc: ", "value": "AUCTION - {}"},
        "amount": {"key": "Amount: "},
    },
    "exempt_non_taxable_bonus_shares": {
        "income_type": {"key": "Type: ", "value": "18"},
        "payer_cnpj": {"key": "CNPJ: "},
        "payer_name": {"key": "Name: "},
        "amount": {"key": "Amount: "},
    },
}


def test_generate_declaration_contains_contributor_name() -> None:
    cls_repo = MagicMock()
    cls_repo.fetch.return_value = DeclarationData(
        int_year=2024,
        list_positions=[
            PortfolioPosition(
                str_ticker="PETR4",
                str_cnpj="33000167000101",
                str_company_name="PETROBRAS",
                int_quantity=100,
                decimal_avg_buy_price=Decimal("30.00"),
                decimal_financial_position=Decimal("3000.00"),
            )
        ],
        decimal_lending_income=Decimal("50.00"),
        decimal_reimbursement=Decimal("10.00"),
    )
    cls_use_case = GenerateDeclaration(cls_repo, _MOCK_CFG)
    dict_result = cls_use_case.execute(2024)
    assert "Test User" in dict_result["str_report"]
    assert "PETR4" in dict_result["str_report"]


def test_generate_declaration_year_is_returned() -> None:
    cls_repo = MagicMock()
    cls_repo.fetch.return_value = DeclarationData(int_year=2023)
    cls_use_case = GenerateDeclaration(cls_repo, _MOCK_CFG)
    dict_result = cls_use_case.execute(2023)
    assert dict_result["int_year"] == 2023
```

- [ ] **Step 2: Write failing test for `ImportTrades`**

`tests/unit/test_import_trades.py`:
```python
"""Unit tests for ImportTrades use case."""

from __future__ import annotations

from unittest.mock import MagicMock

from capabilities.import_trades.application.use_cases import ImportTrades
from capabilities.import_trades.domain.dto import ImportResultDTO
from capabilities.import_trades.domain.entities import TradeImportJob


def test_import_trades_delegates_to_repo() -> None:
    cls_repo = MagicMock()
    cls_repo.import_job.return_value = ImportResultDTO(
        table_name="b3_movimentacao", rows_processed=42, status="ok"
    )
    list_jobs = [
        TradeImportJob(
            file_name_like="movimentacao-2025*.xlsx",
            dict_dtypes={"entrada_saida": str},
            table_name="b3_movimentacao",
        )
    ]
    list_results = ImportTrades(cls_repo).execute(list_jobs)
    cls_repo.import_job.assert_called_once()
    assert list_results[0]["rows_processed"] == 42


def test_import_trades_empty_jobs_returns_empty_list() -> None:
    cls_repo = MagicMock()
    list_results = ImportTrades(cls_repo).execute([])
    assert list_results == []
    cls_repo.import_job.assert_not_called()
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
poetry run python -m pytest tests/unit/test_generate_declaration.py tests/unit/test_import_trades.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_generate_declaration.py tests/unit/test_import_trades.py
git commit -m "test: add unit tests for generate_declaration and import_trades use cases"
```

---

## Task 9: README user guide

**Files:**
- Modify (or create if missing): `README.md`

- [ ] **Step 1: Rewrite `README.md`**

Replace the full contents of `README.md` with:

```markdown
# irpf

IRPF (Brazilian income-tax) declaration helper — imports B3 trade data from Excel exports
into PostgreSQL and generates a ready-to-copy declaration text file for all variable-income
assets (stocks, FIIs, ETFs).

## How it works

```
B3 Excel exports → import_trades → PostgreSQL → declaration_rv → report .txt
```

1. **`import_trades`** reads your B3 Excel files and inserts the rows into PostgreSQL.
2. **`declaration_rv`** queries three PostgreSQL views and writes a structured declaration
   text file that you can copy section-by-section into the IRPF program.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12 | [python.org](https://www.python.org/downloads/) |
| Poetry | ≥ 1.8 | `pipx install poetry` |
| Docker + Docker Compose | ≥ 25 / v2 | [docs.docker.com](https://docs.docker.com/get-started/get-docker/) |

---

## First-time setup

```bash
# 1. Clone
git clone https://github.com/<your-org>/irpf.git
cd irpf

# 2. Copy and fill in credentials
cp .env.example .env
# Edit .env — set DB_USER, DB_PASSWORD, DB_NAME, and pgAdmin credentials

# 3. Install Python dependencies
poetry install

# 4. Start PostgreSQL and pgAdmin
docker compose up -d

# 5. Apply all DB migrations (creates tables + views)
poetry run alembic upgrade head
```

pgAdmin is available at **http://localhost:5050** (default credentials: `admin@irpf.local` / `admin`).

---

## Configuring your personal data

Open `src/config/inputs.yaml` and fill in the `declaration_rv.contributor` block:

```yaml
declaration_rv:
  contributor:
    full_name: "YOUR FULL LEGAL NAME"
    cpf: "000.000.000-00"
```

All other fields (paths, queries, label strings) are ready to use as-is.

---

## Where to put your B3 Excel files

Download your annual reports from [B3 Investor Area](https://www.investidor.b3.com.br/) and
place them in **`~/daily_infos/<YYYY-MM-DD>/`** — the same date-stamped folder where outputs
are written. For example, if you run on 2025-05-25, put the files in `~/daily_infos/2025-05-25/`.
The folder is created automatically when the app starts.

The base path is controlled by `inputs.yaml → import_trades.data_path` (default `~/daily_infos`);
the app appends today's date automatically.

### Expected file names (B3 export naming convention)

| Report | Filename pattern | Example |
|--------|-----------------|---------|
| Movements | `movimentacao-YYYY*.xlsx` | `movimentacao-2025-01-01_a_2025-12-31.xlsx` |
| Negotiations | `negociacao-YYYY*.xlsx` | `negociacao-01-01-2025_a_31-12-2025.xlsx` |
| Annual consolidated | `relatorio-consolidado-anual-YYYY.xlsx` | `relatorio-consolidado-anual-2024.xlsx` |

> The app picks the **most recent file** that matches each pattern — you do not need to rename
> anything after downloading.

### Where to download each report

1. Log in to [investidor.b3.com.br](https://www.investidor.b3.com.br/)
2. **Movements** → "Extrato" → "Movimentação" → select year → "Exportar"
3. **Negotiations** → "Extrato" → "Negociação" → select year → "Exportar"
4. **Annual consolidated** → "Extrato" → "Posição consolidada" → select year → "Exportar"

Place all three files in `~/daily_infos/data/` before running.

---

## Running the app

```bash
poetry run python src/main.py
```

The app will:
1. Read B3 Excel files from `~/daily_infos/<YYYY-MM-DD>/`
2. Insert all rows into PostgreSQL (skipping duplicates)
3. Query the three IRPF views
4. Write the declaration report to `~/daily_infos/<today>/`

To run only one pipeline (skip the other), edit `inputs.yaml`:

```yaml
run_import_trades: true     # set false to skip Excel import
run_declaration_rv: true    # set false to skip report generation
```

---

## Output files

All outputs land in **`~/daily_infos/<YYYY-MM-DD>/`**, created automatically on each run.

| File | Contents |
|------|---------|
| `irpf-development_<USER>_<YYYYMMDD>_<HHMMSS>.log` | Execution log |
| `irpf-development_<USER>_<YYYYMMDD>_<HHMMSS>.json` | Import summary (rows per table) |
| `irpf-development_<USER>_<YYYYMMDD>_<HHMMSS>.txt` | **IRPF declaration report** ← copy this |

The `.txt` report contains 8 sections matching the IRPF program tabs:

```
0. CONTRIBUTOR DATA
1. ASSETS AND RIGHTS
2. DIVIDENDS — EXEMPT NON-TAXABLE INCOME
3. JCP — TAXABLE INCOME
4. FRACTION AUCTION — EXEMPT NON-TAXABLE INCOME
5. BONUS SHARES — EXEMPT NON-TAXABLE INCOME
6. MONETARY UPDATE INCOME — TAXABLE
7. STOCK LENDING INCOME — TAXABLE
8. LENDING REIMBURSEMENT — EXEMPT
```

---

## Yearly update workflow

Each year you only need to:

1. Download new B3 Excel files into `~/daily_infos/data/`
2. Update `inputs.yaml → declaration_rv.contributor` if anything changed
3. Run `poetry run python src/main.py`

No schema changes are needed — the views recalculate from all historical data automatically.

---

## Database management

```bash
# Check current migration state
poetry run alembic current

# Apply pending migrations
poetry run alembic upgrade head

# Roll back one migration
poetry run alembic downgrade -1

# Roll back everything (destroys all tables and views)
poetry run alembic downgrade base

# Inspect tables and views in psql
docker exec -it irpf-postgresql-1 psql -U irpf_user -d wealth_db -c "\dt; \dv"
```

---

## Running tests

```bash
poetry run python -m pytest tests/unit/ -v
```

---

## Troubleshooting

**`Connection refused` on DB_HOST**
> The PostgreSQL container is not running. Run `docker compose up -d` and wait ~10s for the
> healthcheck to pass (`docker compose ps` shows "healthy").

**`FileNotFoundError: No such file: ...movimentacao-2025*.xlsx`**
> No matching B3 file found in `~/daily_infos/<today>/`. Download the file from B3, place it
> in `~/daily_infos/<YYYY-MM-DD>/` (today's date folder), and ensure it matches the expected
> name pattern (see table above).

**`alembic upgrade head` fails with `relation already exists`**
> The schema was created outside of Alembic. Roll back and let Alembic recreate it:
> ```bash
> docker compose down -v       # destroys DB volume — all data lost
> docker compose up -d
> poetry run alembic upgrade head
> ```

**Duplicate rows on re-import**
> The import uses `INSERT OR IGNORE` (via `bool_insert_or_ignore=True`) — duplicates are
> silently skipped based on the composite primary key. Re-running is always safe.

**`pgAdmin` shows no server**
> Add the server manually: right-click "Servers" → Register → Server.
> Connection: Host `postgresql`, Port `5432`, DB `wealth_db`, User/Password from `.env`.
> (Use the Docker service name `postgresql` as the host — not `localhost` — from inside pgAdmin.)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add user guide covering b3 file setup, run instructions, and troubleshooting"
```

---

## Task 10: Push and create PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin feat/declaration-rv
```

- [ ] **Step 2: Create PR**

```bash
gh pr create \
  --title "feat: port declaracao_rv into ddd skeleton with docker postgresql" \
  --base main \
  --body "$(cat <<'EOF'
## Summary

- Ported `declaracao_rv` source project into the DDD/hexagonal skeleton
- Added `import_trades` capability: reads B3 Excel files, inserts into PostgreSQL via stpstone `PostgreSQLDB`
- Added `declaration_rv` capability: queries PostgreSQL views, generates IRPF text report
- Replaced vendored stpstone with installed stpstone 3.1.1 (full API migration)
- Made solution generic: contributor info and paths live in `src/config/inputs.yaml`
- Output files land in `daily_infos/<yyyy-mm-dd>/` (cross-platform path via `~` expansion)
- Added Docker Compose with PostgreSQL 16 + pgAdmin4
- All code in English

## Test plan

- [ ] `docker compose up -d` starts postgresql and pgadmin with no errors
- [ ] pgAdmin reachable at `http://localhost:5050`
- [ ] `poetry run alembic upgrade head` creates all tables and views — verify with `\dt; \dv`
- [ ] `poetry run python -m pytest tests/unit/` — all 4 tests pass
- [ ] Place B3 xlsx files in `~/daily_infos/<YYYY-MM-DD>/` and run `poetry run python src/main.py`
- [ ] Verify `~/daily_infos/<today>/` contains `.log`, `.json`, and `.txt` output files
- [ ] Inspect the `.txt` report for all 8 IRPF declaration sections

🤖 Generated with [Claude Code](https://claude.ai/claude-code)
EOF
)"
```

---

## Verification

End-to-end:
1. `docker compose up -d` — postgres healthy, pgadmin accessible at `http://localhost:5050`
2. `cp .env.example .env` and fill in actual credentials
3. `poetry run alembic upgrade head` — all tables + 3 views created (verify with `\dt; \dv` in psql)
4. Place B3 xlsx files in `~/daily_infos/<today>/` (same date-stamped folder as outputs)
5. `poetry run python src/main.py`
6. Check `~/daily_infos/<today>/` for `.log`, `.json`, `.txt`
7. Inspect the `.txt` for all 8 IRPF declaration sections
8. `poetry run python -m pytest tests/unit/ -v` — 4 tests pass
9. To roll back schema: `poetry run alembic downgrade base`
