from typing import Any


class StrategySignalStore:
    """In-memory analysis signal store for read-only dashboard/API access."""

    def __init__(self) -> None:
        self._signals: list[Any] = []

    def store_signal(self, signal: Any) -> Any:
        self._signals.insert(0, signal)
        self._signals = self._signals[:1000]
        return signal

    def list_signals(self, limit: int = 100) -> list[Any]:
        safe_limit = max(1, min(limit, 1000))
        return self._signals[:safe_limit]

    def get_signal(self, signal_id: str) -> Any | None:
        return next((signal for signal in self._signals if signal.signal_id == signal_id), None)


strategy_signal_store = StrategySignalStore()
