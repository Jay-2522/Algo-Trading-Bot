from typing import Any


class SignalEligibilityValidator:
    """Reject strategy signals that are not safe to convert to execution intent."""

    MIN_CONFIDENCE = 70.0

    def validate(self, signal: Any) -> tuple[bool, str, list[str]]:
        action = str(self._get(signal, "action", "WAIT")).upper()
        confidence = float(self._get(signal, "confidence", 0.0) or 0.0)
        reasons: list[str] = []

        if action == "WAIT" or action not in {"BUY", "SELL"}:
            return False, "REJECTED_WAIT_SIGNAL", ["WAIT or non-BUY/SELL signals cannot be bridged."]
        if confidence < self.MIN_CONFIDENCE:
            return False, "REJECTED_LOW_CONFIDENCE", [f"Signal confidence {confidence} is below {self.MIN_CONFIDENCE}."]
        if bool(self._get(signal, "live_execution_enabled", False)) or bool(self._get_metadata(signal, "live_execution_enabled", False)):
            return False, "FAILED_SAFE", ["Unexpected live execution flag detected."]
        if bool(self._get(signal, "broker_execution_enabled", False)) or bool(self._get_metadata(signal, "broker_execution_enabled", False)):
            return False, "FAILED_SAFE", ["Unexpected broker execution flag detected."]
        if self._news_blocks(signal):
            return False, "REJECTED_NEWS_RISK", ["News risk context blocks strategy execution intent."]
        if self._regime_blocks(signal):
            return False, "REJECTED_REGIME", ["Market regime risk mode is NO_TRADE."]
        if str(self._get(signal, "trade_quality", "")).upper() == "NO_TRADE":
            return False, "REJECTED_REGIME", ["Trade quality is NO_TRADE."]
        if not bool(self._get(signal, "execution_allowed", False)):
            return False, "REJECTED_EXECUTION_NOT_ALLOWED", ["Signal execution_allowed is false."]

        return True, "APPROVED_FOR_QUEUE_PREVIEW", reasons

    def _news_blocks(self, signal: Any) -> bool:
        news_context = self._get(signal, "news_context", {}) or {}
        if isinstance(news_context, dict):
            return bool(news_context.get("high_impact_event_active")) or str(news_context.get("trade_action", "ALLOW")).upper() == "BLOCK"
        return bool(getattr(news_context, "high_impact_event_active", False)) or str(getattr(news_context, "trade_action", "ALLOW")).upper() == "BLOCK"

    def _regime_blocks(self, signal: Any) -> bool:
        regime_context = self._get(signal, "regime_context", None)
        if regime_context is None:
            return False
        if isinstance(regime_context, dict):
            return str(regime_context.get("risk_mode", "")).upper() == "NO_TRADE"
        return str(getattr(regime_context, "risk_mode", "")).upper() == "NO_TRADE"

    def _get_metadata(self, signal: Any, key: str, default: Any) -> Any:
        metadata = self._get(signal, "metadata", {}) or {}
        if isinstance(metadata, dict):
            return metadata.get(key, default)
        return default

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
