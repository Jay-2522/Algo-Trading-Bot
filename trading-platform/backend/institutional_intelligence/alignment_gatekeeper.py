from typing import Any

from backend.institutional_intelligence.setup_validator_models import SetupValidationRule


class AlignmentGatekeeper:
    def validate_alignment(self, entry_model: Any, alignment_context: Any) -> SetupValidationRule:
        direction = self._get(entry_model, "direction")
        aligned = self._get(alignment_context, "overall_direction")
        quality = self._get(alignment_context, "alignment_quality")
        score = float(self._get(alignment_context, "alignment_score") or 0.0)
        if self._get(entry_model, "model_type") == "NO_TRADE":
            return SetupValidationRule(
                rule_name="ENTRY_MODEL_ACTIONABILITY",
                category="ALIGNMENT",
                passed=False,
                score=0.0,
                severity="CRITICAL",
                reason="No-trade entry models cannot be approved for simulation.",
            )
        if aligned == "CONFLICTED" or (aligned in {"BULLISH", "BEARISH"} and aligned != direction):
            return SetupValidationRule(
                rule_name="HIGHER_TIMEFRAME_ALIGNMENT",
                category="ALIGNMENT",
                passed=False,
                score=0.0,
                severity="CRITICAL",
                reason="Candidate direction conflicts with higher-timeframe institutional flow.",
            )
        if quality == "FULLY_ALIGNED" and aligned == direction:
            return SetupValidationRule(
                rule_name="HIGHER_TIMEFRAME_ALIGNMENT",
                category="ALIGNMENT",
                passed=True,
                score=max(score, 90.0),
                severity="INFO",
                reason="Multi-timeframe direction is fully aligned with the candidate.",
            )
        if aligned == direction:
            return SetupValidationRule(
                rule_name="HIGHER_TIMEFRAME_ALIGNMENT",
                category="ALIGNMENT",
                passed=True,
                score=max(score, 65.0),
                severity="INFO",
                reason="Top-down institutional direction supports the candidate.",
            )
        return SetupValidationRule(
            rule_name="HIGHER_TIMEFRAME_ALIGNMENT",
            category="ALIGNMENT",
            passed=False,
            score=35.0,
            severity="WARNING",
            reason="Higher-timeframe confirmation is not yet directional.",
        )

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
