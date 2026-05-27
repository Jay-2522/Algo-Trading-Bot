from typing import Any

from backend.webhooks.tradingview_payload_validator import TradingViewPayloadValidator
from backend.webhooks.webhook_rate_limiter import WebhookRateLimiter
from backend.webhooks.webhook_replay_guard import WebhookReplayGuard
from backend.webhooks.webhook_security_models import WebhookSecurityEvent


class WebhookSecurityMonitor:
    """Combine replay, rate, and malformed payload checks into security events."""

    def __init__(
        self,
        replay_guard: WebhookReplayGuard | None = None,
        rate_limiter: WebhookRateLimiter | None = None,
        validator: TradingViewPayloadValidator | None = None,
    ) -> None:
        self.replay_guard = replay_guard or WebhookReplayGuard()
        self.rate_limiter = rate_limiter or WebhookRateLimiter()
        self.validator = validator or TradingViewPayloadValidator()

    def classify_request(self, payload: dict[str, Any] | None, source_ip: str | None) -> WebhookSecurityEvent:
        source = str(source_ip or "unknown")
        replay = self.replay_guard.validate_request(payload)
        rate = self.rate_limiter.validate_request(source)
        validation = self.validator.validate_payload(payload)

        reasons: list[str] = []
        reasons.extend(replay.reasons)
        reasons.extend(rate.warnings)
        if not validation["valid"]:
            reasons.extend(validation["issues"])

        event_type = "SAFE_REQUEST"
        severity = "LOW"
        blocked = False
        if not validation["valid"]:
            event_type = "INVALID_PAYLOAD"
            severity = "MEDIUM"
        if replay.duplicate_detected:
            event_type = "DUPLICATE_SIGNAL"
            severity = "MEDIUM"
        if replay.replay_detected:
            event_type = "REPLAY_ATTACK"
            severity = "HIGH"
        if rate.blocked:
            event_type = "RATE_LIMIT"
            severity = "HIGH"
        blocked = not replay.allowed or not rate.allowed
        if len(reasons) >= 4 and not blocked:
            event_type = "SUSPICIOUS_ACTIVITY"
            severity = "MEDIUM"

        return WebhookSecurityEvent(
            source_ip=source,
            fingerprint=replay.fingerprint,
            event_type=event_type,
            severity=severity,
            blocked=blocked,
            reasons=reasons,
        )
