import sys
import os
import json
import argparse
from uuid import UUID
from datetime import datetime
from typing import Any, Type, List

# Add necessary paths for importing models
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_dir)
# Add apps/api to path so we can import app
sys.path.append(os.path.join(root_dir, "apps", "api"))

# Import SQLModel and Session
from sqlmodel import SQLModel, Session, create_engine, select
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point
import shapely.wkt as wkt

# Import models from app.models
try:
    # Manually load .env from root before importing settings to ensure they are available
    env_path = os.path.join(root_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    from app.core.config import settings
    from app.models.event import Event, PendingEvent
    from app.models.venue import Venue
except ImportError as e:
    print(f"Error importing app models: {e}")
    print("Ensure you are running this from the project root with the correct PYTHONPATH.")
    sys.exit(1)

# Engine setup
def get_engine():
    # Try to reconstruct URL from individual env vars first (more reliable for local dev)
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB", "fomo")
    
    # Base URL from settings or default
    db_url = settings.DATABASE_URL

    # If we have individual credentials, use them to ensure we're not using hardcoded defaults
    if user and password:
        # Reconstruct the URL parts while keeping the host/port from settings
        # This handles cases where settings.DATABASE_URL has the wrong password
        import re
        # Pattern to match driver://user:pass@host:port/db
        pattern = r"^(?P<driver>.*://)(?P<user>.*?):(?P<password>.*?)@(?P<host_port>.*?)/(?P<db>.*)$"
        match = re.match(pattern, db_url)
        if match:
            gd = match.groupdict()
            db_url = f"{gd['driver']}{user}:{password}@{gd['host_port']}/{db_name}"
        else:
            # Fallback if URL doesn't match standard pattern
            db_url = f"postgresql+psycopg2://{user}:{password}@localhost:5432/{db_name}"

    # Automatically map 'db' to 'localhost' if running locally on host
    if "@db:" in db_url and (os.name == "nt" or not os.path.exists("/.dockerenv")):
        db_url = db_url.replace("@db:", "@localhost:")
    
    return create_engine(db_url)

engine = get_engine()

MODELS = {
    "events": Event,
    "venues": Venue,
    "pending_events": PendingEvent,
}

SEED_DIR = os.path.join(root_dir, "infra", "seeds")

def serialize_item(item: SQLModel) -> dict[str, Any]:
    """Serializes a SQLModel item to a JSON-compatible dict."""
    # Using mode="json" handles UUID and datetime objects automatically in Pydantic v2
    data = item.model_dump(mode="json")
    
    # Force 'location' to WKT string if it exists to satisfy requirements
    if hasattr(item, "location") and item.location is not None:
        try:
            # Handle both WKB and already-converted shapes
            shape = to_shape(item.location)
            data["location"] = wkt.dumps(shape)
        except Exception:
            # If model already serialized it to dict via field_serializer, we might need to convert it back or just leave it.
            # But the prompt asked for WKT strings.
            if isinstance(data.get("location"), dict) and data["location"].get("type") == "Point":
                coords = data["location"].get("coordinates")
                if coords and len(coords) == 2:
                    data["location"] = f"POINT({coords[0]} {coords[1]})"
    
    return data

def deserialize_item(model: Type[SQLModel], data: dict[str, Any]) -> SQLModel:
    """Deserializes a JSON dict to a SQLModel item, handling PostGIS fields."""
    # Convert location from WKT or GeoJSON dict back to PostGIS element if present
    if "location" in data and data["location"]:
        if isinstance(data["location"], str):
            try:
                shape = wkt.loads(data["location"])
                data["location"] = from_shape(shape, srid=4326)
            except Exception:
                pass
        elif isinstance(data["location"], dict) and data["location"].get("type") == "Point":
            coords = data["location"].get("coordinates")
            if coords and len(coords) == 2:
                lng, lat = coords
                data["location"] = from_shape(Point(lng, lat), srid=4326)
            
    return model.model_validate(data)

def dump_table(table_name: str):
    """Dumps a table to a JSON file."""
    model = MODELS.get(table_name)
    if not model:
        print(f"Error: Unknown table {table_name}")
        return

    with Session(engine) as session:
        try:
            items = session.exec(select(model)).all()
            data = [serialize_item(item) for item in items]
            
            if not os.path.exists(SEED_DIR):
                os.makedirs(SEED_DIR, exist_ok=True)
                
            file_path = os.path.join(SEED_DIR, f"{table_name}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"Successfully dumped {len(data)} items to {file_path}")
        except Exception as e:
            print(f"Error dumping {table_name}: {e}")

def seed_table(table_name: str):
    """Seeds a table from a JSON file using upsert logic."""
    model = MODELS.get(table_name)
    if not model:
        print(f"Error: Unknown table {table_name}")
        return

    file_path = os.path.join(SEED_DIR, f"{table_name}.json")
    if not os.path.exists(file_path):
        print(f"Error: Seed file {file_path} not found")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        with Session(engine) as session:
            for item_data in data:
                item = deserialize_item(model, item_data)
                
                # SQLModel/SQLAlchemy session.merge handles upsert based on primary key
                session.merge(item)
                
            session.commit()
            print(f"Successfully seeded {len(data)} items to {table_name}")
    except Exception as e:
        print(f"Error seeding {table_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database Hydration System")
    parser.add_argument("command", choices=["dump", "seed"], help="Command to run")
    parser.add_argument("--table", choices=list(MODELS.keys()) + ["all"], default="all", help="Table to process")

    args = parser.parse_args()

    tables = list(MODELS.keys()) if args.table == "all" else [args.table]

    if args.command == "dump":
        for table in tables:
            dump_table(table)
    elif args.command == "seed":
        for table in tables:
            seed_table(table)
