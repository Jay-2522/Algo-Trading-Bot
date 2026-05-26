from typing import Any

from backend.institutional_intelligence.setup_validator_models import SetupValidationRule


class RiskGatekeeper:
    def validate_risk(self, entry_model: Any, risk_context: Any = None) -> list[SetupValidationRule]:
        invalidation = self._number(entry_model, "invalidation_level")
        target = self._number(entry_model, "target_level")
        low = self._number(entry_model, "entry_zone_low")
        high = self._number(entry_model, "entry_zone_high")
        direction = self._get(entry_model, "direction")
        if invalidation is None or target is None or low is None or high is None:
            return [
                SetupValidationRule(
                    rule_name="DEFINED_RISK_GEOMETRY",
                    category="RISK",
                    passed=False,
                    score=0.0,
                    severity="CRITICAL",
                    reason="Entry, invalidation, and target levels must be defined.",
                )
            ]
        entry = (low + high) / 2.0
        risk = entry - invalidation if direction == "BULLISH" else invalidation - entry
        reward = target - entry if direction == "BULLISH" else entry - target
        rr = reward / risk if risk > 0 else 0.0
        geometry = SetupValidationRule(
            rule_name="RISK_REWARD_QUALITY",
            category="RISK",
            passed=rr >= 1.5,
            score=100.0 if rr >= 2.0 else 70.0 if rr >= 1.5 else 20.0,
            severity="INFO" if rr >= 1.5 else "CRITICAL",
            reason=f"Analytical reward-to-risk ratio is {rr:.2f}.",
        )
        status = self._get(risk_context, "overall_status")
        operational = SetupValidationRule(
            rule_name="RISK_CONTROL_STATUS",
            category="RISK",
            passed=status in {None, "OPERATIONAL"},
            score=100.0 if status in {None, "OPERATIONAL"} else 0.0,
            severity="INFO" if status in {None, "OPERATIONAL"} else "CRITICAL",
            reason="Risk controls are operational." if status in {None, "OPERATIONAL"} else "Risk controls block simulation eligibility.",
        )
        return [geometry, operational]

    def _number(self, value: Any, key: str) -> float | None:
        raw = self._get(value, key)
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
