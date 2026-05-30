from datetime import datetime, timezone
from typing import Any

from backend.strategy_engine.swing_point_detector import SwingPointDetector


class BosChochDetector:
    """Detect BOS and CHOCH from swing structure and latest close."""

    def __init__(self, swing_detector: SwingPointDetector | None = None) -> None:
        self.swing_detector = swing_detector or SwingPointDetector()

    def detect(self, candles: list[Any] | None = None, liquidity_context: Any | None = None) -> dict[str, Any]:
        swings = self.swing_detector.detect_swings(candles)
        result = {
            **swings,
            "bos_direction": "NONE",
            "choch_direction": "NONE",
            "structure_bias": "NEUTRAL",
            "structure_shift_detected": False,
            "break_level": None,
            "break_price": None,
            "break_candle_time": None,
            "post_sweep_confirmation": False,
            "confirmation_reason": "No BOS or CHOCH confirmation detected.",
        }
        if not candles or not swings["latest_swing_high"] or not swings["latest_swing_low"]:
            return result

        try:
            latest = candles[-1]
            latest_close = float(self._value(latest, "close"))
            latest_time = self._time(latest).isoformat()
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            result["warnings"].append(f"Invalid candle data supplied for BOS/CHOCH detection: {exc}")
            return result

        latest_high = float(swings["latest_swing_high"]["price"])
        latest_low = float(swings["latest_swing_low"]["price"])
        prior_bias = self._prior_bias(candles[:-1])

        if latest_close > latest_high:
            result.update(
                self._bullish_break(latest_high, latest_close, latest_time, prior_bias, liquidity_context)
            )
        elif latest_close < latest_low:
            result.update(
                self._bearish_break(latest_low, latest_close, latest_time, prior_bias, liquidity_context)
            )
        return result

    def _bullish_break(
        self,
        break_level: float,
        break_price: float,
        break_time: str,
        prior_bias: str,
        liquidity_context: Any | None,
    ) -> dict[str, Any]:
        choch = prior_bias == "BEARISH"
        post_sweep = self._liquidity_direction(liquidity_context) == "SELL_SIDE_SWEEP"
        direction_key = "choch_direction" if choch else "bos_direction"
        direction_value = "BULLISH_CHOCH" if choch else "BULLISH_BOS"
        return {
            direction_key: direction_value,
            "structure_bias": "BULLISH",
            "structure_shift_detected": True,
            "break_level": round(break_level, 5),
            "break_price": round(break_price, 5),
            "break_candle_time": break_time,
            "post_sweep_confirmation": post_sweep,
            "confirmation_reason": (
                f"Close broke above swing high {round(break_level, 5)} after prior {prior_bias.lower()} context."
            ),
        }

    def _bearish_break(
        self,
        break_level: float,
        break_price: float,
        break_time: str,
        prior_bias: str,
        liquidity_context: Any | None,
    ) -> dict[str, Any]:
        choch = prior_bias == "BULLISH"
        post_sweep = self._liquidity_direction(liquidity_context) == "BUY_SIDE_SWEEP"
        direction_key = "choch_direction" if choch else "bos_direction"
        direction_value = "BEARISH_CHOCH" if choch else "BEARISH_BOS"
        return {
            direction_key: direction_value,
            "structure_bias": "BEARISH",
            "structure_shift_detected": True,
            "break_level": round(break_level, 5),
            "break_price": round(break_price, 5),
            "break_candle_time": break_time,
            "post_sweep_confirmation": post_sweep,
            "confirmation_reason": (
                f"Close broke below swing low {round(break_level, 5)} after prior {prior_bias.lower()} context."
            ),
        }

    def _prior_bias(self, candles: list[Any]) -> str:
        if len(candles) < 4:
            return "NEUTRAL"
        closes = [float(self._value(candle, "close")) for candle in candles[-6:]]
        change = closes[-1] - closes[0]
        if change > 0.5:
            return "BULLISH"
        if change < -0.5:
            return "BEARISH"
        return "NEUTRAL"

    def _liquidity_direction(self, liquidity_context: Any | None) -> str:
        if liquidity_context is None:
            return "NONE"
        if isinstance(liquidity_context, dict):
            return str(liquidity_context.get("sweep_direction", "NONE"))
        return str(getattr(liquidity_context, "sweep_direction", "NONE"))

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
