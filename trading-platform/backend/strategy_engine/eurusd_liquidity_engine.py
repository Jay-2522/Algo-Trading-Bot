from datetime import datetime, timezone
from typing import Any

from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import EURUSDLiquidityContext


class EURUSDLiquidityEngine:
    """Detect EURUSD liquidity sweeps with pip-sized tolerance."""

    TOLERANCE = 0.0002

    def __init__(self, session_service: MarketSessionService | None = None, tolerance: float = TOLERANCE) -> None:
        self.session_service = session_service or MarketSessionService()
        self.tolerance = tolerance

    def detect(self, candles: list[Any] | None = None) -> EURUSDLiquidityContext:
        if not candles:
            return EURUSDLiquidityContext(
                symbol="EURUSD",
                warnings=["No candle data supplied; EURUSD liquidity context is a safe placeholder."],
            )

        try:
            normalized = [self._normalize(candle) for candle in candles]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return EURUSDLiquidityContext(
                symbol="EURUSD",
                warnings=[f"Invalid candle data supplied; EURUSD liquidity context is a safe placeholder: {exc}"],
            )

        latest = normalized[-1]
        levels = self._levels(normalized)
        equal_highs = self._equal_levels(normalized, "high")
        equal_lows = self._equal_levels(normalized, "low")
        liquidity_pools = [
            {"type": "EQUAL_HIGHS", "level": item["level"], "touches": item["touches"], "importance": 20}
            for item in equal_highs
        ] + [
            {"type": "EQUAL_LOWS", "level": item["level"], "touches": item["touches"], "importance": 20}
            for item in equal_lows
        ]
        candidates = self._sweep_candidates(levels, equal_highs, equal_lows, latest)
        active = max(candidates, key=lambda item: item["importance"], default=None)
        session_context = self.session_service.get_session_context(latest["time"])

        context = EURUSDLiquidityContext(
            symbol="EURUSD",
            asian_high=levels["asian_high"],
            asian_low=levels["asian_low"],
            previous_day_high=levels["previous_day_high"],
            previous_day_low=levels["previous_day_low"],
            equal_highs=equal_highs,
            equal_lows=equal_lows,
            liquidity_pools=liquidity_pools,
            swept_asian_high=any(item["type"] == "ASIAN_HIGH" for item in candidates),
            swept_asian_low=any(item["type"] == "ASIAN_LOW" for item in candidates),
            swept_previous_high=any(item["type"] == "PREVIOUS_DAY_HIGH" for item in candidates),
            swept_previous_low=any(item["type"] == "PREVIOUS_DAY_LOW" for item in candidates),
            active_sweep_level=active["type"] if active else None,
            sweep_price=round(latest["high"] if active and active["direction"] == "BUY_SIDE_SWEEP" else latest["low"], 5) if active else None,
            rejection_detected=active is not None,
            rejection_candle_type=self._rejection_type(latest, active["level"], active["direction"]) if active else "NONE",
            session_alignment=session_context.session_quality == "HIGH",
            sweep_direction=active["direction"] if active else "NONE",
        )
        strength, confidence, quality = self._score(context)
        context.sweep_strength = strength
        context.confidence = confidence
        context.sweep_quality = quality
        return context

    def _levels(self, candles: list[dict[str, Any]]) -> dict[str, float | None]:
        reference = candles[:-1] if len(candles) > 1 else candles
        asian = [candle for candle in reference if 0 <= candle["time"].hour < 7]
        previous_day = self._previous_day_candles(reference)
        return {
            "asian_high": round(max((candle["high"] for candle in asian), default=None), 5) if asian else None,
            "asian_low": round(min((candle["low"] for candle in asian), default=None), 5) if asian else None,
            "previous_day_high": round(max((candle["high"] for candle in previous_day), default=None), 5) if previous_day else None,
            "previous_day_low": round(min((candle["low"] for candle in previous_day), default=None), 5) if previous_day else None,
        }

    def _previous_day_candles(self, candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candles:
            return []
        latest_date = candles[-1]["time"].date()
        previous_dates = sorted({candle["time"].date() for candle in candles if candle["time"].date() < latest_date})
        if not previous_dates:
            return []
        previous_date = previous_dates[-1]
        return [candle for candle in candles if candle["time"].date() == previous_date]

    def _equal_levels(self, candles: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
        reference = candles[:-1] if len(candles) > 1 else candles
        levels: list[dict[str, Any]] = []
        for index, candle in enumerate(reference):
            value = candle[field]
            touches = [
                other
                for other in reference
                if abs(other[field] - value) <= self.tolerance
            ]
            if len(touches) < 2:
                continue
            level = round(sum(item[field] for item in touches) / len(touches), 5)
            if any(abs(existing["level"] - level) <= self.tolerance for existing in levels):
                continue
            levels.append(
                {
                    "level": level,
                    "touches": len(touches),
                    "tolerance": self.tolerance,
                    "type": "EQUAL_HIGHS" if field == "high" else "EQUAL_LOWS",
                }
            )
        return levels

    def _sweep_candidates(
        self,
        levels: dict[str, float | None],
        equal_highs: list[dict[str, Any]],
        equal_lows: list[dict[str, Any]],
        latest: dict[str, Any],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        high_levels = [
            ("ASIAN_HIGH", levels["asian_high"], 30),
            ("PREVIOUS_DAY_HIGH", levels["previous_day_high"], 35),
        ]
        low_levels = [
            ("ASIAN_LOW", levels["asian_low"], 30),
            ("PREVIOUS_DAY_LOW", levels["previous_day_low"], 35),
        ]
        for level_type, level, importance in high_levels:
            if level is not None and latest["high"] > level + self.tolerance and latest["close"] < level:
                candidates.append({"type": level_type, "level": level, "importance": importance, "direction": "BUY_SIDE_SWEEP"})
        for level_type, level, importance in low_levels:
            if level is not None and latest["low"] < level - self.tolerance and latest["close"] > level:
                candidates.append({"type": level_type, "level": level, "importance": importance, "direction": "SELL_SIDE_SWEEP"})
        for pool in equal_highs:
            level = float(pool["level"])
            if latest["high"] > level + self.tolerance and latest["close"] < level:
                candidates.append({"type": "EQUAL_HIGHS", "level": level, "importance": 25, "direction": "BUY_SIDE_SWEEP"})
        for pool in equal_lows:
            level = float(pool["level"])
            if latest["low"] < level - self.tolerance and latest["close"] > level:
                candidates.append({"type": "EQUAL_LOWS", "level": level, "importance": 25, "direction": "SELL_SIDE_SWEEP"})
        return candidates

    def _score(self, context: EURUSDLiquidityContext) -> tuple[float, float, str]:
        if context.sweep_direction == "NONE":
            return 0.0, 0.0, "NONE"
        strength = 35.0
        if context.active_sweep_level in {"PREVIOUS_DAY_HIGH", "PREVIOUS_DAY_LOW"}:
            strength += 20.0
        if context.active_sweep_level in {"ASIAN_HIGH", "ASIAN_LOW"}:
            strength += 15.0
        if context.rejection_detected:
            strength += 20.0
        if context.session_alignment:
            strength += 15.0
        confidence = min(strength, 100.0)
        if confidence >= 75:
            quality = "HIGH"
        elif confidence >= 50:
            quality = "MEDIUM"
        else:
            quality = "LOW"
        return round(strength, 2), round(confidence, 2), quality

    def _rejection_type(self, candle: dict[str, Any], level: float, direction: str) -> str:
        body = abs(candle["close"] - candle["open"]) or 0.00001
        upper_wick = candle["high"] - max(candle["open"], candle["close"])
        lower_wick = min(candle["open"], candle["close"]) - candle["low"]
        if direction == "BUY_SIDE_SWEEP" and upper_wick >= body * 1.5:
            return "PIN_BAR"
        if direction == "SELL_SIDE_SWEEP" and lower_wick >= body * 1.5:
            return "PIN_BAR"
        if direction == "BUY_SIDE_SWEEP" and candle["close"] < level:
            return "STRONG_CLOSE_BACK_INSIDE"
        if direction == "SELL_SIDE_SWEEP" and candle["close"] > level:
            return "STRONG_CLOSE_BACK_INSIDE"
        return "NONE"

    def _normalize(self, candle: Any) -> dict[str, Any]:
        return {
            "time": self._time(self._field(candle, "timestamp") if self._has_field(candle, "timestamp") else self._field(candle, "time")),
            "open": float(self._field(candle, "open")),
            "high": float(self._field(candle, "high")),
            "low": float(self._field(candle, "low")),
            "close": float(self._field(candle, "close")),
        }

    def _time(self, raw: Any) -> datetime:
        if isinstance(raw, datetime):
            return raw.replace(tzinfo=timezone.utc) if raw.tzinfo is None else raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _has_field(self, candle: Any, field: str) -> bool:
        return field in candle if isinstance(candle, dict) else hasattr(candle, field)

    def _field(self, candle: Any, field: str) -> Any:
        return candle[field] if isinstance(candle, dict) else getattr(candle, field)
