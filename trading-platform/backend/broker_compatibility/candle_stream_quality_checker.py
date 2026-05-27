from backend.broker_compatibility.canonical_candle_models import CanonicalCandle


class CandleStreamQualityChecker:
    """Classify canonical candle and feed quality for AI-ready market data."""

    def classify_candle_quality(self, candle: CanonicalCandle) -> str:
        issues = list(candle.issues)
        if candle.open is None or candle.high is None or candle.low is None or candle.close is None:
            issues.append("Missing OHLC price data.")
        else:
            if candle.high < candle.low:
                issues.append("Invalid OHLC range.")
            if not (candle.low <= candle.open <= candle.high):
                issues.append("Open price outside range.")
            if not (candle.low <= candle.close <= candle.high):
                issues.append("Close price outside range.")
        if issues:
            return "INVALID"
        if candle.source == "SIMULATION_FALLBACK":
            return "WARNING"
        return "GOOD"

    def classify_feed_quality(self, candles: list[CanonicalCandle]) -> str:
        if not candles:
            return "UNAVAILABLE"
        qualities = [self.classify_candle_quality(candle) for candle in candles]
        if all(quality == "INVALID" for quality in qualities):
            return "INVALID"
        if any(quality == "INVALID" for quality in qualities):
            return "WARNING"
        if len(candles) < 10:
            return "WARNING"
        if any(quality == "WARNING" for quality in qualities):
            return "WARNING"
        return "GOOD"
