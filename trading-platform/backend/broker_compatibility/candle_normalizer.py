from datetime import datetime, timezone
from typing import Any

from backend.broker_compatibility.canonical_candle_models import CanonicalCandle
from backend.replay.symbol_normalizer import SymbolNormalizer


class CandleNormalizer:
    """Normalize broker or fallback OHLC records into canonical candles."""

    def __init__(self, normalizer: SymbolNormalizer | None = None) -> None:
        self.normalizer = normalizer or SymbolNormalizer()

    def normalize_candle(self, raw_candle: Any, symbol: str, broker_id: str, timeframe: str) -> CanonicalCandle:
        issues: list[str] = []
        canonical = self.normalizer.normalize(symbol)
        timestamp = self._parse_timestamp(self._read(raw_candle, "timestamp", self._read(raw_candle, "time")))
        if timestamp is None:
            issues.append("Missing or invalid candle timestamp.")
            timestamp = datetime.now(timezone.utc)

        open_price = self._to_float(self._read(raw_candle, "open"))
        high = self._to_float(self._read(raw_candle, "high"))
        low = self._to_float(self._read(raw_candle, "low"))
        close = self._to_float(self._read(raw_candle, "close"))
        volume = self._to_float(self._read(raw_candle, "volume", self._read(raw_candle, "tick_volume", 0)))
        source = self._read(raw_candle, "source", "SIMULATION_FALLBACK")
        if source not in {"MT5_READ_ONLY", "SIMULATION_FALLBACK"}:
            source = "SIMULATION_FALLBACK"

        if None in {open_price, high, low, close}:
            issues.append("Missing OHLC price data.")
        else:
            if high < low:
                issues.append("Invalid OHLC range: high is below low.")
            if not (low <= open_price <= high):
                issues.append("Open price is outside candle range.")
            if not (low <= close <= high):
                issues.append("Close price is outside candle range.")

        usable = not issues
        quality = "GOOD" if usable and source == "MT5_READ_ONLY" else "WARNING" if usable else "INVALID"
        return CanonicalCandle(
            canonical_symbol=canonical,
            broker_id=str(broker_id or "").strip().upper(),
            timeframe=str(timeframe or "").strip().upper(),
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source=source,
            usable=usable,
            quality=quality,
            issues=issues,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _read(self, raw: Any, key: str, default: Any = None) -> Any:
        if isinstance(raw, dict):
            return raw.get(key, default)
        try:
            return raw[key]
        except Exception:
            return getattr(raw, key, default)

    def _parse_timestamp(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except Exception:
                return None
        return None

    def _to_float(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None
