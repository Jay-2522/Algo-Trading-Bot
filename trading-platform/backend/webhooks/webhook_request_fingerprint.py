import hashlib
import json
from typing import Any


class WebhookRequestFingerprint:
    """Build stable request fingerprints without including secrets."""

    FIELDS = ("symbol", "action", "timeframe", "timestamp", "strategy")

    def build_fingerprint(self, payload: dict[str, Any] | None) -> str:
        payload = payload or {}
        fingerprint_payload = {
            field: str(payload.get(field) or "").strip().upper()
            for field in self.FIELDS
        }
        encoded = json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
