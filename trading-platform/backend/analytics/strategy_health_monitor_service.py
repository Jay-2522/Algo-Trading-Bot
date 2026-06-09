from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.analytics.performance_validation_service import PerformanceValidationService
from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService


class StrategyHealthMonitorService:
    """Read-only strategy health scoring from persistent demo outcomes."""

    MIN_CLOSED_TRADES = 3

    def __init__(
        self,
        journal: PersistentTradeJournalService | None = None,
        validation: PerformanceValidationService | None = None,
    ) -> None:
        self.journal = journal or PersistentTradeJournalService()
        self.validation = validation or PerformanceValidationService(self.journal)

    def get_status(self) -> dict[str, Any]:
        current = self.get_current_health()
        return {
            "status": "READY",
            "engine": "STRATEGY_HEALTH_MONITOR",
            "health_status": current.get("status"),
            "classification": current.get("classification"),
            "message": "Read-only health monitoring from closed demo trades and drift analytics.",
            **self._safety_flags(),
        }

    def get_current_health(self) -> dict[str, Any]:
        trades = self._closed_trades()
        if len(trades) < self.MIN_CLOSED_TRADES:
            return {
                "status": "INSUFFICIENT_DATA",
                "closed_trades": len(trades),
                "minimum_required_closed_trades": self.MIN_CLOSED_TRADES,
                "health_score": None,
                "classification": "INSUFFICIENT_DATA",
                "components": self._empty_components(),
                "message": "Strategy health requires more closed demo trades.",
                "generated_at": self._now(),
                **self._safety_flags(),
            }

        summary = self._summary(trades)
        drift = self.validation.detect_drift()
        components = {
            "win_rate_health": self._score_ratio(summary["win_rate"], 60.0),
            "rr_health": self._score_ratio(summary["avg_rr"], 2.0),
            "pnl_health": self._pnl_health(summary["net_pnl"], summary["expectancy"]),
            "drawdown_health": self._drawdown_health(summary["max_drawdown"]),
            "execution_quality_health": self._execution_quality_health(len(trades)),
            "drift_health": self._drift_health(drift),
        }
        health_score = round(sum(components.values()) / len(components), 2)
        classification = self._classification(health_score)
        return {
            "status": "READY",
            "closed_trades": len(trades),
            "health_score": health_score,
            "classification": classification,
            "components": components,
            "metrics": summary,
            "drift_status": drift.get("drift_status", "INSUFFICIENT_DATA"),
            "trend": self._trend(trades),
            "generated_at": self._now(),
            **self._safety_flags(),
        }

    def get_history(self) -> dict[str, Any]:
        current = self.get_current_health()
        return {
            "status": current["status"],
            "history": [] if current["status"] == "INSUFFICIENT_DATA" else [current],
            "message": "Health history is derived from current persistent journal state.",
            **self._safety_flags(),
        }

    def _closed_trades(self) -> list[dict[str, Any]]:
        return sorted(self.journal.get_closed_trades(), key=lambda trade: str(trade.get("closed_at") or trade.get("created_at") or ""))

    def _summary(self, trades: list[dict[str, Any]]) -> dict[str, Any]:
        pnl_values = [self._pnl(trade) for trade in trades]
        wins = [value for value in pnl_values if value > 0]
        rr_values = [self._number(trade.get("risk_reward_ratio")) for trade in trades if self._number_or_none(trade.get("risk_reward_ratio")) is not None]
        net_pnl = sum(pnl_values)
        return {
            "win_rate": round((len(wins) / len(trades)) * 100, 2),
            "avg_rr": round(sum(rr_values) / len(rr_values), 4) if rr_values else 0.0,
            "net_pnl": round(net_pnl, 4),
            "expectancy": round(net_pnl / len(trades), 4),
            "max_drawdown": self._max_drawdown(pnl_values),
            "consecutive_losses": self._consecutive_losses(trades),
        }

    def _max_drawdown(self, pnl_values: list[float]) -> float:
        running = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for pnl in pnl_values:
            running += pnl
            peak = max(peak, running)
            max_drawdown = max(max_drawdown, peak - running)
        return round(max_drawdown, 4)

    def _consecutive_losses(self, trades: list[dict[str, Any]]) -> int:
        count = 0
        for trade in reversed(trades):
            if self._pnl(trade) < 0:
                count += 1
            else:
                break
        return count

    def _score_ratio(self, value: float, target: float) -> float:
        if target <= 0:
            return 0.0
        return round(max(0.0, min(100.0, (value / target) * 100)), 2)

    def _pnl_health(self, net_pnl: float, expectancy: float) -> float:
        if net_pnl > 0 and expectancy > 0:
            return 100.0
        if net_pnl == 0:
            return 55.0
        return max(0.0, round(50.0 + expectancy * 5.0, 2))

    def _drawdown_health(self, drawdown: float) -> float:
        if drawdown <= 0:
            return 100.0
        return round(max(0.0, 100.0 - min(drawdown * 10.0, 100.0)), 2)

    def _execution_quality_health(self, closed_count: int) -> float:
        rejected = len([trade for trade in self.journal.list_trades(limit=100000) if trade.get("status") == "REJECTED"])
        total = closed_count + rejected
        if total <= 0:
            return 0.0
        return round(max(0.0, 100.0 - (rejected / total) * 100.0), 2)

    def _drift_health(self, drift: dict[str, Any]) -> float:
        status = str(drift.get("drift_status") or "INSUFFICIENT_DATA").upper()
        return {
            "NORMAL": 100.0,
            "MINOR_DRIFT": 75.0,
            "MODERATE_DRIFT": 45.0,
            "MAJOR_DRIFT": 10.0,
            "INSUFFICIENT_DATA": 50.0,
        }.get(status, 50.0)

    def _classification(self, score: float) -> str:
        if score >= 85:
            return "EXCELLENT"
        if score >= 70:
            return "GOOD"
        if score >= 55:
            return "WATCHLIST"
        if score >= 35:
            return "DEGRADED"
        return "CRITICAL"

    def _trend(self, trades: list[dict[str, Any]]) -> str:
        if len(trades) < 6:
            return "LIMITED_SAMPLE"
        midpoint = len(trades) // 2
        first = sum(self._pnl(trade) for trade in trades[:midpoint]) / max(1, midpoint)
        second = sum(self._pnl(trade) for trade in trades[midpoint:]) / max(1, len(trades) - midpoint)
        if second > first:
            return "IMPROVING"
        if second < first:
            return "DETERIORATING"
        return "STABLE"

    def _empty_components(self) -> dict[str, None]:
        return {
            "win_rate_health": None,
            "rr_health": None,
            "pnl_health": None,
            "drawdown_health": None,
            "execution_quality_health": None,
            "drift_health": None,
        }

    def _pnl(self, trade: dict[str, Any]) -> float:
        return self._number(trade.get("net_pnl"), trade.get("total_pnl"), trade.get("realized_pnl"), trade.get("profit_loss"))

    def _number_or_none(self, *values: Any) -> float | None:
        for value in values:
            if value in (None, ""):
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number == number:
                return number
        return None

    def _number(self, *values: Any) -> float:
        return self._number_or_none(*values) or 0.0

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
