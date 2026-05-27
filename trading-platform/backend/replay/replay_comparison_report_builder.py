from backend.replay.replay_calibration_models import ReplayCalibrationReport
from backend.replay.replay_comparison_models import ReplayScenarioComparison
from backend.replay.replay_filter_comparator import ReplayFilterComparator
from backend.replay.replay_report_models import ReplayHistoricalReport
from backend.replay.replay_scenario_comparator import ReplayScenarioComparator
from backend.replay.replay_timeframe_comparator import ReplayTimeframeComparator


class ReplayComparisonReportBuilder:
    """Build consolidated replay scenario comparison output."""

    def __init__(
        self,
        scenario_comparator: ReplayScenarioComparator | None = None,
        timeframe_comparator: ReplayTimeframeComparator | None = None,
        filter_comparator: ReplayFilterComparator | None = None,
    ) -> None:
        self.scenario_comparator = scenario_comparator or ReplayScenarioComparator()
        self.timeframe_comparator = timeframe_comparator or ReplayTimeframeComparator()
        self.filter_comparator = filter_comparator or ReplayFilterComparator()

    def build_comparison_report(
        self,
        replay_reports: list[ReplayHistoricalReport],
        calibration_reports: list[ReplayCalibrationReport] | None = None,
    ) -> ReplayScenarioComparison:
        calibration_reports = calibration_reports or []
        comparison = self.scenario_comparator.compare_scenarios(replay_reports, calibration_reports)
        timeframe = self.timeframe_comparator.compare_timeframes(replay_reports)
        filters = self.filter_comparator.compare_filters(calibration_reports)

        comparison.key_insights.extend(
            insight
            for insight in [timeframe.insight, filters.insight]
            if insight and insight not in comparison.key_insights
        )
        if timeframe.best_timeframe != "N/A":
            comparison.recommendations.append(f"Prioritize deeper testing on {timeframe.best_timeframe}.")
        if filters.most_restrictive_filter != "NONE":
            comparison.recommendations.append(
                f"Review {filters.most_restrictive_filter} filter calibration before broader optimization."
            )
        comparison.simulation_only = True
        comparison.live_execution_enabled = False
        return comparison
