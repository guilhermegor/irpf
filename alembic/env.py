"""Alembic migration environment — loads metadata from SQLAlchemy Base."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

import chassis.db_schema.infrastructure.models  # noqa: F401 — registers all ORM models
from chassis.db_schema.infrastructure.base import Base


load_dotenv()

_cfg = context.config
if _cfg.config_file_name is not None:
    fileConfig(_cfg.config_file_name)

_TAXPAYER = os.environ["TAXPAYER"]
_DB_DSN = (
    f"postgresql+psycopg://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
    f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    f"?options=-c%20search_path%3D{_TAXPAYER}"
)
_cfg.set_main_option("sqlalchemy.url", _DB_DSN.replace("%", "%%"))

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
