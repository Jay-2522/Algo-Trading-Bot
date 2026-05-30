from datetime import datetime, timezone
from typing import Any


class SwingPointDetector:
    """Detect local swing highs and lows from supplied candle data."""

    def detect_swings(self, candles: list[Any] | None = None, left: int = 2, right: int = 2) -> dict[str, Any]:
        if not candles or len(candles) < left + right + 1:
            return {
                "swing_highs": [],
                "swing_lows": [],
                "latest_swing_high": None,
                "latest_swing_low": None,
                "warnings": ["Insufficient candle data for swing point detection."],
            }

        try:
            normalized = [
                {
                    "index": index,
                    "time": self._time(candle).isoformat(),
                    "high": float(self._value(candle, "high")),
                    "low": float(self._value(candle, "low")),
                }
                for index, candle in enumerate(candles)
            ]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return {
                "swing_highs": [],
                "swing_lows": [],
                "latest_swing_high": None,
                "latest_swing_low": None,
                "warnings": [f"Invalid candle data supplied for swing point detection: {exc}"],
            }

        swing_highs: list[dict[str, Any]] = []
        swing_lows: list[dict[str, Any]] = []
        for index in range(left, len(normalized) - right):
            candle = normalized[index]
            left_window = normalized[index - left:index]
            right_window = normalized[index + 1:index + right + 1]
            if all(candle["high"] > item["high"] for item in left_window + right_window):
                swing_highs.append(
                    {
                        "type": "SWING_HIGH",
                        "index": candle["index"],
                        "time": candle["time"],
                        "price": candle["high"],
                    }
                )
            if all(candle["low"] < item["low"] for item in left_window + right_window):
                swing_lows.append(
                    {
                        "type": "SWING_LOW",
                        "index": candle["index"],
                        "time": candle["time"],
                        "price": candle["low"],
                    }
                )

        warnings = [] if swing_highs or swing_lows else ["No confirmed swing points detected in supplied candles."]
        return {
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "latest_swing_high": swing_highs[-1] if swing_highs else None,
            "latest_swing_low": swing_lows[-1] if swing_lows else None,
            "warnings": warnings,
        }

    def _time(self, candle: Any) -> datetime:
        raw = self._value(candle, "timestamp") if self._has_field(candle, "timestamp") else self._value(candle, "time")
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                return raw.replace(tzinfo=timezone.utc)
            return raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _has_field(self, candle: Any, field: str) -> bool:
        if isinstance(candle, dict):
            return field in candle
        return hasattr(candle, field)

    def _value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)
