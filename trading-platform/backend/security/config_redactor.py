from typing import Any


class ConfigRedactor:
    """Redact sensitive configuration values before API display or logs."""

    SENSITIVE_PARTS = ("password", "secret", "token", "api_key", "apikey", "login", "account", "private")

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [self.redact_dict(item) if isinstance(item, dict) else self.redact_value(key, item) for item in value]
            else:
                redacted[key] = self.redact_value(key, value)
        return redacted

    def redact_value(self, key: str, value: Any) -> Any:
        lowered = str(key).lower()
        if any(part in lowered for part in self.SENSITIVE_PARTS):
            return "********"
        return value
