from datetime import datetime, timezone
from typing import Any

from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import EURUSDStructureContext


class EURUSDStructureEngine:
    """Detect EURUSD swing structure, BOS, and CHOCH using forex pip tolerance."""

    TOLERANCE = 0.0002

    def __init__(self, session_service: MarketSessionService | None = None, tolerance: float = TOLERANCE) -> None:
        self.session_service = session_service or MarketSessionService()
        self.tolerance = tolerance

    def detect(self, candles: list[Any] | None = None, liquidity_context: Any | None = None) -> EURUSDStructureContext:
        if not candles:
            return EURUSDStructureContext(
                symbol="EURUSD",
                warnings=["No candle data supplied; EURUSD BOS/CHOCH context is a safe placeholder."],
            )

        try:
            normalized = [self._normalize(candle) for candle in candles]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return EURUSDStructureContext(
                symbol="EURUSD",
                warnings=[f"Invalid candle data supplied; EURUSD structure context is a safe placeholder: {exc}"],
            )

        swing_highs = self._swing_points(normalized, "high")
        swing_lows = self._swing_points(normalized, "low")
        latest_high = swing_highs[-1] if swing_highs else None
        latest_low = swing_lows[-1] if swing_lows else None
        latest = normalized[-1]
        prior_bias = self._prior_bias(swing_highs, swing_lows)

        bos_direction = "NONE"
        choch_direction = "NONE"
        break_level = None
        break_price = None
        if latest_high and latest["close"] > float(latest_high["level"]) + self.tolerance:
            break_level = float(latest_high["level"])
            break_price = latest["close"]
            if prior_bias == "BEARISH":
                choch_direction = "BULLISH_CHOCH"
            else:
                bos_direction = "BULLISH_BOS"
        elif latest_low and latest["close"] < float(latest_low["level"]) - self.tolerance:
            break_level = float(latest_low["level"])
            break_price = latest["close"]
            if prior_bias == "BULLISH":
                choch_direction = "BEARISH_CHOCH"
            else:
                bos_direction = "BEARISH_BOS"

        structure_bias = self._structure_bias(bos_direction, choch_direction, prior_bias)
        post_sweep = self._post_sweep_confirmation(liquidity_context, bos_direction, choch_direction)
        context = EURUSDStructureContext(
            symbol="EURUSD",
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            latest_swing_high=latest_high,
            latest_swing_low=latest_low,
            bos_detected=bos_direction != "NONE",
            choch_detected=choch_direction != "NONE",
            bos_direction=bos_direction,
            choch_direction=choch_direction,
            structure_shift_detected=bos_direction != "NONE" or choch_direction != "NONE",
            break_level=round(break_level, 5) if break_level is not None else None,
            break_price=round(break_price, 5) if break_price is not None else None,
            break_candle_time=latest["time"].isoformat(),
            post_sweep_confirmation=post_sweep,
            structure_bias=structure_bias,
            confirmation_reason=self._confirmation_reason(bos_direction, choch_direction, post_sweep),
            warnings=[] if swing_highs and swing_lows else ["Insufficient clean swing structure for strong EURUSD confirmation."],
        )
        strength, confidence, quality = self._score(context, latest)
        context.structure_strength = strength
        context.confidence = confidence
        context.structure_quality = quality
        return context

    def _swing_points(self, candles: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        reference_end = len(candles) - 1
        for index in range(1, max(reference_end, 1)):
            previous_value = candles[index - 1][field]
            current_value = candles[index][field]
            next_value = candles[index + 1][field]
            if field == "high":
                is_swing = current_value >= previous_value + self.tolerance and current_value >= next_value + self.tolerance
                point_type = "SWING_HIGH"
            else:
                is_swing = current_value <= previous_value - self.tolerance and current_value <= next_value - self.tolerance
                point_type = "SWING_LOW"
            if is_swing:
                points.append(
                    {
                        "index": index,
                        "time": candles[index]["time"].isoformat(),
                        "level": round(current_value, 5),
                        "type": point_type,
                    }
                )
        return points

    def _prior_bias(self, swing_highs: list[dict[str, Any]], swing_lows: list[dict[str, Any]]) -> str:
        high_bias = "NEUTRAL"
        low_bias = "NEUTRAL"
        if len(swing_highs) >= 2:
            high_bias = "BULLISH" if swing_highs[-1]["level"] > swing_highs[-2]["level"] else "BEARISH"
        if len(swing_lows) >= 2:
            low_bias = "BULLISH" if swing_lows[-1]["level"] > swing_lows[-2]["level"] else "BEARISH"
        if high_bias == low_bias and high_bias != "NEUTRAL":
            return high_bias
        if high_bias != "NEUTRAL":
            return high_bias
        if low_bias != "NEUTRAL":
            return low_bias
        return "NEUTRAL"

    def _structure_bias(self, bos_direction: str, choch_direction: str, prior_bias: str) -> str:
        if bos_direction == "BULLISH_BOS" or choch_direction == "BULLISH_CHOCH":
            return "BULLISH"
        if bos_direction == "BEARISH_BOS" or choch_direction == "BEARISH_CHOCH":
            return "BEARISH"
        return prior_bias if prior_bias in {"BULLISH", "BEARISH"} else "NEUTRAL"

    def _post_sweep_confirmation(self, liquidity_context: Any | None, bos_direction: str, choch_direction: str) -> bool:
        sweep_direction = self._get(liquidity_context, "sweep_direction", "NONE")
        bullish_shift = bos_direction == "BULLISH_BOS" or choch_direction == "BULLISH_CHOCH"
        bearish_shift = bos_direction == "BEARISH_BOS" or choch_direction == "BEARISH_CHOCH"
        return (sweep_direction == "SELL_SIDE_SWEEP" and bullish_shift) or (
            sweep_direction == "BUY_SIDE_SWEEP" and bearish_shift
        )

    def _score(self, context: EURUSDStructureContext, latest: dict[str, Any]) -> tuple[float, float, str]:
        score = 0.0
        if context.bos_detected:
            score += 30.0
        if context.choch_detected:
            score += 35.0
        if context.post_sweep_confirmation:
            score += 20.0
        if self.session_service.get_session_context(latest["time"]).session_quality == "HIGH":
            score += 10.0
        if context.swing_highs and context.swing_lows:
            score += 5.0
        confidence = min(score, 100.0)
        if confidence >= 75:
            quality = "HIGH"
        elif confidence >= 50:
            quality = "MEDIUM"
        elif confidence >= 25:
            quality = "LOW"
        else:
            quality = "NONE"
        return round(score, 2), round(confidence, 2), quality

    def _confirmation_reason(self, bos_direction: str, choch_direction: str, post_sweep: bool) -> str:
        shift = choch_direction if choch_direction != "NONE" else bos_direction
        if shift == "NONE":
            return "No EURUSD BOS or CHOCH confirmation detected."
        if post_sweep:
            return f"{shift} confirmed after EURUSD liquidity sweep."
        return f"{shift} detected without post-sweep confirmation."

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

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
