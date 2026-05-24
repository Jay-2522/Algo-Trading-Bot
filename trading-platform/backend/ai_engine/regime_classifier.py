from backend.ai_engine.ai_models import MarketRegime


class RegimeClassifier:
    """Classify market regime from normalized quality measurements."""

    def classify_market_regime(
        self,
        trend_strength: float,
        volatility: str,
        spread: float,
        liquidity: float,
        session_name: str,
    ) -> MarketRegime:
        volatility_level = volatility.upper()
        liquidity_quality = "HIGH" if liquidity >= 70 else "NORMAL" if liquidity >= 45 else "LOW"

        if volatility_level in {"HIGH", "EXTREME"}:
            regime = "VOLATILE"
        elif liquidity < 35 or session_name == "Closed":
            regime = "LOW_LIQUIDITY"
        elif trend_strength >= 70:
            regime = "TRENDING"
        else:
            regime = "RANGING"

        classification_confidence = 80.0 if regime != "RANGING" else 65.0
        if spread > 30:
            classification_confidence = max(classification_confidence - 15, 0)

        return MarketRegime(
            regime=regime,
            volatility_level=volatility_level,
            liquidity_quality=liquidity_quality,
            trend_strength=round(max(0, min(100, trend_strength)), 2),
            confidence=classification_confidence,
        )

