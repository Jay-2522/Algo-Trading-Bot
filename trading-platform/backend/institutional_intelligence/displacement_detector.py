from typing import Any

from backend.institutional_intelligence.smc_models import DisplacementMove


class DisplacementDetector:
    """Find unusually large-bodied directional candles versus recent range."""

    def __init__(self, threshold_multiple: float = 1.5, average_window: int = 5) -> None:
        self.threshold_multiple = threshold_multiple
        self.average_window = average_window

    def detect_displacement(self, candles: list[Any] | None) -> list[DisplacementMove]:
        parsed = [self._values(candle) for candle in (candles or [])]
        if len(parsed) < self.average_window + 1:
            return []
        moves: list[DisplacementMove] = []
        for index in range(self.average_window, len(parsed)):
            current = parsed[index]
            previous = parsed[index - self.average_window : index]
            if current is None or any(item is None for item in previous):
                continue
            values = [item for item in previous if item is not None]
            average_range = sum(item["high"] - item["low"] for item in values) / len(values)
            body = abs(current["close"] - current["open"])
            if average_range <= 0 or body < average_range * self.threshold_multiple:
                continue
            direction = "BULLISH" if current["close"] > current["open"] else "BEARISH"
            moves.append(
                DisplacementMove(
                    direction=direction,
                    start_index=index,
                    end_index=index,
                    magnitude=round(body, 5),
                    candle_count=1,
                    valid=True,
                )
            )
        return moves

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda key: getattr(candle, key)
            values = {name: float(getter(name)) for name in ("open", "high", "low", "close")}
            if values["high"] < values["low"]:
                return None
            return values
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
