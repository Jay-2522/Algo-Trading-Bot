from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class StreamStatus(BaseModel):
    """Current observable streaming service state."""

    status: str
    active_streams: list[str] = Field(default_factory=list)
    connected_clients: int
    mode: str
    timestamp: str = Field(default_factory=utc_timestamp)


class TickMessage(BaseModel):
    """JSON-safe tick broadcast payload."""

    symbol: str
    bid: float
    ask: float
    spread: float
    timestamp: str = Field(default_factory=utc_timestamp)
    source: str


class StreamControlResponse(BaseModel):
    """Result of an explicit stream-state control action."""

    success: bool
    symbol: str
    action: str
    message: str
    timestamp: str = Field(default_factory=utc_timestamp)


class ClientConnectionInfo(BaseModel):
    """In-memory description of a connected WebSocket subscriber."""

    client_id: str
    connected_at: str = Field(default_factory=utc_timestamp)
    subscribed_symbol: str
