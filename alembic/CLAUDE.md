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
