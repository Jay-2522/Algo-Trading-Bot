from backend.nifty50.nifty_risk_models import NIFTYRiskDecision
from backend.nifty50.nifty_strategy_models import NIFTYStrategySnapshot


class NIFTYRiskEngine:
    def evaluate(self, snapshot: NIFTYStrategySnapshot) -> NIFTYRiskDecision:
        rejection_reasons: list[str] = []
        warnings = ["Execution layer is missing; execution_allowed remains false."]

        if snapshot.confidence < 70:
            rejection_reasons.append("Confidence below 70.")
        if snapshot.strategy_bias == "NEUTRAL":
            rejection_reasons.append("Strategy bias is neutral.")
        if snapshot.regime == "UNKNOWN":
            rejection_reasons.append("Market regime is unknown.")
        if snapshot.placeholder:
            rejection_reasons.append("No market data available.")

        # Explicit hard guards for this phase.
        live_execution_enabled = False
        broker_execution_enabled = False
        if live_execution_enabled:
            rejection_reasons.append("Unexpected live execution flag enabled.")
        if broker_execution_enabled:
            rejection_reasons.append("Unexpected broker execution flag enabled.")

        analysis_approved = (
            snapshot.confidence >= 70
            and snapshot.strategy_bias in {"BULLISH", "BEARISH"}
            and snapshot.regime != "UNKNOWN"
            and not snapshot.placeholder
        )
        approved = analysis_approved and not rejection_reasons
        quality = self._quality(snapshot.confidence, approved)
        risk_level = self._risk_level(snapshot.confidence, approved)
        return NIFTYRiskDecision(
            strategy_bias=snapshot.strategy_bias,
            confidence=snapshot.confidence,
            approved=approved,
            trade_quality=quality,
            risk_level=risk_level,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
        )

    def _quality(self, confidence: float, approved: bool) -> str:
        if not approved:
            return "NO_TRADE"
        if confidence >= 90:
            return "A_PLUS"
        if confidence >= 80:
            return "A"
        if confidence >= 70:
            return "B"
        if confidence >= 60:
            return "C"
        return "NO_TRADE"

    def _risk_level(self, confidence: float, approved: bool) -> str:
        if not approved:
            return "BLOCKED"
        if confidence >= 85:
            return "LOW"
        if confidence >= 75:
            return "MEDIUM"
        return "HIGH"
