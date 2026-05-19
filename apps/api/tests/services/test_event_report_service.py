from datetime import UTC, datetime
from uuid import uuid4

from app.services.event_report_service import EventReportService
from sqlmodel import Session, select

from packages.domain.models import Event, EventReport, EventStatus, EventVisibility, User
from packages.domain.models.event_report import GpsValidationStatus, ReportResolution, ReportStatus


def create_user(session: Session, email: str = "reporter@example.com") -> User:
    user = User(external_id=str(uuid4()), email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_event(
    session: Session,
    title: str,
    *,
    status: EventStatus = EventStatus.live,
    visibility: EventVisibility = EventVisibility.public,
) -> Event:
    event = Event(
        title=title,
        location="POINT(23.7275 37.9838)",
        start_time=datetime(2026, 6, 1, 20, 0, tzinfo=UTC),
        category="Music",
        status=status,
        visibility=visibility,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def report_count(session: Session) -> int:
    return len(session.exec(select(EventReport)).all())


# --- submit_report ---


def test_submit_report_creates_report_for_public_event(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Live Event")
    service = EventReportService(session)

    report = service.submit_report(
        reporter_user_id=user.id,
        event_id=event.id,
        reason="spam",
    )

    assert report is not None
    assert report.event_id == event.id
    assert report.reporter_user_id == user.id
    assert report.reason == "spam"
    assert report.status == ReportStatus.open
    assert report.resolution is None
    assert report.reviewed_by is None
    assert report.reviewed_at is None


def test_submit_report_duplicate_is_idempotent(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Idempotent Event")
    service = EventReportService(session)

    first = service.submit_report(
        reporter_user_id=user.id,
        event_id=event.id,
        reason="misleading",
    )
    second = service.submit_report(
        reporter_user_id=user.id,
        event_id=event.id,
        reason="misleading",
    )

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert report_count(session) == 1


def test_submit_report_different_reasons_create_separate_reports(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Multi-Reason Event")
    service = EventReportService(session)

    r1 = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")
    r2 = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="fake")

    assert r1 is not None
    assert r2 is not None
    assert r1.id != r2.id
    assert report_count(session) == 2


def test_submit_report_different_users_same_event_and_reason(session: Session) -> None:
    user_a = create_user(session, "a@example.com")
    user_b = create_user(session, "b@example.com")
    event = create_event(session, "Shared Report Event")
    service = EventReportService(session)

    r1 = service.submit_report(reporter_user_id=user_a.id, event_id=event.id, reason="spam")
    r2 = service.submit_report(reporter_user_id=user_b.id, event_id=event.id, reason="spam")

    assert r1 is not None
    assert r2 is not None
    assert r1.id != r2.id
    assert report_count(session) == 2


def test_submit_report_returns_none_for_hidden_event(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Hidden Event", visibility=EventVisibility.hidden)
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")

    assert report is None
    assert report_count(session) == 0


def test_submit_report_returns_none_for_shadow_hidden_event(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Shadow Event", visibility=EventVisibility.shadow_hidden)
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")

    assert report is None


def test_submit_report_returns_none_for_restricted_event(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Restricted Event", visibility=EventVisibility.restricted)
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")

    assert report is None


def test_submit_report_returns_none_for_removed_event(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Removed Event", status=EventStatus.removed)
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")

    assert report is None
    assert report_count(session) == 0


def test_submit_report_returns_none_for_under_investigation_event(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Investigated Event", status=EventStatus.under_investigation)
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")

    assert report is None


def test_submit_report_defaults_gps_validation_status_to_not_checked(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "GPS Default Event")
    service = EventReportService(session)

    report = service.submit_report(
        reporter_user_id=user.id,
        event_id=event.id,
        reason="wrong_location",
    )

    assert report is not None
    assert report.gps_validation_status == GpsValidationStatus.not_checked


def test_submit_report_accepts_explicit_gps_validation_status(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "GPS Explicit Event")
    service = EventReportService(session)

    report = service.submit_report(
        reporter_user_id=user.id,
        event_id=event.id,
        reason="wrong_location",
        gps_validation_status=GpsValidationStatus.invalid,
    )

    assert report is not None
    assert report.gps_validation_status == GpsValidationStatus.invalid


def test_submit_report_persists_details(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Details Event")
    service = EventReportService(session)

    report = service.submit_report(
        reporter_user_id=user.id,
        event_id=event.id,
        reason="spam",
        details="This event is clearly spam with fake tickets.",
    )

    assert report is not None
    assert report.details == "This event is clearly spam with fake tickets."


# --- list_reports ---


def test_list_reports_for_event_returns_only_that_events_reports(session: Session) -> None:
    user = create_user(session)
    event_a = create_event(session, "Event A")
    event_b = create_event(session, "Event B")
    service = EventReportService(session)

    service.submit_report(reporter_user_id=user.id, event_id=event_a.id, reason="spam")
    service.submit_report(reporter_user_id=user.id, event_id=event_b.id, reason="spam")

    reports = service.list_reports_for_event(event_id=event_a.id)

    assert len(reports) == 1
    assert reports[0].event_id == event_a.id


def test_list_open_reports_excludes_resolved(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Open Reports Event")
    service = EventReportService(session)

    r1 = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")
    r2 = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="fake")
    assert r1 is not None and r2 is not None

    service.resolve_report(report_id=r2.id, resolution=ReportResolution.event_kept)

    open_reports = service.list_open_reports()

    assert len(open_reports) == 1
    assert open_reports[0].id == r1.id


def test_list_reports_by_status_filters_correctly(session: Session) -> None:
    user = create_user(session)
    event = create_event(session, "Status Reports Event")
    service = EventReportService(session)

    r1 = service.submit_report(reporter_user_id=user.id, event_id=event.id, reason="spam")
    assert r1 is not None
    service.resolve_report(report_id=r1.id, resolution=ReportResolution.event_kept)

    resolved = service.list_reports_by_status(ReportStatus.resolved)
    open_reports = service.list_reports_by_status(ReportStatus.open)

    assert len(resolved) == 1
    assert len(open_reports) == 0


# --- resolve / dismiss ---


def test_resolve_report_sets_all_fields(session: Session) -> None:
    reviewer = create_user(session, "reviewer@example.com")
    reporter = create_user(session, "reporter2@example.com")
    event = create_event(session, "Resolve Event")
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=reporter.id, event_id=event.id, reason="spam")
    assert report is not None

    resolved = service.resolve_report(
        report_id=report.id,
        resolution=ReportResolution.event_kept,
        reviewed_by=reviewer.id,
    )

    assert resolved is not None
    assert resolved.status == ReportStatus.resolved
    assert resolved.resolution == ReportResolution.event_kept
    assert resolved.reviewed_by == reviewer.id
    assert resolved.reviewed_at is not None


def test_resolve_report_with_custom_review_status(session: Session) -> None:
    reporter = create_user(session)
    event = create_event(session, "Under Review Event")
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=reporter.id, event_id=event.id, reason="spam")
    assert report is not None

    updated = service.resolve_report(
        report_id=report.id,
        resolution=ReportResolution.needs_monitoring,
        review_status=ReportStatus.under_review,
    )

    assert updated is not None
    assert updated.status == ReportStatus.under_review
    assert updated.resolution == ReportResolution.needs_monitoring


def test_resolve_nonexistent_report_returns_none(session: Session) -> None:
    service = EventReportService(session)

    result = service.resolve_report(
        report_id=uuid4(),
        resolution=ReportResolution.event_kept,
    )

    assert result is None


def test_dismiss_report_sets_dismissed_status_and_rejected_resolution(session: Session) -> None:
    reviewer = create_user(session, "dismisser@example.com")
    reporter = create_user(session, "dismissed_reporter@example.com")
    event = create_event(session, "Dismiss Event")
    service = EventReportService(session)

    report = service.submit_report(reporter_user_id=reporter.id, event_id=event.id, reason="spam")
    assert report is not None

    dismissed = service.dismiss_report(report_id=report.id, reviewed_by=reviewer.id)

    assert dismissed is not None
    assert dismissed.status == ReportStatus.dismissed
    assert dismissed.resolution == ReportResolution.report_rejected
    assert dismissed.reviewed_by == reviewer.id
    assert dismissed.reviewed_at is not None


def test_dismiss_nonexistent_report_returns_none(session: Session) -> None:
    service = EventReportService(session)

    result = service.dismiss_report(report_id=uuid4())

    assert result is None
