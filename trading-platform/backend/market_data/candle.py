from datetime import datetime

from pydantic import BaseModel, Field


class Candle(BaseModel):
    """Normalized OHLCV candle used by APIs and future strategy consumers."""

    symbol: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int
    real_volume: int

    def to_dict(self) -> dict:
        """Return a JSON-safe representation of the candle."""

        return self.model_dump(mode="json")

