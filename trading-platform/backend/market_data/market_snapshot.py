from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from backend.market_data.candle import Candle


class MarketSnapshot(BaseModel):
    """Point-in-time market view for APIs, dashboards, and future strategies."""

    symbol: str
    latest_tick: Dict[str, Any]
    candles: Dict[str, List[Candle]]
    available_timeframes: List[str]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "ok"

    def to_dict(self) -> dict:
        """Return a JSON-safe representation of the snapshot."""

        return self.model_dump(mode="json")

