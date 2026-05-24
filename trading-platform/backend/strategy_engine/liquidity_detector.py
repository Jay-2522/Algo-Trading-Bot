from typing import Any, Dict, List


class LiquidityDetector:
    """Detect simple equal-high and equal-low liquidity pools."""

    def __init__(self, tolerance_percent: float = 0.05) -> None:
        self.tolerance_percent = tolerance_percent

    def find_equal_highs(self, candles: list[Any]) -> List[Dict[str, Any]]:
        """Find highs clustered within a tight tolerance."""

        return self._find_equal_levels(candles, field="high", zone_type="equal_highs")

    def find_equal_lows(self, candles: list[Any]) -> List[Dict[str, Any]]:
        """Find lows clustered within a tight tolerance."""

        return self._find_equal_levels(candles, field="low", zone_type="equal_lows")

    def detect_liquidity_zones(self, candles: list[Any]) -> Dict[str, Any]:
        """Return structured liquidity zones for future strategy analysis."""

        equal_highs = self.find_equal_highs(candles)
        equal_lows = self.find_equal_lows(candles)
        return {
            "equal_highs": equal_highs,
            "equal_lows": equal_lows,
            "potential_stop_hunt_zones": equal_highs + equal_lows,
            "metadata": {
                "candles_analyzed": len(candles),
                "tolerance_percent": self.tolerance_percent,
            },
        }

    def _find_equal_levels(self, candles: list[Any], field: str, zone_type: str) -> List[Dict[str, Any]]:
        zones: List[Dict[str, Any]] = []
        if len(candles) < 2:
            return zones

        for index in range(1, len(candles)):
            previous = float(self._get_value(candles[index - 1], field))
            current = float(self._get_value(candles[index], field))
            tolerance = previous * (self.tolerance_percent / 100)

            if abs(current - previous) <= tolerance:
                zones.append(
                    {
                        "type": zone_type,
                        "level": round((previous + current) / 2, 5),
                        "start_index": index - 1,
                        "end_index": index,
                        "touches": 2,
                    }
                )

        return zones

    def _get_value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)

