from collections import defaultdict

from backend.replay.replay_comparison_models import ReplayTimeframeComparison
from backend.replay.replay_report_models import ReplayHistoricalReport
from backend.replay.replay_scenario_ranker import ReplayScenarioRanker


class ReplayTimeframeComparator:
    """Compare replay performance grouped by timeframe."""

    def __init__(self, ranker: ReplayScenarioRanker | None = None) -> None:
        self.ranker = ranker or ReplayScenarioRanker()

    def compare_timeframes(self, replay_reports: list[ReplayHistoricalReport]) -> ReplayTimeframeComparison:
        if not replay_reports:
            return ReplayTimeframeComparison(symbol="N/A")

        grouped: dict[str, list[ReplayHistoricalReport]] = defaultdict(list)
        for report in replay_reports:
            grouped[report.timeframe].append(report)

        summaries: dict[str, dict] = {}
        for timeframe, reports in grouped.items():
            scores = [self.ranker.rank_scenario(report) for report in reports]
            net_rr = [report.trade_analytics.net_rr for report in reports]
            win_rates = [report.trade_analytics.win_rate for report in reports]
            block_rates = [report.decision_analytics.block_rate for report in reports]
            summaries[timeframe] = {
                "runs": len(reports),
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
                "average_net_rr": round(sum(net_rr) / len(net_rr), 4) if net_rr else 0.0,
                "average_win_rate": round(sum(win_rates) / len(win_rates), 2) if win_rates else 0.0,
                "average_block_rate": round(sum(block_rates) / len(block_rates), 2) if block_rates else 0.0,
            }

        best = max(summaries.items(), key=lambda item: item[1]["average_score"])[0]
        weakest = min(summaries.items(), key=lambda item: item[1]["average_score"])[0]
        symbol = replay_reports[0].symbol if replay_reports else "N/A"
        insight = (
            f"{best} is the strongest tested timeframe by average scenario score; "
            f"{weakest} is weakest."
            if len(summaries) > 1
            else f"Only {best} has replay data; run more timeframes for comparison."
        )
        return ReplayTimeframeComparison(
            symbol=symbol,
            timeframes_compared=sorted(summaries),
            best_timeframe=best,
            weakest_timeframe=weakest,
            timeframe_summaries=summaries,
            insight=insight,
        )
