from datetime import datetime, time, timezone
from typing import Any

from backend.institutional_intelligence.session_models import SessionManipulationSignal, TradingSessionRange


class SessionManipulationDetector:
    """Detect confirmed session raids that return through the raided range boundary."""

    def detect_manipulation(
        self,
        candles: list[Any] | None,
        asian_range: TradingSessionRange | None = None,
        sweep_context: Any = None,
    ) -> list[SessionManipulationSignal]:
        if not asian_range or not asian_range.valid or asian_range.high is None or asian_range.low is None:
            return []
        signals: list[SessionManipulationSignal] = []
        seen: set[str] = set()
        for index, candle in enumerate(candles or []):
            timestamp = self._timestamp(candle)
            high = self._number(candle, "high")
            low = self._number(candle, "low")
            close = self._number(candle, "close")
            if timestamp is None or high is None or low is None or close is None:
                continue
            session = self._active_session(timestamp.time())
            if session not in {"LONDON", "NEW_YORK"}:
                continue
            if high > asian_range.high and close < asian_range.high and "ASIAN_HIGH_SWEEP" not in seen:
                signals.append(
                    self._signal(index, "ASIAN_HIGH_SWEEP", "BEARISH", session, asian_range.high, timestamp, 80.0)
                )
                seen.add("ASIAN_HIGH_SWEEP")
                if session == "LONDON":
                    signals.append(
                        self._signal(index, "LONDON_FAKEOUT", "BEARISH", session, asian_range.high, timestamp, 75.0)
                    )
            if low < asian_range.low and close > asian_range.low and "ASIAN_LOW_SWEEP" not in seen:
                signals.append(
                    self._signal(index, "ASIAN_LOW_SWEEP", "BULLISH", session, asian_range.low, timestamp, 80.0)
                )
                seen.add("ASIAN_LOW_SWEEP")
                if session == "NEW_YORK":
                    signals.append(
                        self._signal(index, "NEW_YORK_REVERSAL", "BULLISH", session, asian_range.low, timestamp, 75.0)
                    )
        return self._merge_sweep_confirmation(signals, sweep_context)

    def _merge_sweep_confirmation(self, signals: list[SessionManipulationSignal], context: Any) -> list[SessionManipulationSignal]:
        sweeps = self._items(context, "sweeps")
        if not sweeps:
            return signals
        confirmed_directions = {
            self._get(sweep, "direction")
            for sweep in sweeps
            if self._get(sweep, "valid") is not False
        }
        return [
            signal.model_copy(
                update={"confidence": min(signal.confidence + 10.0, 100.0)}
            )
            if signal.direction in confirmed_directions
            else signal
            for signal in signals
        ]

    def _signal(
        self,
        index: int,
        signal_type: str,
        direction: str,
        session: str,
        level: float,
        timestamp: datetime,
        confidence: float,
    ) -> SessionManipulationSignal:
        return SessionManipulationSignal(
            signal_id=f"SES-{signal_type}-{timestamp.strftime('%Y%m%d%H%M')}-{index}",
            manipulation_type=signal_type,
            direction=direction,
            session_name=session,
            swept_level=level,
            confirmation=True,
            confidence=confidence,
            timestamp=timestamp,
        )

    def _active_session(self, value: time) -> str | None:
        if time(12, 0) <= value < time(21, 0):
            return "NEW_YORK"
        if time(7, 0) <= value < time(16, 0):
            return "LONDON"
        return None

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

    def _items(self, context: Any, key: str) -> list[Any]:
        if context is None:
            return []
        return list((context.get(key, []) if isinstance(context, dict) else getattr(context, key, [])) or [])

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
