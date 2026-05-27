from datetime import datetime, timedelta, timezone

from backend.webhooks.webhook_security_models import WebhookRateLimitResult


class WebhookRateLimiter:
    """In-memory source-IP rate limiter with localhost whitelist."""

    LOCALHOST = {"127.0.0.1", "::1", "localhost", "testclient"}

    def __init__(self, limit: int = 30, window_seconds: int = 60, whitelist_localhost: bool = True) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.whitelist_localhost = whitelist_localhost
        self.requests: dict[str, list[datetime]] = {}

    def validate_request(self, source_ip: str | None) -> WebhookRateLimitResult:
        source = str(source_ip or "unknown").lower()
        if self.whitelist_localhost and source in self.LOCALHOST:
            return WebhookRateLimitResult(
                allowed=True,
                request_count=0,
                limit=self.limit,
                blocked=False,
                reset_window_seconds=self.window_seconds,
                warnings=["Localhost source is whitelisted for development verification."],
            )

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        entries = [entry for entry in self.requests.get(source, []) if entry >= cutoff]
        entries.append(now)
        self.requests[source] = entries
        blocked = len(entries) > self.limit
        return WebhookRateLimitResult(
            allowed=not blocked,
            request_count=len(entries),
            limit=self.limit,
            blocked=blocked,
            reset_window_seconds=self.window_seconds,
            warnings=["Rate limit exceeded."] if blocked else [],
        )
