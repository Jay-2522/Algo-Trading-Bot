from typing import Any

from backend.ai_engine.ai_models import DecisionExplanation
from backend.ai_engine.decision_engine import DecisionEngine
from backend.ai_engine.decision_logger import DecisionLogger


class AIOrchestrator:
    """Coordinate advisory scoring, explanation, and optional persistence."""

    def __init__(
        self,
        decision_engine: DecisionEngine | None = None,
        decision_logger: DecisionLogger | None = None,
    ) -> None:
        self.decision_engine = decision_engine or DecisionEngine()
        self.decision_logger = decision_logger or DecisionLogger()

    def generate_full_analysis(
        self,
        symbol: str,
        strategy_context: dict[str, Any] | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        package = self.decision_engine.evaluate_setup(symbol, strategy_context)
        decision = package["decision"]
        explanation = self._explain(package)
        persistence = (
            self.decision_logger.log_decision(decision, explanation, package["context"])
            if persist
            else {"persisted": False, "message": "Persistence disabled for this evaluation."}
        )
        return {
            "decision": decision,
            "explanation": explanation,
            "signal_score": package["signal_score"],
            "regime": package["regime"],
            "persistence": persistence,
        }

    def _explain(self, package: dict[str, Any]) -> DecisionExplanation:
        decision = package["decision"]
        score = package["signal_score"]
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []

        if score.risk_score >= 80:
            strengths.append("Risk controls are currently operational.")
        else:
            warnings.append("Risk controls are blocking setup approval.")
        if score.session_score >= 70:
            strengths.append("Session conditions support liquidity.")
        else:
            weaknesses.append("Session liquidity is limited.")
        if score.trend_score < 60:
            weaknesses.append("Directional trend alignment is weak.")
        if decision.regime.regime in {"VOLATILE", "LOW_LIQUIDITY", "NEWS_RISK"}:
            warnings.append(f"Regime classified as {decision.regime.regime}.")

        return DecisionExplanation(
            summary=f"{decision.symbol} advisory decision: {decision.action} at {decision.confidence}% confidence.",
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
        )
