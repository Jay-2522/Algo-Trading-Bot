from typing import Any

from backend.news_intelligence.news_service import NewsService
from backend.strategy_execution_bridge.bridge_decision_store import BridgeDecisionStore
from backend.strategy_execution_bridge.final_demo_execution_store import FinalDemoExecutionStore
from backend.trade_copier.copier_execution_store import CopierExecutionStore


class AnalyticsDataCollector:
    """Collect analytics inputs from existing in-memory stores without fabricating data."""

    def collect_strategy_signals(self) -> list[Any]:
        try:
            return BridgeDecisionStore().list_decisions(1000)
        except Exception:
            return []

    def collect_demo_executions(self) -> list[Any]:
        try:
            return FinalDemoExecutionStore().list_decisions(1000)
        except Exception:
            return []

    def collect_trade_copier_results(self) -> list[Any]:
        try:
            return CopierExecutionStore().list_results(1000)
        except Exception:
            return []

    def collect_risk_decisions(self) -> list[Any]:
        try:
            from backend.api.execution_risk_routes import execution_risk_service

            return execution_risk_service.list_decisions(1000)
        except Exception:
            return []

    def collect_news_decisions(self) -> list[Any]:
        try:
            context = NewsService().get_news_risk_context()
            events = [*getattr(context, "active_events", []), *getattr(context, "upcoming_events", [])]
            return events
        except Exception:
            return []

    def collect_all(self) -> dict[str, list[Any]]:
        return {
            "strategy_signals": self.collect_strategy_signals(),
            "demo_executions": self.collect_demo_executions(),
            "trade_copier_results": self.collect_trade_copier_results(),
            "risk_decisions": self.collect_risk_decisions(),
            "news_decisions": self.collect_news_decisions(),
        }
