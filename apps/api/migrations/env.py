from logging.config import fileConfig

from alembic import context
from app.core.config import settings
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Import all models to ensure they are registered with SQLModel.metadata
try:
    from packages.domain.models import (
        Event,  # noqa: F401
        HypeLedger,  # noqa: F401
        Organizer,  # noqa: F401
        OrganizerFollower,  # noqa: F401
        PendingEvent,  # noqa: F401
        Place,  # noqa: F401
        Profile,  # noqa: F401
        User,  # noqa: F401
        UserConnection,  # noqa: F401
        WalletAccount,  # noqa: F401
        WalletTransaction,  # noqa: F401
    )
except ImportError:
    # Handle the case where the environment is not set up correctly for imports
    pass

# this is the Alembic Config object, which provides access to the values within the .ini file
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def include_object(obj: object, name: str, type_: str, reflected: bool, compare_to: object) -> bool:
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
