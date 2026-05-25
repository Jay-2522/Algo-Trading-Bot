from uuid import uuid4

from fastapi import WebSocket

from backend.streaming.stream_models import ClientConnectionInfo, TickMessage


class WebSocketConnectionManager:
    """Track symbol subscriptions and safely broadcast JSON tick messages."""

    def __init__(self) -> None:
        self._clients: dict[str, dict[WebSocket, ClientConnectionInfo]] = {}

    async def connect(self, websocket: WebSocket, symbol: str) -> ClientConnectionInfo:
        normalized_symbol = self._normalize_symbol(symbol)
        await websocket.accept()
        info = ClientConnectionInfo(
            client_id=str(uuid4()),
            subscribed_symbol=normalized_symbol,
        )
        self._clients.setdefault(normalized_symbol, {})[websocket] = info
        return info

    def disconnect(self, websocket: WebSocket, symbol: str) -> None:
        normalized_symbol = self._normalize_symbol(symbol)
        subscribers = self._clients.get(normalized_symbol)
        if not subscribers:
            return
        subscribers.pop(websocket, None)
        if not subscribers:
            self._clients.pop(normalized_symbol, None)

    async def broadcast(self, symbol: str, message: TickMessage | dict) -> int:
        normalized_symbol = self._normalize_symbol(symbol)
        payload = message.model_dump(mode="json") if isinstance(message, TickMessage) else message
        subscribers = list(self._clients.get(normalized_symbol, {}).keys())
        broken_connections: list[WebSocket] = []
        sent_count = 0
        for websocket in subscribers:
            try:
                await websocket.send_json(payload)
                sent_count += 1
            except Exception:
                broken_connections.append(websocket)
        for websocket in broken_connections:
            self.disconnect(websocket, normalized_symbol)
        return sent_count

    def get_client_count(self) -> int:
        return sum(len(subscribers) for subscribers in self._clients.values())

    def get_symbol_client_count(self, symbol: str) -> int:
        return len(self._clients.get(self._normalize_symbol(symbol), {}))

    def get_connections(self) -> list[ClientConnectionInfo]:
        return [
            info
            for subscribers in self._clients.values()
            for info in subscribers.values()
        ]

    def _normalize_symbol(self, symbol: str) -> str:
        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")
        return normalized_symbol
