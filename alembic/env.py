from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool

from sublease_matcher.api.adapters.sqlalchemy import models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

env_url_override = os.getenv("SM_DATABASE_URL")
if env_url_override:
    config.set_main_option("sqlalchemy.url", env_url_override)

resolved_url = config.get_main_option("sqlalchemy.url")
if not resolved_url:
    raise RuntimeError("sqlalchemy.url must be configured (set SM_DATABASE_URL)")
print("Alembic URL ->", create_engine(resolved_url).url)

target_metadata = models.Base.metadata


def get_database_url() -> str:
    database_url = config.get_main_option("sqlalchemy.url")
    if not database_url:
        raise RuntimeError("sqlalchemy.url must be configured (set SM_DATABASE_URL)")
    return database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=get_database_url(),
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
