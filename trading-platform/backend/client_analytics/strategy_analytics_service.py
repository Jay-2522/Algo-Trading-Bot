from typing import Any

from backend.client_analytics.analytics_data_collector import AnalyticsDataCollector
from backend.client_analytics.comparative_analytics import ComparativeAnalytics
from backend.client_analytics.strategy_models import StrategyPerformanceSummary
from backend.nifty50.nifty_analytics_service import NIFTYAnalyticsService


class StrategyAnalyticsService:
    """Strategy intelligence summaries for supported symbols."""

    SYMBOLS = ["XAUUSD", "EURUSD", "NIFTY50"]
    SESSIONS = ["ASIAN", "LONDON", "NEW_YORK", "OVERLAP"]

    def __init__(
        self,
        collector: AnalyticsDataCollector | None = None,
        comparative: ComparativeAnalytics | None = None,
        nifty_analytics: NIFTYAnalyticsService | None = None,
    ) -> None:
        self.collector = collector or AnalyticsDataCollector()
        self.comparative = comparative or ComparativeAnalytics()
        self.nifty_analytics = nifty_analytics or NIFTYAnalyticsService()

    def get_strategy_overview(self) -> dict[str, Any]:
        summaries = self.get_all_strategy_performance()
        non_placeholder = [item for item in summaries if item.confidence_quality != "PLACEHOLDER"]
        avg_conf = self._avg([item.avg_confidence for item in non_placeholder])
        avg_risk = self._avg([item.risk_pass_rate for item in non_placeholder])
        avg_exec = self._avg([item.execution_rate for item in non_placeholder])
        rankings = self.get_rankings()
        return {
            "status": "OPERATIONAL",
            "total_strategies": len(summaries),
            "avg_confidence": avg_conf,
            "avg_risk_efficiency": avg_risk,
            "avg_execution_efficiency": avg_exec,
            "top_ranked_strategy": rankings[0]["symbol"] if rankings else None,
            "session_efficiency": self._avg([item.session_efficiency for item in non_placeholder]),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_symbol_performance(self, symbol: str) -> StrategyPerformanceSummary:
        normalized = symbol.upper()
        if normalized == "NIFTY50":
            return StrategyPerformanceSummary(
                symbol="NIFTY50",
                confidence_quality="SMC_INTELLIGENCE_READY",
                execution_quality="PLACEHOLDER",
                risk_quality="ANALYTICS_INTEGRATED",
            )
        data = self.collector.collect_all()
        signals = [signal for signal in data["strategy_signals"] if self._symbol(signal) == normalized]
        executions = [execution for execution in data["demo_executions"] if self._symbol(execution) == normalized]
        risk_decisions = [decision for decision in data["risk_decisions"] if self._symbol(decision) == normalized]
        total = len(signals)
        confidence_values = [float(getattr(signal, "confidence", 0) or 0) for signal in signals]
        avg_confidence = self._avg(confidence_values)
        execution_rate = round((len(executions) / total) * 100, 2) if total else 0.0
        approved = len([decision for decision in risk_decisions if bool(getattr(decision, "approved", False))])
        risk_pass_rate = round((approved / len(risk_decisions)) * 100, 2) if risk_decisions else 0.0
        session_efficiency = self._session_efficiency(normalized, data)
        strategy_score = round((avg_confidence + execution_rate + risk_pass_rate + session_efficiency) / 4, 2)
        return StrategyPerformanceSummary(
            symbol=normalized,
            total_signals=total,
            buy_signals=len([signal for signal in signals if str(getattr(signal, "action", "")).upper() == "BUY"]),
            sell_signals=len([signal for signal in signals if str(getattr(signal, "action", "")).upper() == "SELL"]),
            wait_signals=len([signal for signal in signals if str(getattr(signal, "action", "")).upper() == "WAIT"]),
            avg_confidence=avg_confidence,
            confidence_quality=self._quality(avg_confidence),
            execution_rate=execution_rate,
            execution_quality=self._quality(execution_rate),
            risk_pass_rate=risk_pass_rate,
            risk_quality=self._quality(risk_pass_rate),
            session_efficiency=session_efficiency,
            strategy_score=strategy_score,
        )

    def get_all_strategy_performance(self) -> list[StrategyPerformanceSummary]:
        return [self.get_symbol_performance(symbol) for symbol in self.SYMBOLS]

    def get_rankings(self) -> list[dict]:
        return self.comparative.rank_symbols(self.get_all_strategy_performance())

    def get_session_efficiency(self) -> list[dict]:
        data = self.collector.collect_all()
        signals = data["strategy_signals"]
        return [
            {
                "session": session,
                "signals": len([signal for signal in signals if self._session(signal) == session]),
                "risk_pass_rate": 0.0,
                "execution_rate": 0.0,
                "efficiency_score": 0.0,
            }
            for session in self.SESSIONS
        ]

    def get_comparative_analysis(self) -> dict[str, Any]:
        summaries = self.get_all_strategy_performance()
        return {
            "rankings": self.comparative.rank_symbols(summaries),
            "confidence": self.comparative.compare_confidence(summaries),
            "execution_efficiency": self.comparative.compare_execution_efficiency(summaries),
            "risk_efficiency": self.comparative.compare_risk_efficiency(summaries),
            "session_efficiency": self.comparative.compare_session_efficiency(summaries),
            "nifty50_status": "ANALYTICS_INTEGRATED",
            "nifty50_strategy_status": self.nifty_analytics.get_strategy_status(),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _symbol(self, item: Any) -> str | None:
        value = getattr(item, "symbol", None) or getattr(item, "canonical_symbol", None) or getattr(item, "source_symbol", None)
        return str(value).upper() if value else None

    def _session(self, item: Any) -> str:
        return str(getattr(item, "session", None) or getattr(item, "market_session", None) or "UNKNOWN").upper()

    def _avg(self, values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    def _quality(self, value: float) -> str:
        if value >= 75:
            return "HIGH"
        if value >= 50:
            return "MEDIUM"
        if value > 0:
            return "LOW"
        return "NONE"

    def _session_efficiency(self, symbol: str, data: dict[str, list[Any]]) -> float:
        signals = [signal for signal in data["strategy_signals"] if self._symbol(signal) == symbol and self._session(signal) in self.SESSIONS]
        return round(min(100, len(signals) * 10), 2) if signals else 0.0
