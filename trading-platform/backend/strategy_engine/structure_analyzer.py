from typing import Any, Dict


class StructureAnalyzer:
    """Detect simple BOS and CHOCH behavior from recent candle structure."""

    def detect_bos(self, candles: list[Any]) -> Dict[str, Any]:
        """Detect a basic break of structure using recent swing extremes."""

        if len(candles) < 5:
            return {"detected": False, "direction": "none", "level": None, "reason": "insufficient_candles"}

        previous_candles = candles[:-1]
        latest = candles[-1]
        previous_high = max(float(self._get_value(candle, "high")) for candle in previous_candles)
        previous_low = min(float(self._get_value(candle, "low")) for candle in previous_candles)
        latest_close = float(self._get_value(latest, "close"))

        if latest_close > previous_high:
            return {"detected": True, "direction": "bullish", "level": previous_high, "reason": "close_above_prior_high"}
        if latest_close < previous_low:
            return {"detected": True, "direction": "bearish", "level": previous_low, "reason": "close_below_prior_low"}
        return {"detected": False, "direction": "none", "level": None, "reason": "no_structure_break"}

    def detect_choch(self, candles: list[Any]) -> Dict[str, Any]:
        """Detect a basic change of character from recent directional bias."""

        if len(candles) < 6:
            return {"detected": False, "direction": "none", "level": None, "reason": "insufficient_candles"}

        previous_closes = [float(self._get_value(candle, "close")) for candle in candles[-6:-1]]
        latest_close = float(self._get_value(candles[-1], "close"))
        previous_bias = "bullish" if previous_closes[-1] > previous_closes[0] else "bearish"
        recent_high = max(float(self._get_value(candle, "high")) for candle in candles[-6:-1])
        recent_low = min(float(self._get_value(candle, "low")) for candle in candles[-6:-1])

        if previous_bias == "bullish" and latest_close < recent_low:
            return {"detected": True, "direction": "bearish", "level": recent_low, "reason": "bullish_bias_failed"}
        if previous_bias == "bearish" and latest_close > recent_high:
            return {"detected": True, "direction": "bullish", "level": recent_high, "reason": "bearish_bias_failed"}
        return {"detected": False, "direction": "none", "level": None, "reason": "no_character_change"}

    def analyze_market_structure(self, candles: list[Any]) -> Dict[str, Any]:
        """Return BOS, CHOCH, and simple continuation/reversal context."""

        bos = self.detect_bos(candles)
        choch = self.detect_choch(candles)

        if choch["detected"]:
            behavior = "potential_reversal"
        elif bos["detected"]:
            behavior = "trend_continuation"
        else:
            behavior = "range_or_developing_structure"

        return {
            "bos": bos,
            "choch": choch,
            "behavior": behavior,
            "metadata": {"candles_analyzed": len(candles)},
        }

    def _get_value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)

