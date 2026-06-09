from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from backend.analytics.performance_validation_service import PerformanceValidationService
from backend.analytics.strategy_health_monitor_service import StrategyHealthMonitorService
from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService


class RiskAlertService:
    """Generate read-only risk alerts from real demo performance records."""

    def __init__(
        self,
        journal: PersistentTradeJournalService | None = None,
        validation: PerformanceValidationService | None = None,
        health_monitor: StrategyHealthMonitorService | None = None,
    ) -> None:
        self.journal = journal or PersistentTradeJournalService()
        self.validation = validation or PerformanceValidationService(self.journal)
        self.health_monitor = health_monitor or StrategyHealthMonitorService(self.journal, self.validation)

    def get_status(self) -> dict[str, Any]:
        current = self.get_current_alerts()
        return {
            "status": "READY",
            "engine": "RISK_ALERTS",
            "active_alerts": len(current.get("alerts", [])),
            "message": "Read-only risk alerts from closed demo trades and drift analytics.",
            **self._safety_flags(),
        }

    def get_current_alerts(self) -> dict[str, Any]:
        trades = self._closed_trades()
        if len(trades) < self.health_monitor.MIN_CLOSED_TRADES:
            return {
                "status": "INSUFFICIENT_DATA",
                "active_alerts": 0,
                "alerts": [],
                "message": "Risk alerts require more closed demo trades.",
                "generated_at": self._now(),
                **self._safety_flags(),
            }

        alerts: list[dict[str, Any]] = []
        alerts.extend(self._consecutive_loss_alerts(trades))
        alerts.extend(self._win_rate_alerts(trades))
        alerts.extend(self._drawdown_alerts(trades))
        alerts.extend(self._drift_alerts())
        alerts.extend(self._frequency_alerts())
        alerts.extend(self._expectancy_alerts(trades))
        return {
            "status": "READY",
            "active_alerts": len(alerts),
            "alerts": alerts,
            "message": "No active strategy alerts." if not alerts else "Active read-only strategy risk alerts generated.",
            "generated_at": self._now(),
            **self._safety_flags(),
        }

    def get_history(self) -> dict[str, Any]:
        current = self.get_current_alerts()
        return {
            "status": current["status"],
            "history": [] if current["status"] == "INSUFFICIENT_DATA" else [current],
            "message": "Alert history is derived from current persistent journal state.",
            **self._safety_flags(),
        }

    def _consecutive_loss_alerts(self, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        losses = 0
        for trade in reversed(trades):
            if self._pnl(trade) < 0:
                losses += 1
            else:
                break
        if losses < 2:
            return []
        severity = "CRITICAL" if losses >= 4 else "HIGH" if losses == 3 else "WARNING"
        return [self._alert("CONSECUTIVE_LOSSES", severity, f"{losses} consecutive closed demo losses detected.", "Review recent setups before expanding demo exposure.")]

    def _win_rate_alerts(self, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(trades) < 6:
            return []
        all_win_rate = self._win_rate(trades)
        recent = trades[-3:]
        recent_win_rate = self._win_rate(recent)
        if recent_win_rate > all_win_rate - 20:
            return []
        return [self._alert("WIN_RATE_DETERIORATION", "WARNING", f"Recent win rate {recent_win_rate}% is materially below overall win rate {all_win_rate}%.", "Inspect the latest closed demo trades for setup quality changes.")]

    def _drawdown_alerts(self, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pnl_values = [self._pnl(trade) for trade in trades]
        drawdown = self._max_drawdown(pnl_values)
        gross_profit = sum(value for value in pnl_values if value > 0)
        threshold = max(5.0, gross_profit * 0.35)
        if drawdown <= threshold:
            return []
        severity = "CRITICAL" if drawdown > threshold * 2 else "HIGH"
        return [self._alert("DRAWDOWN_THRESHOLD", severity, f"Closed-trade drawdown {round(drawdown, 2)} breached threshold {round(threshold, 2)}.", "Pause strategy expansion and review drawdown contributors.")]

    def _drift_alerts(self) -> list[dict[str, Any]]:
        drift = self.validation.detect_drift()
        status = str(drift.get("drift_status") or "").upper()
        if status not in {"MODERATE_DRIFT", "MAJOR_DRIFT"}:
            return []
        severity = "CRITICAL" if status == "MAJOR_DRIFT" else "HIGH"
        return [self._alert("STRATEGY_DRIFT_ESCALATION", severity, str(drift.get("reason") or f"{status} detected."), str(drift.get("suggested_action") or "Review drift contributors."))]

    def _frequency_alerts(self) -> list[dict[str, Any]]:
        comparison = self.validation.compare()
        if comparison.get("status") != "READY":
            return []
        live_frequency = self._number(comparison.get("live", {}).get("metrics", {}).get("average_trade_frequency"))
        historical_frequency = self._number(comparison.get("historical", {}).get("metrics", {}).get("average_trade_frequency"))
        if live_frequency <= max(historical_frequency * 2, 10.0):
            return []
        return [self._alert("EXCESSIVE_TRADE_FREQUENCY", "WARNING", f"Live trade frequency {live_frequency} per day exceeds historical baseline {historical_frequency}.", "Check whether the strategy is over-triggering in demo conditions.")]

    def _expectancy_alerts(self, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        expectancy = sum(self._pnl(trade) for trade in trades) / len(trades)
        if expectancy >= 0:
            return []
        return [self._alert("NEGATIVE_EXPECTANCY", "HIGH", f"Closed demo expectancy is negative at {round(expectancy, 2)}.", "Review strategy rules and keep live execution disabled.")]

    def _alert(self, alert_type: str, severity: str, reason: str, recommendation: str) -> dict[str, Any]:
        timestamp = self._now()
        return {
            "alert_id": str(uuid5(NAMESPACE_URL, f"{alert_type}:{severity}:{reason}")),
            "alert_type": alert_type,
            "severity": severity,
            "reason": reason,
            "recommendation": recommendation,
            "timestamp": timestamp,
            **self._safety_flags(),
        }

    def _closed_trades(self) -> list[dict[str, Any]]:
        return sorted(self.journal.get_closed_trades(), key=lambda trade: str(trade.get("closed_at") or trade.get("created_at") or ""))

    def _win_rate(self, trades: list[dict[str, Any]]) -> float:
        wins = [trade for trade in trades if self._pnl(trade) > 0]
        return round((len(wins) / len(trades)) * 100, 2) if trades else 0.0

    def _max_drawdown(self, pnl_values: list[float]) -> float:
        running = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for pnl in pnl_values:
            running += pnl
            peak = max(peak, running)
            max_drawdown = max(max_drawdown, peak - running)
        return round(max_drawdown, 4)

    def _pnl(self, trade: dict[str, Any]) -> float:
        return self._number(trade.get("net_pnl"), trade.get("total_pnl"), trade.get("realized_pnl"), trade.get("profit_loss"))

    def _number(self, *values: Any) -> float:
        for value in values:
            if value in (None, ""):
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number == number:
                return number
        return 0.0

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _safety_flags(self) -> dict[str, bool]:
        return {
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "mt5_order_send_used": False,
        }
