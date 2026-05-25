from backend.institutional_intelligence.smc_models import StructureBias, SwingPoint


class StructureBiasAnalyzer:
    """Describe swing sequencing as bias, without converting bias into orders."""

    def analyze_bias(self, swings: list[SwingPoint]) -> StructureBias:
        highs = [swing.price for swing in swings if swing.type == "HIGH"]
        lows = [swing.price for swing in swings if swing.type == "LOW"]
        higher_highs, lower_highs = self._comparisons(highs)
        higher_lows, lower_lows = self._comparisons(lows)
        bullish = higher_highs > 0 and higher_lows > 0 and lower_highs == 0 and lower_lows == 0
        bearish = lower_highs > 0 and lower_lows > 0 and higher_highs == 0 and higher_lows == 0
        observations = higher_highs + higher_lows + lower_highs + lower_lows
        if bullish:
            bias = "BULLISH"
            directional = higher_highs + higher_lows
        elif bearish:
            bias = "BEARISH"
            directional = lower_highs + lower_lows
        elif observations >= 2:
            bias = "RANGING"
            directional = max(higher_highs + higher_lows, lower_highs + lower_lows)
        else:
            bias = "UNCLEAR"
            directional = 0
        confidence = round(directional / observations * 100, 2) if observations else 0.0
        return StructureBias(
            bias=bias,
            higher_highs=higher_highs,
            higher_lows=higher_lows,
            lower_highs=lower_highs,
            lower_lows=lower_lows,
            confidence=confidence,
        )

    def _comparisons(self, prices: list[float]) -> tuple[int, int]:
        higher = lower = 0
        for previous, current in zip(prices, prices[1:]):
            if current > previous:
                higher += 1
            elif current < previous:
                lower += 1
        return higher, lower
