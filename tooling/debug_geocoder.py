import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add apps/api to sys.path to resolve 'app'
sys.path.append(str(Path(__file__).parent.parent / "apps" / "api"))
# Add root to resolve 'packages'
sys.path.append(str(Path(__file__).parent.parent))

# Mock engine before importing anything that uses it
with patch("sqlmodel.create_engine"):
    from app.core.config import settings
    from app.services.harvester.location.geocoder import GeocoderService


async def debug_geocoder():
    # Load env from apps/api/.env
    from dotenv import load_dotenv

    load_dotenv("apps/api/.env")

    # Manually update settings if not loaded correctly
    settings.MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")

    print(f"Token present: {bool(settings.MAPBOX_ACCESS_TOKEN)}")

    test_cases = [
        {"name": "Floyd", "addr": "Πειραιώς 117", "city": "Αθήνα"},
        {
            "name": "ROHAS ATHENS LIVE STAGE",
            "addr": "Χατζηγιάννη Μέξη 6, Αθήνα 115 28",
            "city": "Αθήνα",
        },
        {
            "name": "Bolivar Beach Club",
            "addr": "Λ. Ποσειδώνος, Ακτή του Ήλιου Άλιμος",
            "city": "Άλιμος",
        },
    ]

    # Patch Session and VenueRepository to bypass DB
    with (
        patch("app.services.harvester.location.geocoder.Session"),
        patch("app.services.harvester.location.geocoder.VenueRepository") as mock_repo_class,
    ):
        # Make get_by_name return None to force Mapbox call
        mock_repo_class.return_value.get_by_name.return_value = None

        for case in test_cases:
            print(f"\n--- Testing: {case['name']} ---")
            try:
                res = await GeocoderService.get_coordinates(
                    case["name"], "GR", city_hint=case["city"], source_address=case["addr"]
                )
                if res:
                    print(f"Status: {res.geocoding_status}")
                    print(f"Coords: {res.lat}, {res.lng}")
                    print(f"Relevance: {res.relevance}")
                    print(f"Full Addr: {res.full_address}")
                    print(f"Metadata: {res.geocoding_metadata}")
                else:
                    print("Result: None (Failed)")
            except Exception as e:
                print(f"Error: {e}")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_geocoder())
