from typing import Any

from backend.institutional_intelligence.alignment_gatekeeper import AlignmentGatekeeper
from backend.institutional_intelligence.confluence_gatekeeper import ConfluenceGatekeeper
from backend.institutional_intelligence.risk_gatekeeper import RiskGatekeeper
from backend.institutional_intelligence.session_gatekeeper import SessionGatekeeper
from backend.institutional_intelligence.setup_validator_models import SetupValidationResult, SetupValidationRule


class SetupValidatorEngine:
    def __init__(
        self,
        alignment_gatekeeper: AlignmentGatekeeper | None = None,
        session_gatekeeper: SessionGatekeeper | None = None,
        confluence_gatekeeper: ConfluenceGatekeeper | None = None,
        risk_gatekeeper: RiskGatekeeper | None = None,
    ) -> None:
        self.alignment_gatekeeper = alignment_gatekeeper or AlignmentGatekeeper()
        self.session_gatekeeper = session_gatekeeper or SessionGatekeeper()
        self.confluence_gatekeeper = confluence_gatekeeper or ConfluenceGatekeeper()
        self.risk_gatekeeper = risk_gatekeeper or RiskGatekeeper()

    def validate_setup(
        self,
        entry_model: Any,
        confluence_context: Any = None,
        alignment_context: Any = None,
        session_context: Any = None,
        risk_context: Any = None,
    ) -> SetupValidationResult:
        rules = [
            self.alignment_gatekeeper.validate_alignment(entry_model, alignment_context),
            *self.session_gatekeeper.validate_session(entry_model, session_context),
            self.confluence_gatekeeper.validate_confluence(entry_model, confluence_context),
            *self.risk_gatekeeper.validate_risk(entry_model, risk_context),
            self._validate_structure(entry_model),
        ]
        score = round(sum(rule.score for rule in rules) / len(rules), 2) if rules else 0.0
        critical = [rule.reason for rule in rules if not rule.passed and rule.severity == "CRITICAL"]
        warnings = [rule.reason for rule in rules if not rule.passed and rule.severity == "WARNING"]
        passed = [rule.reason for rule in rules if rule.passed]
        model_readiness = self._get(entry_model, "readiness")
        if critical or model_readiness in {"AVOID", "NO_SETUP"}:
            readiness = "REJECTED"
        elif all(rule.passed for rule in rules):
            readiness = "APPROVED"
        elif score >= 65.0:
            readiness = "CONDITIONAL"
        else:
            readiness = "WAIT"
        confidence = max(score - (len(critical) * 20.0) - (len(warnings) * 7.5), 0.0)
        return SetupValidationResult(
            symbol=self._get(entry_model, "symbol") or "",
            timeframe=self._get(entry_model, "timeframe") or "",
            model_type=self._get(entry_model, "model_type") or "UNKNOWN",
            direction=self._get(entry_model, "direction") or "NEUTRAL",
            approved_for_simulation=readiness == "APPROVED",
            overall_score=score,
            confidence=round(min(confidence, 100.0), 2),
            readiness=readiness,
            rules=rules,
            strengths=passed,
            weaknesses=warnings,
            warnings=list(self._get(entry_model, "warnings") or []),
            rejection_reasons=critical,
            approval_reasons=passed if readiness == "APPROVED" else [],
        )

    def _validate_structure(self, model: Any) -> SetupValidationRule:
        model_type = self._get(model, "model_type")
        direction = self._get(model, "direction")
        zone_low = self._get(model, "entry_zone_low")
        zone_high = self._get(model, "entry_zone_high")
        valid = (
            model_type != "NO_TRADE"
            and direction in {"BULLISH", "BEARISH"}
            and zone_low is not None
            and zone_high is not None
            and float(zone_high) > float(zone_low)
        )
        return SetupValidationRule(
            rule_name="STRUCTURAL_INTEGRITY",
            category="STRUCTURE",
            passed=valid,
            score=100.0 if valid else 0.0,
            severity="INFO" if valid else "CRITICAL",
            reason="Entry model contains valid directional zone structure." if valid else "Entry model lacks valid actionable structure.",
        )

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
