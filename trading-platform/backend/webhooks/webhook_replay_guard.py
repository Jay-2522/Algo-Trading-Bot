from datetime import datetime, timedelta, timezone
from typing import Any

from backend.webhooks.webhook_request_fingerprint import WebhookRequestFingerprint
from backend.webhooks.webhook_security_models import WebhookReplayProtectionResult


class WebhookReplayGuard:
    """Detect duplicate fingerprints and replay attempts inside a bounded window."""

    def __init__(
        self,
        fingerprint_builder: WebhookRequestFingerprint | None = None,
        replay_window_seconds: int = 300,
        block_duplicates: bool = True,
    ) -> None:
        self.fingerprint_builder = fingerprint_builder or WebhookRequestFingerprint()
        self.replay_window_seconds = replay_window_seconds
        self.block_duplicates = block_duplicates
        self.seen: dict[str, datetime] = {}

    def validate_request(self, payload: dict[str, Any] | None) -> WebhookReplayProtectionResult:
        now = datetime.now(timezone.utc)
        self._prune(now)
        fingerprint = self.fingerprint_builder.build_fingerprint(payload)
        previous = self.seen.get(fingerprint)
        duplicate = previous is not None
        replay = duplicate and (now - previous).total_seconds() <= self.replay_window_seconds
        reasons: list[str] = []
        warnings: list[str] = []

        if duplicate:
            reasons.append("Duplicate webhook fingerprint detected.")
        if replay:
            reasons.append("Webhook replay attempt detected inside replay window.")
        allowed = not (self.block_duplicates and (duplicate or replay))
        if not allowed:
            warnings.append("Request blocked before webhook normalization.")
        self.seen[fingerprint] = now
        return WebhookReplayProtectionResult(
            allowed=allowed,
            duplicate_detected=duplicate,
            replay_detected=replay,
            fingerprint=fingerprint,
            reasons=reasons,
            warnings=warnings,
        )

    def _prune(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.replay_window_seconds)
        stale = [fingerprint for fingerprint, seen_at in self.seen.items() if seen_at < cutoff]
        for fingerprint in stale:
            self.seen.pop(fingerprint, None)
