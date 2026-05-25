from datetime import datetime, timezone

from backend.trade_journal.drawdown_tracker import DrawdownTracker
from backend.trade_journal.exposure_monitor import ExposureMonitor
from backend.trade_journal.journal_models import JournalEntry, RiskAnalytics


class RiskAnalyticsService:
    """Aggregate simulated realized loss and open risk concentration."""

    def __init__(
        self,
        initial_balance: float = 10000.0,
        max_daily_drawdown_percent: float = 5.0,
        max_consecutive_losses: int = 3,
        max_exposure_percent: float = 2.0,
    ) -> None:
        self.initial_balance = initial_balance
        self.max_daily_drawdown_percent = max_daily_drawdown_percent
        self.max_consecutive_losses = max_consecutive_losses
        self.max_exposure_percent = max_exposure_percent
        self.exposure_monitor = ExposureMonitor(max_exposure_percent)

    def calculate_risk_analytics(self, entries: list[JournalEntry]) -> RiskAnalytics:
        today = datetime.now(timezone.utc).date()
        daily_entries = [
            entry for entry in sorted(entries, key=lambda item: item.timestamp)
            if entry.timestamp.date() == today and entry.outcome != "OPEN"
        ]
        tracker = DrawdownTracker(self.initial_balance)
        for entry in daily_entries:
            tracker.apply_pnl(entry.pnl)
        exposure = self.exposure_monitor.calculate_exposure(entries)
        consecutive, maximum = self._loss_streaks(entries)
        metrics = {
            "daily_drawdown_percent": tracker.get_drawdown_status()["current_drawdown_percent"],
            "current_exposure_percent": exposure.total_exposure_percent,
            "consecutive_losses": consecutive,
            "max_consecutive_losses": maximum,
        }
        alerts = self.check_risk_thresholds(metrics)
        concentration_alert = self._session_concentration_alert(entries)
        if concentration_alert:
            alerts.append(concentration_alert)
        return RiskAnalytics(
            **metrics,
            active_risk_level=self.get_risk_level(metrics),
            risk_alerts=alerts,
        )

    def get_risk_level(self, metrics: dict) -> str:
        drawdown = metrics["daily_drawdown_percent"]
        exposure = metrics["current_exposure_percent"]
        losses = metrics["consecutive_losses"]
        if (
            drawdown >= self.max_daily_drawdown_percent
            or exposure >= self.max_exposure_percent * 1.5
            or losses > self.max_consecutive_losses
        ):
            return "CRITICAL"
        if (
            drawdown >= self.max_daily_drawdown_percent * 0.75
            or exposure >= self.max_exposure_percent
            or losses >= self.max_consecutive_losses
        ):
            return "HIGH"
        if drawdown > 0 or exposure > 0 or losses > 0:
            return "MEDIUM"
        return "LOW"

    def check_risk_thresholds(self, metrics: dict) -> list[str]:
        alerts = []
        if metrics["daily_drawdown_percent"] >= self.max_daily_drawdown_percent:
            alerts.append("Daily simulated drawdown threshold breached.")
        if metrics["current_exposure_percent"] >= self.max_exposure_percent:
            alerts.append("Simulated open exposure threshold breached.")
        if metrics["consecutive_losses"] >= self.max_consecutive_losses:
            alerts.append("Consecutive simulated loss threshold reached.")
        return alerts

    def _session_concentration_alert(self, entries: list[JournalEntry]) -> str | None:
        risk_entries = [entry for entry in entries if entry.outcome in {"OPEN", "LOSS"}]
        if len(risk_entries) < 3:
            return None
        session_counts: dict[str, int] = {}
        for entry in risk_entries:
            session_counts[entry.session_name] = session_counts.get(entry.session_name, 0) + 1
        session, count = max(session_counts.items(), key=lambda item: item[1])
        if count / len(risk_entries) >= 0.75:
            return f"Simulated risk is concentrated in the {session} session."
        return None

    def _loss_streaks(self, entries: list[JournalEntry]) -> tuple[int, int]:
        current = maximum = 0
        for entry in sorted(entries, key=lambda item: item.timestamp):
            if entry.outcome == "LOSS":
                current += 1
                maximum = max(maximum, current)
            elif entry.outcome != "OPEN":
                current = 0
        return current, maximum
