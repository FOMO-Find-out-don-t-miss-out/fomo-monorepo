import pytest
from app.services.harvester.cleanser import ExtractedEvent
from app.services.harvester.ingestion_service import IngestionService
from sqlmodel import Session


@pytest.mark.asyncio
async def test_ingest_junk_ai_category(session: Session) -> None:
    event = ExtractedEvent(title="Junk Event", start_time="2026-01-01T00:00:00Z", category="Junk")
    summary = await IngestionService.ingest_events(session, [event])
    assert summary.added == 0
    assert summary.updated == 0


@pytest.mark.asyncio
async def test_ingest_junk_title_keyword(session: Session) -> None:
    event = ExtractedEvent(
        title="Great Offers", start_time="2026-01-01T00:00:00Z", category="Other"
    )
    summary = await IngestionService.ingest_events(session, [event])
    assert summary.added == 0
    assert summary.updated == 0


@pytest.mark.asyncio
async def test_ingest_not_junk_long_title(session: Session) -> None:
    # Title contains junk keyword but is long enough to maybe not be junk
    event = ExtractedEvent(
        title="Long title" * 20,
        start_time="2026-01-01T00:00:00Z",
        category="Other",
    )
    summary = await IngestionService.ingest_events(session, [event])
    assert summary.added == 1
