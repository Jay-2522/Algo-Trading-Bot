from collections import Counter
from typing import Any

from backend.client_analytics.analytics_data_collector import AnalyticsDataCollector
from backend.client_analytics.analytics_models import (
    ClientAnalyticsOverview,
    RiskAnalyticsSummary,
    SessionPerformanceSummary,
    SymbolPerformanceSummary,
)
from backend.client_analytics.analytics_store import AnalyticsStore
from backend.client_analytics.performance_calculator import PerformanceCalculator


class ClientAnalyticsService:
    """Client-facing analytics facade with no fake PnL or live execution behavior."""

    SUPPORTED_SYMBOLS = ["XAUUSD", "EURUSD", "NIFTY50"]
    SESSIONS = ["ASIAN", "LONDON", "NEW_YORK", "OVERLAP", "UNKNOWN"]

    def __init__(
        self,
        collector: AnalyticsDataCollector | None = None,
        calculator: PerformanceCalculator | None = None,
        store: AnalyticsStore | None = None,
    ) -> None:
        self.collector = collector or AnalyticsDataCollector()
        self.calculator = calculator or PerformanceCalculator()
        self.store = store or AnalyticsStore()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "supported_symbols": self.SUPPORTED_SYMBOLS,
            "nifty50_status": "PLACEHOLDER_ONLY",
            "analytics_mode": "READ_ONLY_NO_FAKE_PNL",
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_overview(self) -> ClientAnalyticsOverview:
        data = self.collector.collect_all()
        symbols = self.get_all_symbol_performance(data)
        risk = self.get_risk_analytics(data)
        executions = data["demo_executions"]
        pnls = [self.calculator._pnl(trade) for trade in executions]
        wins = len([pnl for pnl in pnls if pnl > 0])
        losses = len([pnl for pnl in pnls if pnl < 0])
        active_symbols = sorted(
            {
                symbol.symbol
                for symbol in symbols
                if symbol.total_signals > 0 or symbol.demo_executions > 0
            }
        )
        ranked = sorted(symbols, key=lambda item: item.net_pnl, reverse=True)
        best_symbol = ranked[0].symbol if ranked and ranked[0].net_pnl > 0 else None
        worst_symbol = ranked[-1].symbol if ranked and ranked[-1].net_pnl < 0 else None
        overview = ClientAnalyticsOverview(
            status="OPERATIONAL",
            total_signals=len(data["strategy_signals"]),
            total_demo_executions=len(executions),
            total_copy_batches=len(data["trade_copier_results"]),
            total_risk_blocks=risk.blocked,
            total_news_blocks=risk.news_blocks,
            active_symbols=active_symbols,
            supported_symbols=self.SUPPORTED_SYMBOLS,
            best_symbol=best_symbol,
            worst_symbol=worst_symbol,
            win_rate=self.calculator.calculate_win_rate(wins, losses),
            net_pnl=self.calculator.calculate_net_pnl(executions),
            profit_factor=self.calculator.calculate_profit_factor(executions),
            max_drawdown=self.calculator.calculate_max_drawdown(self._equity_curve(pnls)),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        return self.store.store_snapshot(overview)

    def get_symbol_performance(self, symbol: str, data: dict[str, list[Any]] | None = None) -> SymbolPerformanceSummary:
        normalized = symbol.upper()
        if normalized == "NIFTY50":
            return SymbolPerformanceSummary(symbol="NIFTY50")
        return self.calculator.summarize_symbol(normalized, data or self.collector.collect_all())

    def get_all_symbol_performance(self, data: dict[str, list[Any]] | None = None) -> list[SymbolPerformanceSummary]:
        data = data or self.collector.collect_all()
        return [self.get_symbol_performance(symbol, data) for symbol in self.SUPPORTED_SYMBOLS]

    def get_session_performance(self) -> list[SessionPerformanceSummary]:
        data = self.collector.collect_all()
        return [self.calculator.summarize_session(session, data) for session in self.SESSIONS]

    def get_risk_analytics(self, data: dict[str, list[Any]] | None = None) -> RiskAnalyticsSummary:
        data = data or self.collector.collect_all()
        risk_decisions = data["risk_decisions"]
        news_decisions = data["news_decisions"]
        blocked_decisions = [decision for decision in risk_decisions if not bool(getattr(decision, "approved", False))]
        reasons: list[str] = []
        news_blocks = 0
        regime_blocks = 0
        risk_engine_blocks = 0

        for decision in blocked_decisions:
            decision_reasons = [str(reason) for reason in getattr(decision, "rejection_reasons", [])]
            reasons.extend(decision_reasons)
            upper_text = " ".join(decision_reasons).upper()
            news_blocks += 1 if "NEWS" in upper_text else 0
            regime_blocks += 1 if "REGIME" in upper_text else 0
            risk_engine_blocks += 1

        for event in news_decisions:
            action = str(getattr(event, "trade_action", "")).upper()
            risk_level = str(getattr(event, "risk_level", "")).upper()
            if action == "BLOCK" or risk_level in {"HIGH", "EXTREME"}:
                news_blocks += 1
                reasons.append(getattr(event, "title", "News risk block"))

        most_common = Counter(reasons).most_common(1)
        return RiskAnalyticsSummary(
            total_risk_checks=len(risk_decisions),
            approved=len([decision for decision in risk_decisions if bool(getattr(decision, "approved", False))]),
            blocked=len(blocked_decisions),
            news_blocks=news_blocks,
            regime_blocks=regime_blocks,
            risk_engine_blocks=risk_engine_blocks,
            most_common_block_reason=most_common[0][0] if most_common else None,
        )

    def get_latest_snapshot(self) -> ClientAnalyticsOverview:
        return self.store.get_latest_snapshot() or self.get_overview()

    def _equity_curve(self, pnls: list[float]) -> list[float]:
        equity = 0.0
        curve: list[float] = []
        for pnl in pnls:
            equity += pnl
            curve.append(equity)
        return curve
