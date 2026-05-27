import hmac
import os
from typing import Any


class TradingViewWebhookAuthenticator:
    """Validate TradingView webhook secrets without exposing secret values."""

    SECRET_FIELDS = ("secret", "webhook_secret", "token", "auth_token")

    def __init__(self, expected_secret: str | None = None) -> None:
        self.expected_secret = expected_secret if expected_secret is not None else os.getenv("TRADINGVIEW_WEBHOOK_SECRET")

    def validate_secret(self, secret: str | None) -> bool:
        if not self.expected_secret:
            return secret in {None, ""}
        if not secret:
            return False
        return hmac.compare_digest(str(secret), str(self.expected_secret))

    def authenticate_request(self, payload: dict[str, Any] | None) -> bool:
        payload = payload or {}
        provided_secret = None
        for field in self.SECRET_FIELDS:
            if field in payload:
                provided_secret = payload.get(field)
                break
        return self.validate_secret(provided_secret)
