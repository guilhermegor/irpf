"""Alembic migration environment — loads metadata from SQLAlchemy Base."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL

import chassis.db_schema.infrastructure.models  # noqa: F401 — registers all ORM models
from chassis.db_schema.infrastructure.base import Base


# override=True ensures Make's variable-expanded env values are replaced by the
# raw values from .env (Make treats $ and # in .env as variable refs / comments).
load_dotenv(override=True)

_cfg = context.config
if _cfg.config_file_name is not None:
    fileConfig(_cfg.config_file_name)

_TAXPAYER = os.environ["TAXPAYER"]
_DB_URL = URL.create(
    "postgresql+psycopg",
    username=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]),
    database=os.environ["DB_NAME"],
    query={"options": f"-c search_path={_TAXPAYER}"},
)
# ConfigParser uses % for interpolation — escape every literal % in the URL string.
_cfg.set_main_option("sqlalchemy.url", _DB_URL.render_as_string(hide_password=False).replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script without DB connection)."""
    context.configure(
        url=_DB_URL,
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
