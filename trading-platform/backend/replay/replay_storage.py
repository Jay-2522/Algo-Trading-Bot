from backend.replay.replay_models import ReplayRunResult


class ReplayStorage:
    """Safe in-memory replay storage; replaceable by persistence later."""

    def __init__(self) -> None:
        self._results: dict[str, ReplayRunResult] = {}

    def save_result(self, result: ReplayRunResult) -> ReplayRunResult:
        self._results[result.replay_id] = result
        return result

    def get_recent_results(self, limit: int = 50) -> list[ReplayRunResult]:
        return list(self._results.values())[-max(1, limit) :]

    def get_result(self, replay_id: str) -> ReplayRunResult | None:
        return self._results.get(replay_id)
