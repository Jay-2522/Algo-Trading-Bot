from typing import Any

from backend.institutional_intelligence.setup_validator_models import SetupValidationRule


class SessionGatekeeper:
    def validate_session(self, entry_model: Any, session_context: Any) -> list[SetupValidationRule]:
        readiness = self._get(session_context, "trade_timing_readiness")
        score = float(self._get(session_context, "session_quality_score") or 0.0)
        killzone = self._get(session_context, "active_killzone")
        active = bool(self._get(killzone, "active_killzone"))
        liquidity = self._get(self._get(session_context, "liquidity_profile"), "liquidity_quality")
        rules = []
        if readiness == "AVOID_NEWS_WINDOW":
            rules.append(
                SetupValidationRule(
                    rule_name="NEWS_BLACKOUT_RESTRICTION",
                    category="NEWS",
                    passed=False,
                    score=0.0,
                    severity="CRITICAL",
                    reason="News blackout window prevents simulation eligibility.",
                )
            )
        if readiness == "AVOID_LOW_LIQUIDITY" or liquidity in {"LOW", "POOR"}:
            rules.append(
                SetupValidationRule(
                    rule_name="SESSION_LIQUIDITY_QUALITY",
                    category="SESSION",
                    passed=False,
                    score=min(score, 25.0),
                    severity="CRITICAL",
                    reason="Session liquidity is insufficient for institutional entry qualification.",
                )
            )
        elif readiness == "HIGH_QUALITY_WINDOW" and active:
            rules.append(
                SetupValidationRule(
                    rule_name="SESSION_KILLZONE_QUALITY",
                    category="SESSION",
                    passed=True,
                    score=max(score, 85.0),
                    severity="INFO",
                    reason="Active killzone and session quality support simulation timing.",
                )
            )
        else:
            rules.append(
                SetupValidationRule(
                    rule_name="SESSION_KILLZONE_QUALITY",
                    category="SESSION",
                    passed=False,
                    score=score,
                    severity="WARNING",
                    reason="Setup is outside a confirmed high-quality timing window.",
                )
            )
        return rules

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
