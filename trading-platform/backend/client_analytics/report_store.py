from backend.client_analytics.report_models import ClientReport


class ReportStore:
    """In-memory store for generated client reports."""

    _reports: list[ClientReport] = []

    def store_report(self, report: ClientReport) -> ClientReport:
        self._reports.insert(0, report)
        self._reports = self._reports[:1000]
        return report

    def list_reports(self, limit: int = 100) -> list[ClientReport]:
        bounded_limit = max(1, min(int(limit), 1000))
        return self._reports[:bounded_limit]

    def get_latest_report(self) -> ClientReport | None:
        return self._reports[0] if self._reports else None
