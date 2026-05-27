from backend.replay.replay_engine import AdvancedHistoricalReplayEngine
from backend.replay.replay_models import ReplayRequest, ReplayRunResult, ReplayStatus
from backend.replay.replay_report_builder import ReplayReportBuilder
from backend.replay.replay_report_models import ReplayHistoricalReport
from backend.replay.replay_storage import ReplayStorage


class ReplayService:
    """API-facing facade for advanced institutional historical replay."""

    def __init__(
        self,
        engine: AdvancedHistoricalReplayEngine | None = None,
        storage: ReplayStorage | None = None,
        report_builder: ReplayReportBuilder | None = None,
    ) -> None:
        self.storage = storage or ReplayStorage()
        self.engine = engine or AdvancedHistoricalReplayEngine()
        self.report_builder = report_builder or ReplayReportBuilder()
        self._reports: dict[str, ReplayHistoricalReport] = {}

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
