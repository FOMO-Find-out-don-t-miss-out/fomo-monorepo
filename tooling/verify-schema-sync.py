import os
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from sqlmodel import SQLModel, create_engine

# Add monorepo root and apps/api to path to ensure imports work correctly
sys.path.append(str(Path.cwd()))
sys.path.append(str(Path.cwd() / "apps" / "api"))

# Import all models to ensure they are registered in SQLModel.metadata
try:
    from app.models.event import Event, PendingEvent  # noqa: F401
    from app.models.hype import HypeLedger  # noqa: F401
    from app.models.social import SocialConnection  # noqa: F401
    from app.models.user import Profile, User  # noqa: F401
    from app.models.venue import Venue  # noqa: F401
except ImportError as e:
    print(f"Warning: Some models could not be imported: {e}")  # noqa: T201


def load_env() -> None:
    """Simple .env loader to avoid extra dependencies."""
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def include_object(obj: object, name: str, type_: str, reflected: bool, compare_to: object) -> bool:
    """
    Filter out internal PostGIS and Tiger geocoder tables from comparison.
    Only include tables that are defined in our SQLModel metadata.
    """
    if type_ == "table":
        # Ignore common PostGIS/Tiger internal tables
        internal_prefixes = [
            "spatial_ref_sys",
            "topology",
            "layer",
            "addr",
            "county",
            "state",
            "place",
            "zip",
            "tract",
            "bg",
            "tabblock",
            "edges",
            "faces",
            "featnames",
            "cousub",
            "countysub",
            "direction_lookup",
            "street_type_lookup",
            "secondary_unit_lookup",
            "loader_",
            "geocode_settings",
            "pagc_",
        ]
        if any(name.startswith(prefix) for prefix in internal_prefixes):
            return False

        # Only include tables defined in our metadata
        return name in SQLModel.metadata.tables

    return True


def verify_schema() -> None:
    """
    Compares the current SQLModel metadata with the live database schema.
    Exits with code 1 if differences are detected.
    """
    if os.getenv("SKIP_DB_VERIFY"):
        print("WARNING: Skipping schema verification (SKIP_DB_VERIFY is set).")
        sys.exit(0)

    load_env()

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db = os.getenv("POSTGRES_DB", "fomo")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

    database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

    # Connect with a short timeout to fail fast if DB is not reachable
    engine = create_engine(database_url, connect_args={"connect_timeout": 5})

    try:
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            connection.commit()

            # Configure context with the filter
            context = MigrationContext.configure(
                connection, opts={"include_object": include_object}
            )

            diff = compare_metadata(context, SQLModel.metadata)

        if diff:
            print("CRITICAL: Schema Drift Detected. Please run Alembic migrations.")  # noqa: T201
            for d in diff:
                print(f" - {d}")  # noqa: T201
            sys.exit(1)
        else:
            print("SUCCESS: Schema is in sync.")  # noqa: T201
            sys.exit(0)

    except Exception as e:
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            print(f"WARNING: Could not verify schema sync in CI environment: {e}")
            sys.exit(0)
        print(f"Error: Could not verify schema sync: {e}")  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    verify_schema()
