from typing import Any

from backend.replay.client_symbol_registry import ClientSymbolRegistry
from backend.replay.replay_models import ReplayRequest, ReplayRunResult


class MultiSymbolReplayService:
    """Client-instrument facade over the existing replay service."""

    def __init__(self, replay_service, registry: ClientSymbolRegistry | None = None) -> None:
        self.replay_service = replay_service
        self.registry = registry or ClientSymbolRegistry()

    def run_symbol_replay(self, symbol: str, timeframe: str = "M15") -> ReplayRunResult | dict[str, Any]:
        resolution = self.registry.resolve_symbol(symbol)
        if not resolution.supported or resolution.canonical_symbol is None:
            return {
                "input_symbol": symbol,
                "supported": False,
                "message": resolution.message,
                "simulation_only": True,
                "live_execution_enabled": False,
            }
        request = ReplayRequest(
            symbol=resolution.canonical_symbol,
            timeframe=timeframe,
            window_size=30,
            step_size=10,
            max_steps=2,
        )
        return self.replay_service.run_replay(resolution.canonical_symbol, timeframe, request)

    def run_all_client_symbols(self, timeframe: str = "M15") -> dict[str, Any]:
        results: dict[str, Any] = {}
        for instrument in self.registry.list_supported_symbols():
            run = self.run_symbol_replay(instrument.canonical_symbol, timeframe)
            results[instrument.canonical_symbol] = run.model_dump(mode="json") if hasattr(run, "model_dump") else run
        return {
            "timeframe": timeframe.strip().upper(),
            "symbols": results,
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def compare_client_symbols(self, timeframe: str = "M15"):
        if not self.replay_service.get_recent_replays(1):
            self.run_all_client_symbols(timeframe)
        replay_ids = [
            result.replay_id
            for result in self.replay_service.get_recent_replays(100)
            if result.symbol in {item.canonical_symbol for item in self.registry.list_supported_symbols()}
            and result.timeframe.upper() == timeframe.strip().upper()
        ]
        return self.replay_service.compare_replay_ids(replay_ids)
