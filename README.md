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
# Edit .env — set TAXPAYER, TAXPAYER_FULL_NAME, TAXPAYER_CPF,
#             DB_USER, DB_PASSWORD, DB_NAME, and pgAdmin credentials

# 3. Bootstrap venv and pre-commit hooks
make init

# 4. Create your taxpayer schema and apply all DB migrations
make db-setup-schema

# 5. Download your B3 reports and place them in ~/daily_infos/<today>/
#    See "Where to put your B3 Excel files" below for the exact files,
#    naming convention, and step-by-step download instructions from
#    investidor.b3.com.br (Extrato → Movimentação / Negociação / Posição consolidada).

# 6. Run the app (also starts Docker services on subsequent runs)
make run
```

pgAdmin is available at **http://localhost:5050** (default credentials: `admin@irpf.local` / `admin`).

---

## Configuring your personal data

Your full name and CPF are read from `.env` — never committed to the repository:

```dotenv
TAXPAYER_FULL_NAME=YOUR FULL LEGAL NAME
TAXPAYER_CPF=000.000.000-00
```

All other fields in `src/config/inputs.yaml` (paths, queries, label strings) are ready to use as-is.

---

## Where to put your B3 Excel files

Download your annual reports from the B3 Investor Area and place them in
**`~/daily_infos/<YYYY-MM-DD>/`** — the same date-stamped folder where outputs are written.
For example, if you run on 2025-05-25, put the files in `~/daily_infos/2025-05-25/`.
The folder is created automatically when the app starts.

The base path is controlled by `inputs.yaml → import_trades.data_path` (default `~/daily_infos`);
the app appends today's date automatically.

### Expected file names

B3 exports use their default names — you only need to add the `<TAXPAYER>-` prefix
(the value of `TAXPAYER` in your `.env`) before placing them in the folder.

| Report | Filename pattern | Example (`TAXPAYER=gor`) |
|--------|-----------------|--------------------------|
| Movements | `<TAXPAYER>-movimentacao-YYYY*.xlsx` | `gor-movimentacao-2025-01-01_a_2025-12-31.xlsx` |
| Negotiations | `<TAXPAYER>-negociacao-YYYY*.xlsx` | `gor-negociacao-01-01-2025_a_31-12-2025.xlsx` |
| Annual consolidated | `<TAXPAYER>-relatorio-consolidado-anual-YYYY.xlsx` | `gor-relatorio-consolidado-anual-2024.xlsx` |

> After downloading, rename each file to prepend `<TAXPAYER>-` before placing it in the folder.
> The app then picks the **most recent file** matching each pattern.

### Where to download each report

1. Log in to the B3 Investor Area at [investidor.b3.com.br](https://www.investidor.b3.com.br/)
2. **Movements** → "Extratos" → "Movimentação" → "Filtrar" → select from first to last day of the desired year → "Baixar"
3. **Negotiations** → "Extratos" → "Negociação" → "Filtrar" → select from first to last day of the desired year → "Baixar"
4. **Annual consolidated** → "Relatórios" → "Relatório Consolidado" → "Selecione o período que deseja visualizar" → "Anual" <!-- codespell:ignore --> → select the desired year → Arquivo em excel → "Baixar relatório"

Place all three renamed files in `~/daily_infos/<YYYY-MM-DD>/` (today's date) before running.

---

## Running the app

```bash
make run
```

This starts PostgreSQL + pgAdmin (if not already running), applies any pending
migrations, then executes `src/main.py`. It is safe to call on every run — all
three steps are idempotent.

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
| `development-irpf_<USER>_<YYYYMMDD>_<HHMMSS>.log` | Execution log |
| `development-irpf_<USER>_<YYYYMMDD>_<HHMMSS>.json` | Import summary (rows per table) |
| `development-irpf_<USER>_<YYYYMMDD>_<HHMMSS>.txt` | **IRPF declaration report** ← copy this |

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

1. Download new B3 Excel files into `~/daily_infos/<today>/`
2. Update `inputs.yaml → declaration_rv.contributor` if anything changed
3. Run `make run`

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

**pgAdmin shows no server**
> Add the server manually: right-click "Servers" → Register → Server.
> Connection: Host `postgresql`, Port `5432`, DB `wealth_db`, User/Password from `.env`.
> (Use the Docker service name `postgresql` as the host — not `localhost` — from inside pgAdmin.)
