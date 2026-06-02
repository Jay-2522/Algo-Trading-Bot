from backend.client_analytics.strategy_models import StrategyPerformanceSummary


class ComparativeAnalytics:
    """Compare strategy quality across supported symbols without fabricating outcomes."""

    def rank_symbols(self, summaries: list[StrategyPerformanceSummary]) -> list[dict]:
        ranked = sorted(summaries, key=lambda item: item.strategy_score, reverse=True)
        return [
            {
                "rank": index + 1,
                "symbol": summary.symbol,
                "strategy_score": summary.strategy_score,
                "placeholder": summary.confidence_quality == "PLACEHOLDER",
            }
            for index, summary in enumerate(ranked)
        ]

    def compare_confidence(self, summaries: list[StrategyPerformanceSummary]) -> list[dict]:
        return [{"symbol": item.symbol, "avg_confidence": item.avg_confidence, "quality": item.confidence_quality} for item in summaries]

    def compare_execution_efficiency(self, summaries: list[StrategyPerformanceSummary]) -> list[dict]:
        return [{"symbol": item.symbol, "execution_rate": item.execution_rate, "quality": item.execution_quality} for item in summaries]

    def compare_risk_efficiency(self, summaries: list[StrategyPerformanceSummary]) -> list[dict]:
        return [{"symbol": item.symbol, "risk_pass_rate": item.risk_pass_rate, "quality": item.risk_quality} for item in summaries]

    def compare_session_efficiency(self, summaries: list[StrategyPerformanceSummary]) -> list[dict]:
        return [{"symbol": item.symbol, "session_efficiency": item.session_efficiency} for item in summaries]
