from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper
from backend.webhooks.webhook_models import NormalizedTradingSignal
from backend.webhooks.webhook_orchestration_models import WebhookBrokerRoutingPreview


class WebhookBrokerRoutingPreviewBuilder:
    """Build broker routing previews without creating orders or execution payloads."""

    FOREX_CFD_BROKERS = ["STARTRADER", "FXPRO", "VANTAGE"]
    INDIAN_FUTURE_BROKERS = ["ZERODHA_FUTURE", "ANGELONE_FUTURE", "UPSTOX_FUTURE"]

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        mapper: BrokerSymbolMapper | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.mapper = mapper or BrokerSymbolMapper(self.registry)

    def build_preview(self, signal: NormalizedTradingSignal) -> WebhookBrokerRoutingPreview:
        if signal.market_type in {"FOREX", "COMMODITY_CFD"}:
            targets = list(self.FOREX_CFD_BROKERS)
        elif signal.market_type == "INDIAN_INDEX":
            targets = list(self.INDIAN_FUTURE_BROKERS)
        else:
            targets = []

        supported: list[str] = []
        unsupported: list[str] = []
        broker_symbol_map: dict[str, str | None] = {}
        for broker_id in targets:
            if broker_id.endswith("_FUTURE"):
                unsupported.append(broker_id)
                broker_symbol_map[broker_id] = None
                continue
            mapping = self.mapper.map_symbol(broker_id, signal.canonical_symbol)
            broker_symbol_map[broker_id] = mapping.broker_symbol
            if mapping.supported:
                supported.append(broker_id)
            else:
                unsupported.append(broker_id)

        routing_ready = bool(supported) and signal.action in {"BUY", "SELL", "CLOSE", "ALERT_ONLY"}
        if signal.canonical_symbol == "NIFTY50":
            message = "NIFTY50 routing is preview-only until Zerodha/AngelOne/Upstox integration is implemented."
        elif routing_ready:
            message = "Broker routing preview is ready for simulation review only."
        else:
            message = "No supported broker route available for this signal."

        return WebhookBrokerRoutingPreview(
            canonical_symbol=signal.canonical_symbol,
            broker_targets=targets,
            supported_brokers=supported,
            unsupported_brokers=unsupported,
            broker_symbol_map=broker_symbol_map,
            routing_ready=routing_ready,
            message=message,
        )
