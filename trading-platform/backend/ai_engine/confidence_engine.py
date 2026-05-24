from backend.ai_engine.ai_models import SignalScore


class ConfidenceEngine:
    """Calculate confidence from aligned, normalized quality factors."""

    WEIGHTS = {
        "trend_score": 0.20,
        "liquidity_score": 0.15,
        "structure_score": 0.20,
        "session_score": 0.10,
        "volatility_score": 0.10,
        "spread_score": 0.10,
        "risk_score": 0.15,
    }

    def calculate_confidence(self, signal_score: SignalScore) -> float:
        weighted_score = sum(
            getattr(signal_score, factor) * weight
            for factor, weight in self.WEIGHTS.items()
        )
        alignment_scores = [
            signal_score.trend_score,
            signal_score.structure_score,
            signal_score.liquidity_score,
        ]
        if min(alignment_scores) >= 70:
            weighted_score += 5
        if signal_score.volatility_score < 40:
            weighted_score -= 10
        if signal_score.spread_score < 40:
            weighted_score -= 10
        if signal_score.risk_score < 50:
            weighted_score -= 20
        return round(max(0.0, min(100.0, weighted_score)), 2)

