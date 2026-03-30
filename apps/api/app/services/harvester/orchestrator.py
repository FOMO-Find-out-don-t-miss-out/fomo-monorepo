import asyncio
import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlmodel import Session

from app.core.config import settings
from app.db.session import engine
from app.schemas.event import IngestSummary
from app.services.harvester.cleanser import CleansingService
from app.services.harvester.ingestor import IngestionService
from app.services.harvester.location.geocoder import GeocoderService
from packages.domain.schemas.extracted_event import ExtractedEvent
from packages.domain.utils.url_utils import detect_country_from_url, get_domain_from_url

logger = logging.getLogger(__name__)


class HarvesterOrchestrator:
    @staticmethod
    async def run_pipeline(default_country: str = "GR") -> None:
        """Background task to run scraper, cleanse data using AI fallbacks, and ingest."""
        logger.info(f"Background Task: Starting pipeline (country={default_country})")

        try:
            # Resolve script path
            # apps/api/app/services/harvester/orchestrator.py
            # script is at apps/api/app/services/harvester/scraper.py
            current_file = Path(__file__)
            script_path = current_file.parent / "scraper.py"

            if not script_path.exists():
                logger.error(f"Scraper script not found at {script_path}")
                return

            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
            except TimeoutError:
                process.kill()
                logger.error("Scraper subprocess timed out")
                return

            if process.returncode != 0:
                logger.error(f"Scraper error {process.returncode}: {stderr.decode()}")
                return

            try:
                raw_scraped_data = json.loads(stdout.decode())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse scraper JSON: {e}")
                return

            logger.info(f"Scraper returned {len(raw_scraped_data)} raw items")

            cleaned_events: list[ExtractedEvent] = []
            for item in raw_scraped_data:
                source = item.get("source")
                original_link = item.get("original_link")
                country_hint = (
                    detect_country_from_url(original_link) if original_link else default_country
                )

                source_domain = get_domain_from_url(original_link)

                try:
                    if source == "schema_org":
                        extracted = await CleansingService.clean_json_ld(
                            item.get("structured_data", {}),
                            country_hint,
                            source_domain=source_domain,
                        )
                        if isinstance(extracted, list):
                            for ev in extracted:
                                ev.event_metadata["original_link"] = original_link
                                ev.country_code = country_hint
                                cleaned_events.append(ev)
                        elif extracted:
                            extracted.event_metadata["original_link"] = original_link
                            extracted.country_code = country_hint
                            cleaned_events.append(extracted)
                    elif source == "registry":
                        extracted = ExtractedEvent(
                            title=item.get("title") or "Untitled Event",
                            start_time=item.get("start_time"),
                            end_time=item.get("end_time"),
                            location_name=item.get("location_name"),
                            description=item.get("description"),
                            country_code=country_hint,
                            source_provider=source_domain,
                            ingestion_method="registry",
                            event_metadata={"original_link": original_link},
                        )
                        if (
                            extracted.lat is None or extracted.lng is None
                        ) and extracted.location_name:
                            geo_res = await GeocoderService.get_coordinates(
                                extracted.location_name,
                                country_hint,
                                search_term=extracted.location_name,
                            )
                            if geo_res:
                                extracted.lat, extracted.lng = geo_res.lat, geo_res.lng
                                extracted.confidence_score = geo_res.relevance
                                extracted.geocoding_status = geo_res.geocoding_status
                                extracted.geocoding_metadata = geo_res.geocoding_metadata
                        cleaned_events.append(extracted)
                    elif source == "llm_fallback":
                        extracted_list = await CleansingService.clean_html_fallback(
                            item.get("raw_text", ""), country_hint, source_domain=source_domain
                        )
                        for extracted in extracted_list:
                            extracted.event_metadata["original_link"] = original_link
                            extracted.country_code = country_hint
                            cleaned_events.append(extracted)
                except Exception as e:
                    logger.error(f"Error processing item from {source}: {e}")
                    continue

            logger.info(f"Cleansing: {len(cleaned_events)}/{len(raw_scraped_data)} valid")

            summary = IngestSummary(added=0, updated=0)
            if cleaned_events:
                try:
                    with Session(engine) as db:
                        summary = await IngestionService.ingest_events(db, cleaned_events)
                    logger.info(f"Ingest Result: Added={summary.added}, Updated={summary.updated}")
                except Exception as db_err:
                    logger.error(f"Database error during ingestion: {db_err}")

            if settings.N8N_WEBHOOK_URL:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            settings.N8N_WEBHOOK_URL,
                            json={
                                "status": "completed",
                                "summary": {
                                    "raw_count": len(raw_scraped_data),
                                    "cleaned_count": len(cleaned_events),
                                    "db_added": summary.added,
                                    "db_updated": summary.updated,
                                },
                                "default_country": default_country,
                                "timestamp": datetime.now(UTC).isoformat(),
                            },
                            timeout=10.0,
                        )
                except Exception as web_err:
                    logger.warning(f"Failed to notify n8n: {web_err}")

        except Exception:
            logger.error(f"Fatal exception in background task:\n{traceback.format_exc()}")
