from backend.replay.replay_calibration_engine import ReplayCalibrationEngine
from backend.replay.replay_calibration_models import ReplayCalibrationReport
from backend.replay.replay_models import ReplayRunResult
from backend.replay.replay_report_models import ReplayHistoricalReport


class ReplayCalibrationReportBuilder:
    """Build JSON-safe replay calibration reports."""

    def __init__(self, engine: ReplayCalibrationEngine | None = None) -> None:
        self.engine = engine or ReplayCalibrationEngine()

    def build_report(
        self,
        replay_result: ReplayRunResult,
        replay_report: ReplayHistoricalReport | None = None,
    ) -> ReplayCalibrationReport:
        report = self.engine.calibrate_replay(replay_result, replay_report)
        report.simulation_only = True
        report.live_execution_enabled = False
        return report
