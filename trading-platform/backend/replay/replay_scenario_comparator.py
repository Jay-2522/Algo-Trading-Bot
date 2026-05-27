from collections import Counter

from backend.replay.replay_calibration_models import ReplayCalibrationReport
from backend.replay.replay_comparison_models import ReplayScenarioComparison, ReplayScenarioSummary
from backend.replay.replay_report_models import ReplayHistoricalReport
from backend.replay.replay_scenario_ranker import ReplayScenarioRanker


class ReplayScenarioComparator:
    """Compare replay reports and rank their historical scenario quality."""

    def __init__(self, ranker: ReplayScenarioRanker | None = None) -> None:
        self.ranker = ranker or ReplayScenarioRanker()

    def compare_scenarios(
        self,
        replay_reports: list[ReplayHistoricalReport],
        calibration_reports: list[ReplayCalibrationReport] | None = None,
    ) -> ReplayScenarioComparison:
        if not replay_reports:
            return ReplayScenarioComparison(
                scenario_count=0,
                key_insights=["No replay reports are available for scenario comparison."],
                recommendations=["Run at least two historical replays before comparing scenarios."],
            )

        calibration_map = {item.replay_id: item for item in calibration_reports or []}
        scenarios = [
            self._summary_for_report(report, calibration_map.get(report.replay_id))
            for report in replay_reports
        ]
        scenarios.sort(key=lambda item: item.score, reverse=True)
        for idx, scenario in enumerate(scenarios, start=1):
            scenario.rank = idx

        best = scenarios[0] if scenarios else None
        weakest = scenarios[-1] if scenarios else None
        common_weaknesses = self._common_weaknesses(replay_reports, calibration_reports or [])
        insights = self._insights(scenarios)
        recommendations = self._recommendations(scenarios, common_weaknesses)

        return ReplayScenarioComparison(
            scenario_count=len(scenarios),
            scenarios=scenarios,
            best_scenario=best,
            weakest_scenario=weakest,
            common_weaknesses=common_weaknesses,
            key_insights=insights,
            recommendations=recommendations,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _summary_for_report(
        self,
        report: ReplayHistoricalReport,
        calibration: ReplayCalibrationReport | None = None,
    ) -> ReplayScenarioSummary:
        score = self.ranker.rank_scenario(report, calibration)
        return ReplayScenarioSummary(
            replay_id=report.replay_id,
            symbol=report.symbol,
            timeframe=report.timeframe,
            total_steps=int(report.metadata.get("total_steps", report.decision_analytics.total_decisions) or 0),
            total_decisions=report.decision_analytics.total_decisions,
            total_trades=report.trade_analytics.total_trades,
            win_rate=report.trade_analytics.win_rate,
            net_rr=report.trade_analytics.net_rr,
            block_rate=calibration.block_reason_metrics.block_rate if calibration else report.decision_analytics.block_rate,
            average_confidence=report.decision_analytics.average_confidence,
            optimization_status=calibration.calibration_status if calibration else "UNAVAILABLE",
            score=score,
        )

    def _common_weaknesses(
        self,
        replay_reports: list[ReplayHistoricalReport],
        calibration_reports: list[ReplayCalibrationReport],
    ) -> list[str]:
        weakness_counter: Counter[str] = Counter()
        for report in replay_reports:
            for weakness in report.weakness_insights:
                weakness_counter[weakness.category] += 1
        for calibration in calibration_reports:
            gate = calibration.block_reason_metrics.most_restrictive_gate
            if gate and gate != "NONE":
                weakness_counter[gate] += 1
        return [item for item, _ in weakness_counter.most_common(5)] or ["No recurring weaknesses detected."]

    def _insights(self, scenarios: list[ReplayScenarioSummary]) -> list[str]:
        if not scenarios:
            return ["No scenarios available."]
        if len(scenarios) == 1:
            return ["Only one replay scenario is available; ranking is informational only."]
        best = scenarios[0]
        weakest = scenarios[-1]
        return [
            f"Best replay scenario is {best.replay_id} on {best.timeframe} with score {best.score:.2f}.",
            f"Weakest replay scenario is {weakest.replay_id} on {weakest.timeframe} with score {weakest.score:.2f}.",
            f"Score spread is {best.score - weakest.score:.2f} point(s).",
        ]

    def _recommendations(self, scenarios: list[ReplayScenarioSummary], common_weaknesses: list[str]) -> list[str]:
        if not scenarios:
            return ["Run more replay scenarios before acting on comparison output."]
        recommendations: list[str] = []
        if len(scenarios) < 2:
            recommendations.append("Run at least one additional replay with a different timeframe or calibration.")
        if scenarios[0].block_rate >= 70.0:
            recommendations.append("Top scenario still has high block rate; review calibration suggestions before scaling tests.")
        if scenarios[0].total_trades == 0:
            recommendations.append("No compared scenario generated trades; loosen research filters carefully or extend the replay window.")
        if "RISK" in common_weaknesses:
            recommendations.append("Risk gate pressure is recurring; preserve hard risk controls and improve setup geometry.")
        return recommendations or ["Use the highest-ranked scenario for deeper replay sampling."]
