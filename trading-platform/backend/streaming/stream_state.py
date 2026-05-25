from backend.streaming.stream_models import StreamControlResponse, StreamStatus


class StreamState:
    """Maintain explicit active-stream state without spawning background work."""

    MODE = "SIMULATION_OR_MT5_READ_ONLY"

    def __init__(self, simulation_only: bool = True) -> None:
        self.simulation_only = simulation_only
        self._active_streams: set[str] = set()

    def start_stream(self, symbol: str) -> StreamControlResponse:
        normalized_symbol = self._normalize_symbol(symbol)
        already_active = normalized_symbol in self._active_streams
        self._active_streams.add(normalized_symbol)
        message = "Stream was already active." if already_active else "Stream started."
        return StreamControlResponse(
            success=True,
            symbol=normalized_symbol,
            action="START",
            message=message,
        )

    def stop_stream(self, symbol: str) -> StreamControlResponse:
        normalized_symbol = self._normalize_symbol(symbol)
        was_active = normalized_symbol in self._active_streams
        self._active_streams.discard(normalized_symbol)
        message = "Stream stopped." if was_active else "Stream was not active."
        return StreamControlResponse(
            success=True,
            symbol=normalized_symbol,
            action="STOP",
            message=message,
        )

    def is_streaming(self, symbol: str) -> bool:
        return self._normalize_symbol(symbol) in self._active_streams

    def get_active_streams(self) -> list[str]:
        return sorted(self._active_streams)

    def get_status(self, connected_clients: int = 0) -> StreamStatus:
        return StreamStatus(
            status="operational",
            active_streams=self.get_active_streams(),
            connected_clients=connected_clients,
            mode=self.MODE,
        )

    def _normalize_symbol(self, symbol: str) -> str:
        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")
        return normalized_symbol
