from datetime import datetime, timezone
from typing import Any

from backend.replay.client_symbol_registry import ClientSymbolRegistry
from backend.webhooks.tradingview_signal_classifier import TradingViewSignalClassifier
from backend.webhooks.webhook_models import NormalizedTradingSignal


class TradingViewSignalNormalizer:
    """Convert TradingView alert JSON into orchestration-ready signal objects."""

    ACTION_MAP = {
        "BUY": "BUY",
        "LONG": "BUY",
        "SELL": "SELL",
        "SHORT": "SELL",
        "CLOSE": "CLOSE",
        "EXIT": "CLOSE",
        "ALERT": "ALERT_ONLY",
        "ALERT_ONLY": "ALERT_ONLY",
    }

    def __init__(
        self,
        symbol_registry: ClientSymbolRegistry | None = None,
        classifier: TradingViewSignalClassifier | None = None,
    ) -> None:
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()
        self.classifier = classifier or TradingViewSignalClassifier(self.symbol_registry)

    def normalize(self, payload: dict[str, Any]) -> NormalizedTradingSignal:
        resolution = self.symbol_registry.resolve_symbol(str(payload.get("symbol") or ""))
        canonical = resolution.canonical_symbol or str(payload.get("symbol") or "").strip().upper()
        action = self.ACTION_MAP.get(str(payload.get("action") or "").strip().upper(), "INVALID")
        timeframe = str(payload.get("timeframe") or "M15").strip().upper()
        market_type = self.classifier.classify(canonical)
        timestamp = self._parse_timestamp(payload.get("timestamp")) or datetime.now(timezone.utc)
        confidence = self._to_float(payload.get("confidence"))
        price = self._to_float(payload.get("price"))
        broker_targets = self._broker_targets(market_type)
        ready = bool(resolution.supported and action != "INVALID")

        return NormalizedTradingSignal(
            canonical_symbol=canonical,
            market_type=market_type,
            action=action,
            timeframe=timeframe,
            strategy_name=payload.get("strategy") or payload.get("strategy_name"),
            signal_price=price,
            confidence=confidence,
            broker_targets=broker_targets,
            routing_ready=ready,
            orchestration_ready=ready,
            simulation_only=True,
            live_execution_enabled=False,
            timestamp=timestamp,
        )

    def _broker_targets(self, market_type: str) -> list[str]:
        if market_type in {"FOREX", "COMMODITY_CFD"}:
            return ["STARTRADER", "FXPRO", "VANTAGE"]
        if market_type == "INDIAN_INDEX":
            return ["ZERODHA_FUTURE", "ANGELONE_FUTURE", "UPSTOX_FUTURE"]
        return []

    def _parse_timestamp(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc)
            except Exception:
                return None
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except Exception:
                return None
        return None

    def _to_float(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None
