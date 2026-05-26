from typing import Any

from backend.institutional_intelligence.setup_validator_models import SetupValidationRule


class ConfluenceGatekeeper:
    def validate_confluence(self, entry_model: Any, confluence_context: Any) -> SetupValidationRule:
        model_direction = self._get(entry_model, "direction")
        context = self._get(confluence_context, "confluence_score")
        direction = self._get(context, "dominant_direction")
        score = float(self._get(context, "overall_score") or 0.0)
        confidence = float(self._get(context, "confidence") or 0.0)
        if direction == "CONFLICTED" or direction in {"BULLISH", "BEARISH"} and direction != model_direction:
            return SetupValidationRule(
                rule_name="INSTITUTIONAL_CONFLUENCE",
                category="CONFLUENCE",
                passed=False,
                score=0.0,
                severity="CRITICAL",
                reason="Institutional confluence contradicts the candidate direction.",
            )
        if direction == model_direction and score >= 75.0 and confidence >= 65.0:
            return SetupValidationRule(
                rule_name="INSTITUTIONAL_CONFLUENCE",
                category="CONFLUENCE",
                passed=True,
                score=score,
                severity="INFO",
                reason="Strong same-direction institutional confluence confirms the setup.",
            )
        if direction == model_direction and score >= 55.0:
            return SetupValidationRule(
                rule_name="INSTITUTIONAL_CONFLUENCE",
                category="CONFLUENCE",
                passed=False,
                score=score,
                severity="WARNING",
                reason="Directional confluence exists but has not reached approval quality.",
            )
        return SetupValidationRule(
            rule_name="INSTITUTIONAL_CONFLUENCE",
            category="CONFLUENCE",
            passed=False,
            score=score,
            severity="CRITICAL",
            reason="Institutional confluence is too weak for simulation eligibility.",
        )

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
