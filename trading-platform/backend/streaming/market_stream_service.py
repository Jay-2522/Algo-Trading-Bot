from fastapi import WebSocket

from backend.streaming.connection_manager import WebSocketConnectionManager
from backend.streaming.stream_logger import StreamLogger
from backend.streaming.stream_models import ClientConnectionInfo, StreamControlResponse, StreamStatus, TickMessage
from backend.streaming.stream_state import StreamState
from backend.streaming.tick_streamer import TickStreamer
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class MarketStreamService:
    """Coordinate read-only tick production, subscriber state, and broadcasts."""

    def __init__(
        self,
        state: StreamState | None = None,
        tick_streamer: TickStreamer | None = None,
        connections: WebSocketConnectionManager | None = None,
        stream_logger: StreamLogger | None = None,
    ) -> None:
        self.state = state or StreamState()
        self.tick_streamer = tick_streamer or TickStreamer()
        self.connections = connections or WebSocketConnectionManager()
        self.stream_logger = stream_logger or StreamLogger()
        self._last_price_log_at: dict[str, float] = {}

    def get_status(self) -> StreamStatus:
        return self.state.get_status(self.connections.get_client_count())

    def start_stream(self, symbol: str) -> StreamControlResponse:
        result = self.state.start_stream(symbol)
        self.stream_logger.log_event("STREAM_STARTED", result.symbol, result.message)
        return result

    def stop_stream(self, symbol: str) -> StreamControlResponse:
        result = self.state.stop_stream(symbol)
        self.stream_logger.log_event("STREAM_STOPPED", result.symbol, result.message)
        return result

    def get_tick_once(self, symbol: str) -> TickMessage:
        tick = self.tick_streamer.get_tick(symbol)
        self._log_price_tick(tick)
        return tick

    def _log_price_tick(self, tick: TickMessage) -> None:
        # Keep high-frequency quote logging lightweight; DB audit writes are too heavy for 500ms feeds.
        from time import monotonic

        now = monotonic()
        last = self._last_price_log_at.get(tick.symbol, 0.0)
        if now - last < 5.0:
            return
        self._last_price_log_at[tick.symbol] = now
        logger.info(
            "PRICE_TICK_RECEIVED %s bid=%s ask=%s spread=%s source=%s timestamp=%s",
            tick.symbol,
            tick.bid,
            tick.ask,
            tick.spread,
            tick.source,
            tick.timestamp,
        )

    async def broadcast_tick(self, symbol: str) -> TickMessage:
        tick = self.get_tick_once(symbol)
        await self.connections.broadcast(tick.symbol, tick)
        return tick

    async def register_client(self, websocket: WebSocket, symbol: str) -> ClientConnectionInfo:
        info = await self.connections.connect(websocket, symbol)
        self.stream_logger.log_event(
            "CLIENT_CONNECTED",
            info.subscribed_symbol,
            "WebSocket subscriber connected.",
            {"client_id": info.client_id},
        )
        return info

    def unregister_client(self, websocket: WebSocket, symbol: str) -> None:
        self.connections.disconnect(websocket, symbol)
        self.stream_logger.log_event(
            "CLIENT_DISCONNECTED",
            symbol.strip().upper(),
            "WebSocket subscriber disconnected.",
        )

    def get_clients(self) -> dict:
        return {
            "connected_clients": self.connections.get_client_count(),
            "active_streams": self.state.get_active_streams(),
            "clients": [
                info.model_dump(mode="json")
                for info in self.connections.get_connections()
            ],
        }
