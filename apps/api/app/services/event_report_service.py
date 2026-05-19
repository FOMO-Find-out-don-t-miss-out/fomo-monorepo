from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from packages.domain.models import Event, EventReport
from packages.domain.models.event import EventStatus, EventVisibility
from packages.domain.models.event_report import (
    GpsValidationStatus,
    ReportResolution,
    ReportStatus,
)


class EventReportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_public_event(self, event_id: UUID) -> Event | None:
        statement = (
            select(Event)
            .where(Event.id == event_id)
            .where(Event.status == EventStatus.live)
            .where(Event.visibility == EventVisibility.public)
            .where(Event.removed_at.is_(None))
        )
        return self.session.exec(statement).first()

    def submit_report(
        self,
        *,
        reporter_user_id: UUID,
        event_id: UUID,
        reason: str,
        details: str | None = None,
        gps_validation_status: GpsValidationStatus = GpsValidationStatus.not_checked,
    ) -> EventReport | None:
        if self._get_public_event(event_id) is None:
            return None

        statement = select(EventReport).where(
            EventReport.event_id == event_id,
            EventReport.reporter_user_id == reporter_user_id,
            EventReport.reason == reason,
        )
        existing = self.session.exec(statement).first()
        if existing:
            return existing

        report = EventReport(
            event_id=event_id,
            reporter_user_id=reporter_user_id,
            reason=reason,
            details=details,
            gps_validation_status=gps_validation_status,
            status=ReportStatus.open,
        )
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def list_open_reports(self) -> list[EventReport]:
        return self.list_reports_by_status(ReportStatus.open)

    def list_reports_for_event(self, *, event_id: UUID) -> list[EventReport]:
        statement = (
            select(EventReport)
            .where(EventReport.event_id == event_id)
            .order_by(EventReport.created_at)
        )
        return list(self.session.exec(statement).all())

    def list_reports_by_status(self, status: ReportStatus) -> list[EventReport]:
        statement = (
            select(EventReport)
            .where(EventReport.status == status)
            .order_by(EventReport.created_at)
        )
        return list(self.session.exec(statement).all())

    def resolve_report(
        self,
        *,
        report_id: UUID,
        resolution: ReportResolution,
        reviewed_by: UUID | None = None,
        review_status: ReportStatus = ReportStatus.resolved,
    ) -> EventReport | None:
        report = self.session.get(EventReport, report_id)
        if report is None:
            return None

        report.status = review_status
        report.resolution = resolution
        report.reviewed_by = reviewed_by
        report.reviewed_at = datetime.now(UTC)
        report.updated_at = datetime.now(UTC)
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def dismiss_report(
        self,
        *,
        report_id: UUID,
        reviewed_by: UUID | None = None,
    ) -> EventReport | None:
        return self.resolve_report(
            report_id=report_id,
            resolution=ReportResolution.report_rejected,
            reviewed_by=reviewed_by,
            review_status=ReportStatus.dismissed,
        )
