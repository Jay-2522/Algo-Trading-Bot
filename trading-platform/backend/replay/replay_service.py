from backend.replay.replay_engine import AdvancedHistoricalReplayEngine
from backend.replay.replay_models import ReplayRequest, ReplayRunResult, ReplayStatus
from backend.replay.replay_storage import ReplayStorage


class ReplayService:
    """API-facing facade for advanced institutional historical replay."""

    def __init__(
        self,
        engine: AdvancedHistoricalReplayEngine | None = None,
        storage: ReplayStorage | None = None,
    ) -> None:
        self.storage = storage or ReplayStorage()
        self.engine = engine or AdvancedHistoricalReplayEngine()

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
        return self.storage.save_result(result)

    def get_recent_replays(self, limit: int = 50) -> list[ReplayRunResult]:
        return self.storage.get_recent_results(limit)

    def get_replay_result(self, replay_id: str) -> ReplayRunResult | None:
        return self.storage.get_result(replay_id)
