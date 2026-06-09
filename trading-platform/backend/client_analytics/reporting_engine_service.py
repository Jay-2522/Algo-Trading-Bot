from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any

from backend.analytics.performance_validation_service import PerformanceValidationService
from backend.analytics.trade_outcome_intelligence_service import TradeOutcomeIntelligenceService
from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService


class ReportingEngineService:
    """Reports V2 generated from persistent journal and derived analytics only."""

    CSV_HEADERS = [
        "report_id",
        "report_type",
        "period",
        "symbol",
        "total_trades",
        "closed_demo_trades",
        "win_rate",
        "net_pnl",
        "avg_rr",
        "generated_at",
    ]

    def __init__(self, journal: PersistentTradeJournalService | None = None) -> None:
        self.journal = journal or PersistentTradeJournalService()
        self.outcomes = TradeOutcomeIntelligenceService(self.journal)
        self.performance_validation = PerformanceValidationService(self.journal)

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "READY",
            "reports": ["DAILY", "WEEKLY", "MONTHLY", "SYMBOL"],
            "data_source": "persistent_trade_journal",
            "message": "Reports will populate after demo trades are recorded.",
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def build_daily_report(self) -> dict[str, Any]:
        return self._build_report("DAILY", "TODAY", since=datetime.now(timezone.utc) - timedelta(days=1))

    def build_weekly_report(self) -> dict[str, Any]:
        return self._build_report("WEEKLY", "CURRENT_WEEK", since=datetime.now(timezone.utc) - timedelta(days=7))

    def build_monthly_report(self) -> dict[str, Any]:
        return self._build_report("MONTHLY", "CURRENT_MONTH", since=datetime.now(timezone.utc) - timedelta(days=30))

    def build_symbol_report(self, symbol: str) -> dict[str, Any]:
        normalized = symbol.upper()
        trades = [trade for trade in self.journal.list_trades(limit=100000) if str(trade.get("symbol", "")).upper() == normalized]
        return self._report_payload("SYMBOL", normalized, trades, symbol=normalized)

    def export_json(self) -> dict[str, Any]:
        return {
            "status": "READY",
            "reports": {
                "daily": self.build_daily_report(),
                "weekly": self.build_weekly_report(),
                "monthly": self.build_monthly_report(),
            },
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def export_csv(self) -> str:
        rows = [self._csv_row(self.build_daily_report()), self._csv_row(self.build_weekly_report()), self._csv_row(self.build_monthly_report())]
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=self.CSV_HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()

    def build_performance_v3(self) -> dict[str, Any]:
        summary = self.outcomes.get_summary()
        return {
            "status": "READY",
            "report_type": "PERFORMANCE_V3",
            "data_source": "trade_outcome_intelligence",
            "performance_summary": summary,
            "symbol_breakdown": self.outcomes.get_symbol_performance(),
            "session_breakdown": self.outcomes.get_session_performance(),
            "outcome_attribution_summary": summary.get("outcome_attribution", {}),
            "empty_state": summary.get("total_closed_trades", 0) == 0,
            "message": "No closed demo trades available." if summary.get("total_closed_trades", 0) == 0 else "Performance V3 derived from closed demo trade outcomes.",
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def build_performance_validation_v4(self) -> dict[str, Any]:
        comparison = self.performance_validation.compare()
        drift = self.performance_validation.detect_drift()
        insufficient = comparison.get("status") == "INSUFFICIENT_DATA"
        return {
            "status": "INSUFFICIENT_DATA" if insufficient else "READY",
            "report_type": "PERFORMANCE_VALIDATION_V4",
            "data_source": "persistent_journal_and_backtest_storage",
            "performance_validation_report": {
                "live_vs_historical_comparison": comparison,
                "drift_explanation": {
                    "drift_status": drift.get("drift_status"),
                    "reason": drift.get("reason"),
                    "contributing_metrics": drift.get("contributing_metrics", []),
                    "suggested_action": drift.get("suggested_action"),
                },
                "confidence_summary": {
                    "confidence_score": comparison.get("confidence_score"),
                    "drift_score": comparison.get("drift_score"),
                    "status": "INSUFFICIENT_DATA" if insufficient else "READY",
                },
                "strategy_health_score": comparison.get("strategy_health_score"),
            },
            "message": "Insufficient closed live demo or historical backtest data." if insufficient else "Performance validation report built from closed demo outcomes and historical backtests.",
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _build_report(self, report_type: str, period: str, since: datetime) -> dict[str, Any]:
        trades = [trade for trade in self.journal.list_trades(limit=100000) if self._created_at(trade) >= since]
        return self._report_payload(report_type, period, trades)

    def _report_payload(self, report_type: str, period: str, trades: list[dict[str, Any]], symbol: str | None = None) -> dict[str, Any]:
        generated_at = datetime.now(timezone.utc).isoformat()
        closed = [trade for trade in trades if trade.get("status") == "CLOSED"]
        wins = [trade for trade in closed if trade.get("result") == "WIN"]
        pnl_values = [float(trade.get("profit_loss") or 0) for trade in closed]
        realized_values = [float(trade.get("realized_pnl") if trade.get("realized_pnl") is not None else trade.get("profit_loss") or 0) for trade in closed]
        rr_values = [float(trade.get("risk_reward_ratio") or 0) for trade in trades if trade.get("risk_reward_ratio") is not None]
        summary = {
            "total_trades": len(trades),
            "closed_demo_trades": len(closed),
            "win_rate": round((len(wins) / len(closed)) * 100, 2) if closed else 0.0,
            "net_pnl": round(sum(pnl_values), 2) if pnl_values else 0.0,
            "realized_pnl": round(sum(realized_values), 2) if realized_values else 0.0,
            "avg_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0,
            "best_trade": self._trade_extreme(closed, best=True),
            "worst_trade": self._trade_extreme(closed, best=False),
            "empty_state": len(trades) == 0,
            "closed_empty_state": len(closed) == 0,
        }
        return {
            "report_id": f"reports_v2_{report_type.lower()}_{period.lower()}",
            "report_type": report_type,
            "period": period,
            "symbol": symbol,
            "generated_at": generated_at,
            "summary": summary,
            "trades": trades,
            "message": "Reports will populate after demo trades are recorded." if len(trades) == 0 else "Report derived from persistent trade journal data.",
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _csv_row(self, report: dict[str, Any]) -> dict[str, Any]:
        summary = report["summary"]
        return {
            "report_id": report["report_id"],
            "report_type": report["report_type"],
            "period": report["period"],
            "symbol": report.get("symbol") or "",
            "total_trades": summary["total_trades"],
            "closed_demo_trades": summary["closed_demo_trades"],
            "win_rate": summary["win_rate"],
            "net_pnl": summary["net_pnl"],
            "avg_rr": summary["avg_rr"],
            "generated_at": report["generated_at"],
        }

    def _created_at(self, trade: dict[str, Any]) -> datetime:
        value = trade.get("created_at")
        if not value:
            return datetime.fromtimestamp(0, timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return datetime.fromtimestamp(0, timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _trade_extreme(self, trades: list[dict[str, Any]], best: bool) -> dict[str, Any] | None:
        with_pnl = [trade for trade in trades if trade.get("profit_loss") is not None]
        if not with_pnl:
            return None
        return sorted(with_pnl, key=lambda trade: float(trade.get("profit_loss") or 0), reverse=best)[0]
