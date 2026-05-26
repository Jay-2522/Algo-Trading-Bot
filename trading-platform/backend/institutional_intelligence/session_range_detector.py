from datetime import datetime, time, timezone
from typing import Any

from backend.institutional_intelligence.session_models import TradingSessionRange


class SessionRangeDetector:
    """Calculate deterministic UTC dealing ranges from normalized candles."""

    SESSIONS = {
        "ASIAN": (time(0, 0), time(9, 0)),
        "LONDON": (time(7, 0), time(16, 0)),
        "NEW_YORK": (time(12, 0), time(21, 0)),
    }
    MIN_CANDLES = 2

    def detect_session_range(self, candles: list[Any] | None, session_name: str) -> TradingSessionRange:
        normalized = session_name.strip().upper()
        if normalized not in self.SESSIONS:
            raise ValueError(f"Unsupported session '{session_name}'.")
        start, end = self.SESSIONS[normalized]
        values = []
        for candle in candles or []:
            timestamp = self._timestamp(candle)
            high = self._number(candle, "high")
            low = self._number(candle, "low")
            if timestamp is None or high is None or low is None or high < low:
                continue
            if start <= timestamp.time() < end:
                values.append((high, low))
        valid = len(values) >= self.MIN_CANDLES
        high = max((item[0] for item in values), default=None)
        low = min((item[1] for item in values), default=None)
        return TradingSessionRange(
            session_name=normalized,
            start_time_utc=start.strftime("%H:%M"),
            end_time_utc=end.strftime("%H:%M"),
            high=high,
            low=low,
            midpoint=round((high + low) / 2.0, 8) if high is not None and low is not None else None,
            range_size=round(high - low, 8) if high is not None and low is not None else 0.0,
            candles_count=len(values),
            valid=valid,
        )

    def detect_all_session_ranges(self, candles: list[Any] | None) -> dict[str, TradingSessionRange]:
        return {
            session: self.detect_session_range(candles, session)
            for session in self.SESSIONS
        }

    def _timestamp(self, candle: Any) -> datetime | None:
        value = candle.get("time") if isinstance(candle, dict) else getattr(candle, "time", None)
        if value is None and isinstance(candle, dict):
            value = candle.get("timestamp")
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _number(self, candle: Any, key: str) -> float | None:
        value = candle.get(key) if isinstance(candle, dict) else getattr(candle, key, None)
        try:
            number = float(value)
            return number if number == number and abs(number) != float("inf") else None
        except (TypeError, ValueError):
            return None
