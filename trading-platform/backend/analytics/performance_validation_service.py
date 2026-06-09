from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.backtesting.backtest_storage import BacktestStorage
from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService


DRIFT_LEVELS = ("NORMAL", "MINOR_DRIFT", "MODERATE_DRIFT", "MAJOR_DRIFT")


class PerformanceValidationService:
    """Compare closed demo performance with stored historical backtests."""

    def __init__(
        self,
        journal: PersistentTradeJournalService | None = None,
        backtest_storage: BacktestStorage | None = None,
    ) -> None:
        self.journal = journal or PersistentTradeJournalService()
        self.backtest_storage = backtest_storage or BacktestStorage()

    def get_status(self) -> dict[str, Any]:
        live = self.get_live_performance()
        historical = self.get_historical_performance()
        return {
            "status": "READY",
            "engine": "PERFORMANCE_VALIDATION",
            "live_status": live["status"],
            "historical_status": historical["status"],
            "comparison_status": "READY" if live["status"] == "READY" and historical["status"] == "READY" else "INSUFFICIENT_DATA",
            "message": "Compares closed MT5 demo trades against stored historical backtests without execution access.",
            **self._safety_flags(),
        }

    def get_live_performance(self) -> dict[str, Any]:
        trades = self.journal.get_closed_trades()
        if not trades:
            return self._empty_metrics("LIVE_DEMO", "No closed demo trades available for validation.")
        pnl_values = [self._number(trade.get("net_pnl"), trade.get("total_pnl"), trade.get("realized_pnl"), trade.get("profit_loss")) for trade in trades]
        wins = [value for value in pnl_values if value > 0]
        rr_values = [self._number(trade.get("realized_rr"), trade.get("risk_reward_ratio")) for trade in trades if self._number_or_none(trade.get("realized_rr"), trade.get("risk_reward_ratio")) is not None]
        durations = [self._number(trade.get("duration_minutes")) for trade in trades if self._number_or_none(trade.get("duration_minutes")) is not None]
        timestamps = [self._parse_time(trade.get("closed_at") or trade.get("created_at")) for trade in trades]
        timestamps = [value for value in timestamps if value is not None]
        net_pnl = sum(pnl_values)
        return {
            "status": "READY",
            "source": "LIVE_DEMO",
            "trade_count": len(trades),
            "metrics": {
                "win_rate": round((len(wins) / len(trades)) * 100, 2),
                "avg_rr": round(sum(rr_values) / len(rr_values), 4) if rr_values else 0.0,
                "net_pnl": round(net_pnl, 4),
                "expectancy": round(net_pnl / len(trades), 4),
                "average_duration_minutes": round(sum(durations) / len(durations), 2) if durations else 0.0,
                "average_trade_frequency": self._frequency_per_day(len(trades), timestamps),
            },
            "data_source": "persistent_trade_journal",
            **self._safety_flags(),
        }

    def get_historical_performance(self) -> dict[str, Any]:
        results = self._get_backtest_results()
        if not results:
            return self._empty_metrics("HISTORICAL_BACKTEST", "No stored historical backtest results available for validation.")

        total_trades = 0
        winning_trades = 0
        net_pnl = 0.0
        rr_weighted_total = 0.0
        expectancy_weighted_total = 0.0
        durations: list[float] = []
        timestamps: list[datetime] = []

        for result in results:
            metrics = self._get(result, "metrics", {})
            result_trades = int(self._number(self._get(metrics, "total_trades"), self._get(result, "total_trades")))
            if result_trades <= 0:
                continue
            total_trades += result_trades
            winning_trades += int(self._number(self._get(metrics, "winning_trades"), self._get(result, "winning_trades")))
            result_net = self._number(self._get(metrics, "net_profit"), self._get(result, "net_profit"))
            result_rr = self._number(self._get(metrics, "average_rr"), self._get(result, "average_rr"))
            result_expectancy = self._number(self._get(metrics, "expectancy"))
            net_pnl += result_net
            rr_weighted_total += result_rr * result_trades
            expectancy_weighted_total += result_expectancy * result_trades

            for trade in self._get(result, "trade_history", []) or []:
                entry_time = self._parse_time(self._get(trade, "entry_time"))
                exit_time = self._parse_time(self._get(trade, "exit_time"))
                if entry_time and exit_time and exit_time >= entry_time:
                    durations.append((exit_time - entry_time).total_seconds() / 60)
                    timestamps.append(exit_time)

            start_time = self._parse_time(self._get(result, "start_date"))
            end_time = self._parse_time(self._get(result, "end_date"))
            if start_time:
                timestamps.append(start_time)
            if end_time:
                timestamps.append(end_time)

        if total_trades <= 0:
            return self._empty_metrics("HISTORICAL_BACKTEST", "Stored backtests do not contain closed trades.")

        return {
            "status": "READY",
            "source": "HISTORICAL_BACKTEST",
            "backtest_count": len(results),
            "trade_count": total_trades,
            "metrics": {
                "win_rate": round((winning_trades / total_trades) * 100, 2),
                "avg_rr": round(rr_weighted_total / total_trades, 4),
                "net_pnl": round(net_pnl, 4),
                "expectancy": round(expectancy_weighted_total / total_trades if expectancy_weighted_total else net_pnl / total_trades, 4),
                "average_duration_minutes": round(sum(durations) / len(durations), 2) if durations else 0.0,
                "average_trade_frequency": self._frequency_per_day(total_trades, timestamps),
            },
            "data_source": "stored_backtest_results",
            **self._safety_flags(),
        }

    def compare(self) -> dict[str, Any]:
        live = self.get_live_performance()
        historical = self.get_historical_performance()
        if live["status"] != "READY" or historical["status"] != "READY":
            return {
                "status": "INSUFFICIENT_DATA",
                "comparison_available": False,
                "historical": historical,
                "live": live,
                "variance": {},
                "deviation": {},
                "drift_score": None,
                "confidence_score": None,
                "message": "Validation requires at least one closed live demo trade and one historical backtest with trades.",
                **self._safety_flags(),
            }

        variance: dict[str, float] = {}
        deviation: dict[str, float] = {}
        for metric in ("win_rate", "avg_rr", "net_pnl", "expectancy", "average_duration_minutes", "average_trade_frequency"):
            live_value = self._number(live["metrics"].get(metric))
            historical_value = self._number(historical["metrics"].get(metric))
            variance[metric] = round(live_value - historical_value, 4)
            deviation[metric] = self._deviation_percent(live_value, historical_value)

        drift_score = self._drift_score(deviation)
        confidence_score = self._confidence_score(drift_score, int(live["trade_count"]), int(historical["trade_count"]))
        drift_status = self._classify_score(drift_score)
        return {
            "status": "READY",
            "comparison_available": True,
            "historical": historical,
            "live": live,
            "variance": variance,
            "deviation": deviation,
            "drift_score": drift_score,
            "drift_status": drift_status,
            "confidence_score": confidence_score,
            "strategy_health_score": confidence_score,
            "message": "Live demo performance compared against stored historical backtest expectations.",
            **self._safety_flags(),
        }

    def detect_drift(self) -> dict[str, Any]:
        comparison = self.compare()
        if comparison["status"] != "READY":
            return {
                "status": "INSUFFICIENT_DATA",
                "drift_status": "INSUFFICIENT_DATA",
                "reason": "Not enough closed live demo trades or historical backtest trades to classify drift.",
                "contributing_metrics": [],
                "suggested_action": "Continue collecting real demo outcomes and historical backtests before changing strategy parameters.",
                "comparison": comparison,
                **self._safety_flags(),
            }

        drift_score = float(comparison["drift_score"])
        drift_status = self._classify_score(drift_score)
        contributing = self._contributing_metrics(comparison["deviation"])
        return {
            "status": "READY",
            "drift_status": drift_status,
            "drift_score": drift_score,
            "confidence_score": comparison["confidence_score"],
            "reason": self._drift_reason(drift_status, contributing),
            "contributing_metrics": contributing,
            "suggested_action": self._suggested_action(drift_status),
            "comparison": comparison,
            **self._safety_flags(),
        }

    def _get_backtest_results(self) -> list[Any]:
        try:
            return list(self.backtest_storage.get_recent_results(limit=50))
        except Exception:
            return []

    def _empty_metrics(self, source: str, message: str) -> dict[str, Any]:
        return {
            "status": "INSUFFICIENT_DATA",
            "source": source,
            "trade_count": 0,
            "metrics": {
                "win_rate": 0.0,
                "avg_rr": 0.0,
                "net_pnl": 0.0,
                "expectancy": 0.0,
                "average_duration_minutes": 0.0,
                "average_trade_frequency": 0.0,
            },
            "message": message,
            **self._safety_flags(),
        }

    def _drift_score(self, deviation: dict[str, float]) -> float:
        weights = {
            "win_rate": 0.3,
            "avg_rr": 0.25,
            "net_pnl": 0.25,
            "average_trade_frequency": 0.2,
        }
        score = 0.0
        for metric, weight in weights.items():
            score += min(abs(deviation.get(metric, 0.0)), 100.0) * weight
        return round(score, 2)

    def _confidence_score(self, drift_score: float, live_count: int, historical_count: int) -> float:
        sample_factor = min(1.0, (live_count / 20) * 0.6 + (historical_count / 100) * 0.4)
        confidence = max(0.0, 100.0 - drift_score) * sample_factor
        return round(confidence, 2)

    def _classify_score(self, score: float) -> str:
        if score < 20:
            return "NORMAL"
        if score < 40:
            return "MINOR_DRIFT"
        if score < 70:
            return "MODERATE_DRIFT"
        return "MAJOR_DRIFT"

    def _contributing_metrics(self, deviation: dict[str, float]) -> list[dict[str, Any]]:
        labels = {
            "win_rate": "win rate deviation",
            "avg_rr": "RR deviation",
            "net_pnl": "PnL deviation",
            "average_trade_frequency": "frequency deviation",
        }
        contributors = []
        for metric, label in labels.items():
            value = abs(float(deviation.get(metric, 0.0)))
            if value >= 10:
                contributors.append({"metric": metric, "label": label, "deviation_percent": round(value, 2)})
        return sorted(contributors, key=lambda item: item["deviation_percent"], reverse=True)

    def _drift_reason(self, drift_status: str, contributing_metrics: list[dict[str, Any]]) -> str:
        if drift_status == "NORMAL":
            return "Live demo results remain within the normal variance band of historical expectations."
        if not contributing_metrics:
            return f"{drift_status} detected from combined metric variance."
        joined = ", ".join(item["label"] for item in contributing_metrics[:3])
        return f"{drift_status} detected from {joined}."

    def _suggested_action(self, drift_status: str) -> str:
        return {
            "NORMAL": "Continue monitoring with the current demo-only controls.",
            "MINOR_DRIFT": "Review recent outcomes and continue collecting closed demo trades before changing rules.",
            "MODERATE_DRIFT": "Review symbol/session attribution and pause strategy expansion until the variance is understood.",
            "MAJOR_DRIFT": "Keep live execution disabled and run a full strategy review before any further rollout.",
        }.get(drift_status, "Continue collecting validated read-only analytics.")

    def _deviation_percent(self, live_value: float, historical_value: float) -> float:
        if historical_value == 0:
            return 0.0 if live_value == 0 else 100.0
        return round(((live_value - historical_value) / abs(historical_value)) * 100, 2)

    def _frequency_per_day(self, count: int, timestamps: list[datetime]) -> float:
        if count <= 0 or len(timestamps) < 2:
            return 0.0
        earliest = min(timestamps)
        latest = max(timestamps)
        days = max((latest - earliest).total_seconds() / 86400, 1.0)
        return round(count / days, 4)

    def _parse_time(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

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

    def _get(self, source: Any, key: str, fallback: Any = None) -> Any:
        if isinstance(source, dict):
            return source.get(key, fallback)
        return getattr(source, key, fallback)

    def _safety_flags(self) -> dict[str, bool]:
        return {
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "mt5_order_send_used": False,
        }
