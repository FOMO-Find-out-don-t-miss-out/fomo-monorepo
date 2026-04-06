import asyncio
import json
import logging
import os
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
    async def run_pipeline(
        default_country: str = "GR",
        target_url: str = "https://www.more.com/gr-el/tickets/music/",
        limit: int = 60,
    ) -> None:
        """Background task to run scraper, cleanse data using AI fallbacks, and ingest."""
        logger.info(f"Background Task: Starting pipeline (url={target_url}, limit={limit})")

        try:
            # Resolve script path
            current_file = Path(__file__)
            script_path = current_file.parent / "scraper.py"

            if not script_path.exists():
                logger.error(f"Scraper script not found at {script_path}")
                return

            # Prepare environment for subprocess
            env = os.environ.copy()
            # Ensure PYTHONPATH includes monorepo root and apps/api
            # Path(__file__) is apps/api/app/services/harvester/orchestrator.py
            current_path = Path(__file__).resolve()
            api_dir = str(current_path.parents[3])  # apps/api/
            root_dir = str(current_path.parents[5])  # monorepo root /

            existing_pythonpath = env.get("PYTHONPATH", "")
            if existing_pythonpath:
                env["PYTHONPATH"] = (
                    f"{api_dir}{os.pathsep}{root_dir}{os.pathsep}{existing_pythonpath}"
                )
            else:
                env["PYTHONPATH"] = f"{api_dir}{os.pathsep}{root_dir}"

            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                target_url,
                "--limit",
                str(limit),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
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
                original_link = item.get("original_link")
                source = item.get("source")
                ingestion_method = item.get("ingestion_method") or source
                source_provider = item.get("source_provider") or get_domain_from_url(original_link)

                country_hint = (
                    detect_country_from_url(original_link) if original_link else default_country
                )

                try:
                    if ingestion_method in ["schema_org", "json_ld"]:
                        extracted = await CleansingService.clean_json_ld(
                            item.get("structured_data", {}),
                            country_hint,
                            source_domain=source_provider,
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
                    elif ingestion_method == "registry":
                        extracted = ExtractedEvent(
                            title=item.get("title") or "Untitled Event",
                            start_time=item.get("start_time"),
                            end_time=item.get("end_time"),
                            location_name=item.get("location_name"),
                            description=item.get("description"),
                            country_code=country_hint,
                            source_provider=source_provider,
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
                    elif ingestion_method in ["llm_fallback", "html_fallback"]:
                        extracted_list = await CleansingService.clean_html_fallback(
                            item.get("raw_text", ""), country_hint, source_domain=source_provider
                        )
                        for extracted in extracted_list:
                            extracted.event_metadata["original_link"] = original_link
                            extracted.country_code = country_hint
                            cleaned_events.append(extracted)
                except Exception as e:
                    logger.error(f"Error processing {source_provider} ({ingestion_method}): {e}")
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
