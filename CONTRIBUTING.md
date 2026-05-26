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

Alembic `-m` messages become the filename suffix — keep them readable as a path segment.

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

## Alembic file naming — date+time prefix

`alembic.ini` is configured with a `file_template` that prepends `YYYYMMDD_HHMM` to every
generated file:

```
20260525_1454_7b98ce6f574f_create_b3_tables.py
```

This makes chronological order visible at a glance in any file browser or `ls` listing.
Alembic's actual migration order is determined by the `down_revision` chain inside each
file — the prefix is informational only and does not affect execution order.

Example full pairing:

```bash
alembic revision -m "create_irpf_views"
# → generates: 20260525_1454_8ef63ada69a6_create_irpf_views.py

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
