from datetime import datetime, timedelta, timezone
from typing import Any


class LiquidityLevelBuilder:
    """Build reusable XAUUSD liquidity levels from supplied candles."""

    def __init__(self, equal_level_tolerance: float = 0.25) -> None:
        self.equal_level_tolerance = equal_level_tolerance

    def build_levels(self, symbol: str = "XAUUSD", candles: list[Any] | None = None) -> dict[str, Any]:
        if not candles:
            return {
                "symbol": symbol,
                "asian_high": None,
                "asian_low": None,
                "previous_day_high": None,
                "previous_day_low": None,
                "equal_highs": [],
                "equal_lows": [],
                "liquidity_pools": [],
                "warnings": ["No candle data supplied; liquidity levels are a safe placeholder."],
            }

        try:
            latest_time = self._time(candles[-1])
            normalized = [
                {
                    "time": self._time(candle),
                    "open": float(self._value(candle, "open")),
                    "high": float(self._value(candle, "high")),
                    "low": float(self._value(candle, "low")),
                    "close": float(self._value(candle, "close")),
                    "volume": float(self._optional_value(candle, "volume", self._optional_value(candle, "tick_volume", 0.0))),
                }
                for candle in candles
            ]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return {
                "symbol": symbol,
                "asian_high": None,
                "asian_low": None,
                "previous_day_high": None,
                "previous_day_low": None,
                "equal_highs": [],
                "equal_lows": [],
                "liquidity_pools": [],
                "warnings": [f"Invalid candle data supplied; liquidity levels are a safe placeholder: {exc}"],
            }

        asian_candles = [
            candle for candle in normalized if candle["time"].date() == latest_time.date() and 0 <= candle["time"].hour < 7
        ]
        previous_day = latest_time.date() - timedelta(days=1)
        previous_day_candles = [candle for candle in normalized if candle["time"].date() == previous_day]

        asian_high = self._max_value(asian_candles, "high")
        asian_low = self._min_value(asian_candles, "low")
        previous_day_high = self._max_value(previous_day_candles, "high")
        previous_day_low = self._min_value(previous_day_candles, "low")
        equal_highs = self._equal_levels(normalized, "high", "EQUAL_HIGHS")
        equal_lows = self._equal_levels(normalized, "low", "EQUAL_LOWS")

        liquidity_pools = []
        if asian_high is not None:
            liquidity_pools.append({"type": "ASIAN_HIGH", "level": asian_high, "side": "BUY_SIDE", "importance": 25})
        if asian_low is not None:
            liquidity_pools.append({"type": "ASIAN_LOW", "level": asian_low, "side": "SELL_SIDE", "importance": 25})
        if previous_day_high is not None:
            liquidity_pools.append({"type": "PREVIOUS_DAY_HIGH", "level": previous_day_high, "side": "BUY_SIDE", "importance": 30})
        if previous_day_low is not None:
            liquidity_pools.append({"type": "PREVIOUS_DAY_LOW", "level": previous_day_low, "side": "SELL_SIDE", "importance": 30})
        liquidity_pools.extend(equal_highs)
        liquidity_pools.extend(equal_lows)

        warnings: list[str] = []
        if asian_high is None or asian_low is None:
            warnings.append("Asian high/low unavailable from supplied candles.")
        if previous_day_high is None or previous_day_low is None:
            warnings.append("Previous day high/low unavailable from supplied candles.")

        return {
            "symbol": symbol,
            "asian_high": asian_high,
            "asian_low": asian_low,
            "previous_day_high": previous_day_high,
            "previous_day_low": previous_day_low,
            "equal_highs": equal_highs,
            "equal_lows": equal_lows,
            "liquidity_pools": liquidity_pools,
            "warnings": warnings,
        }

    def _equal_levels(self, candles: list[dict[str, Any]], field: str, level_type: str) -> list[dict[str, Any]]:
        clusters: list[dict[str, Any]] = []
        for index, candle in enumerate(candles):
            level = candle[field]
            touches = [
                other_index
                for other_index, other in enumerate(candles)
                if other_index != index and abs(other[field] - level) <= self.equal_level_tolerance
            ]
            if len(touches) < 1:
                continue
            cluster_indexes = sorted({index, *touches})
            if any(set(cluster_indexes) == set(existing["indexes"]) for existing in clusters):
                continue
            values = [candles[item][field] for item in cluster_indexes]
            side = "BUY_SIDE" if field == "high" else "SELL_SIDE"
            clusters.append(
                {
                    "type": level_type,
                    "level": round(sum(values) / len(values), 5),
                    "side": side,
                    "touches": len(cluster_indexes),
                    "indexes": cluster_indexes,
                    "importance": 20,
                }
            )
        return clusters

    def _max_value(self, candles: list[dict[str, Any]], field: str) -> float | None:
        if not candles:
            return None
        return round(max(candle[field] for candle in candles), 5)

    def _min_value(self, candles: list[dict[str, Any]], field: str) -> float | None:
        if not candles:
            return None
        return round(min(candle[field] for candle in candles), 5)

    def _time(self, candle: Any) -> datetime:
        raw = self._value(candle, "timestamp") if self._has_field(candle, "timestamp") else self._value(candle, "time")
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                return raw.replace(tzinfo=timezone.utc)
            return raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _optional_value(self, candle: Any, field: str, default: Any) -> Any:
        if self._has_field(candle, field):
            return self._value(candle, field)
        return default

    def _has_field(self, candle: Any, field: str) -> bool:
        if isinstance(candle, dict):
            return field in candle
        return hasattr(candle, field)

    def _value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)
