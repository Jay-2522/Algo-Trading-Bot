from typing import Any

from backend.webhooks.tradingview_payload_validator import TradingViewPayloadValidator
from backend.webhooks.tradingview_signal_normalizer import TradingViewSignalNormalizer
from backend.webhooks.tradingview_webhook_auth import TradingViewWebhookAuthenticator
from backend.webhooks.webhook_event_store import WebhookEventStore
from backend.webhooks.webhook_models import NormalizedTradingSignal, WebhookEventRecord


class TradingViewWebhookService:
    """Ingest, validate, normalize, and store TradingView webhook signals."""

    def __init__(
        self,
        authenticator: TradingViewWebhookAuthenticator | None = None,
        validator: TradingViewPayloadValidator | None = None,
        normalizer: TradingViewSignalNormalizer | None = None,
        store: WebhookEventStore | None = None,
    ) -> None:
        self.authenticator = authenticator or TradingViewWebhookAuthenticator()
        self.validator = validator or TradingViewPayloadValidator()
        self.normalizer = normalizer or TradingViewSignalNormalizer()
        self.store = store or WebhookEventStore()

    def process_webhook(self, payload: dict[str, Any] | None) -> NormalizedTradingSignal:
        payload = payload or {}
        authenticated = self.authenticator.authenticate_request(payload)
        event = WebhookEventRecord(
            authenticated=authenticated,
            valid=False,
            symbol=str(payload.get("symbol")) if payload.get("symbol") is not None else None,
            action=str(payload.get("action")) if payload.get("action") is not None else None,
            processing_status="RECEIVED",
        )
        if not authenticated:
            event.processing_status = "REJECTED"
            event.issues.append("Webhook authentication failed.")
            self.store.store_event(event)
            raise PermissionError("Webhook authentication failed.")

        validation = self.validator.validate_payload(payload)
        if not validation["valid"]:
            event.processing_status = "REJECTED"
            event.issues.extend(validation["issues"])
            self.store.store_event(event)
            raise ValueError("; ".join(validation["issues"]))

        event.processing_status = "VALIDATED"
        event.valid = True
        signal = self.normalizer.normalize(payload)
        event.symbol = signal.canonical_symbol
        event.action = signal.action
        event.processing_status = "NORMALIZED"
        self.store.store_event(event)
        return signal

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "operational",
            "mode": "TRADINGVIEW_WEBHOOK_INGESTION_ONLY",
            "supported_symbols": ["EURUSD", "XAUUSD", "NIFTY50"],
            "simulation_only": True,
            "live_execution_enabled": False,
        }
