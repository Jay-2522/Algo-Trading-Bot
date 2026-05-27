from backend.institutional_intelligence.smc_service import SMCService
from backend.webhooks.webhook_models import NormalizedTradingSignal
from backend.webhooks.webhook_orchestration_models import WebhookInstitutionalContextCheck


class WebhookInstitutionalContextChecker:
    """Compare a TradingView signal with available institutional dashboard context."""

    def __init__(self, smc_service: SMCService | None = None) -> None:
        self.smc_service = smc_service or SMCService()

    def check_signal_context(self, signal: NormalizedTradingSignal) -> WebhookInstitutionalContextCheck:
        try:
            dashboard = self.smc_service.analyze_dashboard_context(signal.canonical_symbol, signal.timeframe)
            bias_value = str(getattr(dashboard.institutional_bias, "value", "UNKNOWN") or "UNKNOWN").upper()
            recommendation = getattr(dashboard.final_recommendation, "action", "MONITOR")
            confidence = getattr(dashboard.final_recommendation, "confidence", None)
            aligned = self._aligned(signal.action, bias_value, str(recommendation))
            issues = []
            if aligned is False:
                issues.append("TradingView signal direction conflicts with institutional dashboard context.")
            return WebhookInstitutionalContextCheck(
                canonical_symbol=signal.canonical_symbol,
                institutional_bias=bias_value,
                dashboard_status=str(dashboard.dashboard_status),
                recommendation=str(recommendation),
                confidence=confidence,
                aligned_with_signal=aligned,
                issues=issues,
            )
        except Exception as exc:
            return WebhookInstitutionalContextCheck(
                canonical_symbol=signal.canonical_symbol,
                institutional_bias="UNKNOWN",
                dashboard_status="PARTIAL",
                recommendation="MONITOR",
                confidence=None,
                aligned_with_signal=None,
                issues=[f"Institutional context unavailable: {exc.__class__.__name__}."],
            )

    def _aligned(self, action: str, bias_value: str, recommendation: str) -> bool | None:
        if action not in {"BUY", "SELL"}:
            return None
        if recommendation in {"AVOID", "REVIEW_SYSTEM"}:
            return False
        if "BULL" in bias_value:
            return action == "BUY"
        if "BEAR" in bias_value:
            return action == "SELL"
        if "CONFLICT" in bias_value:
            return False
        return None
