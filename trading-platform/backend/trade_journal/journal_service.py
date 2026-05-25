from backend.trade_journal.exposure_monitor import ExposureMonitor
from backend.trade_journal.journal_logger import JournalLogger
from backend.trade_journal.journal_models import JournalEntry, RiskAlert, RiskAnalytics, SessionPerformance, SymbolPerformance
from backend.trade_journal.journal_storage import JournalStorage
from backend.trade_journal.performance_tracker import PerformanceTracker
from backend.trade_journal.risk_alerts import RiskAlertService
from backend.trade_journal.risk_analytics import RiskAnalyticsService


class JournalService:
    """Application facade for analytics-only journal records and risk observations."""

    def __init__(
        self,
        storage: JournalStorage | None = None,
        logger: JournalLogger | None = None,
    ) -> None:
        self.storage = storage or JournalStorage()
        self.logger = logger or JournalLogger()
        self.performance = PerformanceTracker()
        self.exposure_monitor = ExposureMonitor()
        self.risk_analytics = RiskAnalyticsService()
        self.alerts = RiskAlertService()
        self._volatile_entries: list[JournalEntry] = []

    def add_entry(self, entry: JournalEntry) -> JournalEntry:
        validated = JournalEntry.model_validate(entry.model_dump())
        persisted = self.storage.save_entry(validated)
        if not persisted:
            self._volatile_entries.insert(0, validated)
        self.logger.log_event(
            "SIMULATED_JOURNAL_ENTRY",
            f"Recorded simulated journal outcome for {validated.symbol}.",
            {"journal_id": validated.journal_id, "persisted": persisted},
        )
        self._persist_generated_alerts()
        return validated

    def get_recent_entries(self, limit: int = 50) -> list[JournalEntry]:
        stored = self.storage.get_recent_entries(limit)
        merged = {entry.journal_id: entry for entry in self._volatile_entries + stored}
        return sorted(merged.values(), key=lambda item: item.timestamp, reverse=True)[:limit]

    def get_symbol_performance(self, symbol: str) -> SymbolPerformance:
        normalized = symbol.strip().upper()
        entries = [entry for entry in self._all_entries() if entry.symbol == normalized]
        return self.performance.symbol_performance(normalized, entries)

    def get_session_performance(self, session: str) -> SessionPerformance:
        normalized = session.strip().upper()
        entries = [entry for entry in self._all_entries() if entry.session_name == normalized]
        return self.performance.session_performance(normalized, entries)

    def get_overall_performance(self) -> dict:
        entries = self._all_entries()
        return {
            **self.performance.calculate(entries),
            "strategy_effectiveness": self.performance.strategy_effectiveness(entries),
            "analytics_mode": "SIMULATION_ANALYTICS_ONLY",
        }

    def get_risk_analytics(self) -> RiskAnalytics:
        return self.risk_analytics.calculate_risk_analytics(self._all_entries())

    def get_exposure(self):
        return self.exposure_monitor.calculate_exposure(self._all_entries())

    def get_risk_alerts(self) -> list[RiskAlert]:
        current = self._generate_alerts()
        return current

    def _all_entries(self) -> list[JournalEntry]:
        return self.get_recent_entries(500)

    def _generate_alerts(self) -> list[RiskAlert]:
        entries = self._all_entries()
        analytics = self.risk_analytics.calculate_risk_analytics(entries)
        exposure = self.exposure_monitor.calculate_exposure(entries)
        performance = self.performance.calculate(entries)
        return self.alerts.generate_alerts(analytics, exposure, performance)

    def _persist_generated_alerts(self) -> None:
        for alert in self._generate_alerts():
            self.storage.save_alert(alert)
