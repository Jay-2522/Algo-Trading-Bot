from backend.replay.replay_engine import AdvancedHistoricalReplayEngine
from backend.replay.replay_models import ReplayRequest, ReplayRunResult, ReplayStatus
from backend.replay.replay_calibration_models import ReplayCalibrationReport
from backend.replay.replay_calibration_report_builder import ReplayCalibrationReportBuilder
from backend.replay.replay_comparison_models import (
    ReplayFilterComparison,
    ReplayScenarioComparison,
    ReplayTimeframeComparison,
)
from backend.replay.replay_comparison_report_builder import ReplayComparisonReportBuilder
from backend.replay.replay_filter_comparator import ReplayFilterComparator
from backend.replay.replay_report_builder import ReplayReportBuilder
from backend.replay.replay_report_models import ReplayHistoricalReport
from backend.replay.replay_storage import ReplayStorage
from backend.replay.replay_timeframe_comparator import ReplayTimeframeComparator


class ReplayService:
    """API-facing facade for advanced institutional historical replay."""

    def __init__(
        self,
        engine: AdvancedHistoricalReplayEngine | None = None,
        storage: ReplayStorage | None = None,
        report_builder: ReplayReportBuilder | None = None,
        calibration_builder: ReplayCalibrationReportBuilder | None = None,
        comparison_builder: ReplayComparisonReportBuilder | None = None,
    ) -> None:
        self.storage = storage or ReplayStorage()
        self.engine = engine or AdvancedHistoricalReplayEngine()
        self.report_builder = report_builder or ReplayReportBuilder()
        self.calibration_builder = calibration_builder or ReplayCalibrationReportBuilder()
        self.comparison_builder = comparison_builder or ReplayComparisonReportBuilder()
        self._reports: dict[str, ReplayHistoricalReport] = {}
        self._calibrations: dict[str, ReplayCalibrationReport] = {}

    def get_status(self) -> ReplayStatus:
        return ReplayStatus()

    def run_replay(
        self,
        symbol: str,
        timeframe: str = "M15",
        request: ReplayRequest | None = None,
    ) -> ReplayRunResult:
        configured = (request or ReplayRequest()).model_copy(
            update={"symbol": symbol.strip().upper(), "timeframe": timeframe.strip().upper()}
        )
        result = self.engine.run_replay(ReplayRequest.model_validate(configured.model_dump()))
        stored = self.storage.save_result(result)
        self.build_report_for_run(stored)
        self.get_replay_calibration(stored.replay_id)
        return stored

    def get_recent_replays(self, limit: int = 50) -> list[ReplayRunResult]:
        return self.storage.get_recent_results(limit)

    def get_replay_result(self, replay_id: str) -> ReplayRunResult | None:
        return self.storage.get_result(replay_id)

    def get_replay_report(self, replay_id: str) -> ReplayHistoricalReport | None:
        if replay_id in self._reports:
            return self._reports[replay_id]
        result = self.storage.get_result(replay_id)
        if result is None:
            return None
        return self.build_report_for_run(result)

    def build_report_for_run(self, replay_result: ReplayRunResult) -> ReplayHistoricalReport:
        report = self.report_builder.build_report(replay_result)
        self._reports[report.replay_id] = report
        return report

    def get_latest_replay_report(self) -> ReplayHistoricalReport:
        recent = self.storage.get_recent_results(1)
        if recent:
            return self.get_replay_report(recent[-1].replay_id) or self.build_report_for_run(recent[-1])
        empty = ReplayRunResult(
            replay_id="NO-REPLAY",
            symbol="N/A",
            timeframe="N/A",
            summary="No replay runs are available yet.",
            simulation_only=True,
            live_execution_enabled=False,
        )
        return self.report_builder.build_report(empty)

    def get_replay_calibration(self, replay_id: str) -> ReplayCalibrationReport | None:
        if replay_id in self._calibrations:
            return self._calibrations[replay_id]
        result = self.storage.get_result(replay_id)
        if result is None:
            return None
        replay_report = self.get_replay_report(replay_id)
        calibration = self.calibration_builder.build_report(result, replay_report)
        self._calibrations[replay_id] = calibration
        return calibration

    def get_latest_replay_calibration(self) -> ReplayCalibrationReport:
        recent = self.storage.get_recent_results(1)
        if recent:
            return self.get_replay_calibration(recent[-1].replay_id) or self.calibration_builder.build_report(recent[-1])
        empty = ReplayRunResult(
            replay_id="NO-REPLAY",
            symbol="N/A",
            timeframe="N/A",
            summary="No replay runs are available yet.",
            simulation_only=True,
            live_execution_enabled=False,
        )
        return self.calibration_builder.build_report(empty, self.report_builder.build_report(empty))

    def compare_recent_replays(self, limit: int = 5) -> ReplayScenarioComparison:
        results = self.storage.get_recent_results(max(1, limit))
        reports = [self.get_replay_report(result.replay_id) for result in results]
        calibrations = [self.get_replay_calibration(result.replay_id) for result in results]
        return self.comparison_builder.build_comparison_report(
            [report for report in reports if report is not None],
            [calibration for calibration in calibrations if calibration is not None],
        )

    def compare_replay_ids(self, replay_ids: list[str]) -> ReplayScenarioComparison:
        reports: list[ReplayHistoricalReport] = []
        calibrations: list[ReplayCalibrationReport] = []
        for replay_id in replay_ids:
            report = self.get_replay_report(replay_id)
            calibration = self.get_replay_calibration(replay_id)
            if report is not None:
                reports.append(report)
            if calibration is not None:
                calibrations.append(calibration)
        return self.comparison_builder.build_comparison_report(reports, calibrations)

    def compare_timeframes(self, symbol: str) -> ReplayTimeframeComparison:
        symbol = symbol.strip().upper()
        reports = [
            report
            for result in self.storage.get_recent_results(100)
            if result.symbol.upper() == symbol
            for report in [self.get_replay_report(result.replay_id)]
            if report is not None
        ]
        if not reports:
            fallback = ReplayTimeframeComparator().compare_timeframes([])
            fallback.symbol = symbol
            return fallback
        return ReplayTimeframeComparator().compare_timeframes(reports)

    def compare_filters(self) -> ReplayFilterComparison:
        calibrations = [
            calibration
            for result in self.storage.get_recent_results(100)
            for calibration in [self.get_replay_calibration(result.replay_id)]
            if calibration is not None
        ]
        return ReplayFilterComparator().compare_filters(calibrations)
