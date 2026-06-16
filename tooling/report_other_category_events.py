"""
FOMO-166: dry-run report of likely category fixes for historical events
currently stored with category="Other".

This script is READ-ONLY. It re-runs the domain EventClassifier against each
Other-categorized event's existing title/description/metadata and prints a
report of events where the classifier would now produce a different
(non-Other) category, so a human can decide on a follow-up backfill. It does
not write to the database.

Usage:
    uv run python tooling/report_other_category_events.py [--limit N] [--json]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "apps" / "api"))

env_path = root_dir / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from app.core.config import settings  # noqa: E402
from sqlmodel import Engine, Session, create_engine, select  # noqa: E402

from packages.domain.models.event import Event  # noqa: E402
from packages.domain.models.pending_event import PendingEvent  # noqa: E402
from packages.domain.services.event_classifier import EventClassifier  # noqa: E402


def get_engine() -> Engine:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB", "fomo")

    db_url = settings.DATABASE_URL
    if user and password:
        pattern = (
            r"^(?P<driver>.*://)(?P<user>.*?):(?P<password>.*?)@(?P<host_port>.*?)/(?P<db>.*)$"
        )
        match = re.match(pattern, db_url)
        if match:
            gd = match.groupdict()
            db_url = f"{gd['driver']}{user}:{password}@{gd['host_port']}/{db_name}"

    if "@db:" in db_url and (os.name == "nt" or not Path("/.dockerenv").exists()):
        db_url = db_url.replace("@db:", "@localhost:")

    return create_engine(db_url)


def build_report(session: Session, limit: int | None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for model, label in ((Event, "events"), (PendingEvent, "pending_events")):
        query = select(model).where(model.category == "Other")
        if limit:
            query = query.limit(limit)

        for row in session.exec(query):
            suggested_category, suggested_sub_category, _tags = EventClassifier.classify(
                row.title, row.description, row.event_metadata or {}
            )
            if suggested_category != "Other":
                rows.append(
                    {
                        "table": label,
                        "id": str(row.id),
                        "title": row.title,
                        "current_category": row.category,
                        "suggested_category": suggested_category,
                        "suggested_sub_category": suggested_sub_category,
                    }
                )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="Max rows to scan per table (default: all)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON instead of a table"
    )
    args = parser.parse_args()

    engine = get_engine()
    with Session(engine) as session:
        rows = build_report(session, args.limit)

    if args.json:
        print(json.dumps(rows, indent=2))  # noqa: T201
        return

    if not rows:
        print("No likely re-categorizations found among Other-categorized events.")  # noqa: T201
        return

    print(f"{len(rows)} event(s) with a likely category fix (dry run, no writes made):\n")  # noqa: T201
    for row in rows:
        print(  # noqa: T201
            f"[{row['table']}] {row['id']} \"{row['title']}\" "
            f"Other -> {row['suggested_category']}"
            + (f" / {row['suggested_sub_category']}" if row["suggested_sub_category"] else "")
        )

    print(  # noqa: T201
        "\nThis report does not modify the database. Review and apply fixes "
        "manually or via a separate, explicitly-reviewed backfill task."
    )


if __name__ == "__main__":
    main()
