from datetime import datetime
from typing import Any

from backend.replay.client_symbol_registry import ClientSymbolRegistry


class TradingViewPayloadValidator:
    """Validate TradingView alert payloads before normalization."""

    VALID_ACTIONS = {"BUY", "LONG", "SELL", "SHORT", "CLOSE", "EXIT", "ALERT", "ALERT_ONLY"}
    VALID_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}

    def __init__(self, symbol_registry: ClientSymbolRegistry | None = None) -> None:
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()

    def validate_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        issues: list[str] = []
        if not isinstance(payload, dict):
            return {"valid": False, "issues": ["Payload must be a JSON object."]}

        symbol = payload.get("symbol")
        action = str(payload.get("action") or "").strip().upper()
        timeframe = str(payload.get("timeframe") or "").strip().upper()

        if not symbol:
            issues.append("Missing required field: symbol.")
        elif not self.symbol_registry.is_supported(str(symbol)):
            issues.append(f"Unsupported symbol: {symbol}.")

        if not action:
            issues.append("Missing required field: action.")
        elif action not in self.VALID_ACTIONS:
            issues.append(f"Unsupported action: {action}.")

        if not timeframe:
            issues.append("Missing required field: timeframe.")
        elif timeframe not in self.VALID_TIMEFRAMES:
            issues.append(f"Unsupported timeframe: {timeframe}.")

        if "timestamp" in payload and payload.get("timestamp") not in {None, ""}:
            if self._parse_timestamp(payload.get("timestamp")) is None:
                issues.append("Invalid timestamp format.")

        if "price" in payload and payload.get("price") is not None:
            try:
                float(payload.get("price"))
            except Exception:
                issues.append("Invalid price value.")

        if "confidence" in payload and payload.get("confidence") is not None:
            try:
                confidence = float(payload.get("confidence"))
                if confidence < 0 or confidence > 100:
                    issues.append("Confidence must be between 0 and 100.")
            except Exception:
                issues.append("Invalid confidence value.")

        return {"valid": not issues, "issues": issues}

    def _parse_timestamp(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except Exception:
                return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None
        return None
