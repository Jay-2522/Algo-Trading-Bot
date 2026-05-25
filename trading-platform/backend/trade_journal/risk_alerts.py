from backend.trade_journal.journal_models import ExposureStatus, RiskAlert, RiskAnalytics


class RiskAlertService:
    """Produce auditable alert objects from analytics thresholds."""

    def generate_alerts(
        self,
        analytics: RiskAnalytics,
        exposure: ExposureStatus,
        performance: dict,
    ) -> list[RiskAlert]:
        alerts: list[RiskAlert] = []
        if analytics.daily_drawdown_percent >= 5.0:
            alerts.append(self._alert("CRITICAL", "DRAWDOWN", "High simulated daily drawdown detected."))
        elif analytics.daily_drawdown_percent >= 3.0:
            alerts.append(self._alert("WARNING", "DRAWDOWN", "Simulated daily drawdown is elevated."))
        if analytics.consecutive_losses >= 3:
            severity = "CRITICAL" if analytics.consecutive_losses > 3 else "WARNING"
            alerts.append(self._alert(severity, "LOSS_STREAK", "Consecutive simulated losses require review."))
        if any("concentrated in the" in message for message in analytics.risk_alerts):
            alerts.append(
                self._alert("WARNING", "SESSION_CONCENTRATION", "Simulated risk is concentrated in one session.")
            )
        if exposure.total_exposure_percent >= 2.0:
            alerts.append(self._alert("CRITICAL", "OVEREXPOSURE", "Simulated open exposure exceeds threshold."))
        elif exposure.exposure_warning:
            alerts.append(self._alert("WARNING", "CONCENTRATION", exposure.exposure_warning))
        if performance.get("total_trades", 0) >= 5 and performance.get("win_rate", 0.0) < 35.0:
            alerts.append(self._alert("WARNING", "LOW_WIN_RATE", "Strategy win rate is below review threshold."))
        if exposure.total_exposure_percent >= 3.0:
            alerts.append(
                self._alert("CRITICAL", "VOLATILITY_EXPOSURE", "Abnormal volatility exposure proxy detected.")
            )
        if not alerts:
            alerts.append(self._alert("INFO", "RISK_STATUS", "No simulated risk thresholds breached."))
        return alerts

    def _alert(self, severity: str, category: str, message: str) -> RiskAlert:
        return RiskAlert(severity=severity, category=category, message=message)
