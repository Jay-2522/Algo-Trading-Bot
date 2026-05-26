from datetime import datetime, timezone
from typing import Any

from backend.institutional_intelligence.paper_trade_lifecycle import PaperTradeLifecycleEngine
from backend.institutional_intelligence.paper_trade_models import PaperTradeCandidate, PaperTradePosition


class PaperTradeTracker:
    """Advance pending and active paper records against read-only candle observations."""

    def __init__(self, lifecycle: PaperTradeLifecycleEngine | None = None) -> None:
        self.lifecycle = lifecycle or PaperTradeLifecycleEngine()

    def update_candidate(
        self, candidate: PaperTradeCandidate, candles: list[Any] | None
    ) -> tuple[PaperTradeCandidate, PaperTradePosition | None]:
        if candidate.status != "PENDING":
            return candidate, None
        for index, candle in enumerate(candles or []):
            timestamp = self._timestamp(candle)
            if timestamp is None:
                continue
            expired = self.lifecycle.expire_candidate(candidate, timestamp)
            if expired.status == "EXPIRED":
                return expired, None
            if self._entry_touched(candidate, candle):
                midpoint = (candidate.entry_low + candidate.entry_high) / 2.0
                position = self.lifecycle.activate_candidate(candidate, midpoint, timestamp)
                active_candidate = candidate.model_copy(update={"status": "ACTIVE"})
                return active_candidate, self.update_position(position, (candles or [])[index:]) if position else None
        return candidate, None

    def update_position(self, position: PaperTradePosition, candles: list[Any] | None) -> PaperTradePosition:
        if position.status != "ACTIVE":
            return position
        for candle in candles or []:
            timestamp = self._timestamp(candle)
            high = self._number(candle, "high")
            low = self._number(candle, "low")
            if timestamp is None or high is None or low is None:
                continue
            if position.direction == "BUY":
                if low <= position.invalidation_level:
                    return self.lifecycle.close_position(position, position.invalidation_level, "INVALIDATION", timestamp)
                if high >= position.target_level:
                    return self.lifecycle.close_position(position, position.target_level, "TARGET", timestamp)
            else:
                if high >= position.invalidation_level:
                    return self.lifecycle.close_position(position, position.invalidation_level, "INVALIDATION", timestamp)
                if low <= position.target_level:
                    return self.lifecycle.close_position(position, position.target_level, "TARGET", timestamp)
        return position

    def _entry_touched(self, candidate: PaperTradeCandidate, candle: Any) -> bool:
        high = self._number(candle, "high")
        low = self._number(candle, "low")
        if high is None or low is None:
            return False
        return low <= candidate.entry_high and high >= candidate.entry_low

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
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
