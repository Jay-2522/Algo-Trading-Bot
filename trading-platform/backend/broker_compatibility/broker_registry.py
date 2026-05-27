from backend.broker_compatibility.broker_models import SupportedBroker


class BrokerRegistry:
    """Static broker registry for simulation-only compatibility checks."""

    def __init__(self) -> None:
        self._brokers = {
            "STARTRADER": SupportedBroker(
                broker_id="STARTRADER",
                display_name="STARTRADER",
                platform="MT5",
                supported_account_modes=["DEMO", "LIVE_DISABLED", "READ_ONLY"],
                supported_markets=["FOREX", "COMMODITY_CFD"],
                notes="Compatibility metadata only. Requires broker symbol verification in MT5 demo terminal.",
            ),
            "FXPRO": SupportedBroker(
                broker_id="FXPRO",
                display_name="FxPro",
                platform="MT4_MT5",
                supported_account_modes=["DEMO", "LIVE_DISABLED", "READ_ONLY"],
                supported_markets=["FOREX", "COMMODITY_CFD"],
                notes="Compatibility metadata only. Requires broker symbol verification in MT4/MT5 demo terminal.",
            ),
            "VANTAGE": SupportedBroker(
                broker_id="VANTAGE",
                display_name="Vantage",
                platform="MT4_MT5",
                supported_account_modes=["DEMO", "LIVE_DISABLED", "READ_ONLY"],
                supported_markets=["FOREX", "COMMODITY_CFD"],
                notes="Compatibility metadata only. Requires broker symbol verification in MT4/MT5 demo terminal.",
            ),
        }

    def list_brokers(self) -> list[SupportedBroker]:
        return list(self._brokers.values())

    def get_broker(self, broker_id: str) -> SupportedBroker | None:
        return self._brokers.get(str(broker_id or "").strip().upper())

    def is_supported_broker(self, broker_id: str) -> bool:
        return self.get_broker(broker_id) is not None
