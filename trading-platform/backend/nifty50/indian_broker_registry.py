from backend.nifty50.nifty_models import IndianBrokerCandidate


class IndianBrokerRegistry:
    def __init__(self) -> None:
        self._brokers = [
            IndianBrokerCandidate(
                broker_id="dhan",
                broker_name="Dhan",
                api_supported=True,
                market_data_supported=True,
                order_execution_supported=False,
                paper_trading_supported=True,
                recommended=True,
                warnings=["Final broker selection is still configurable.", "Credentials are not configured."],
            ),
            IndianBrokerCandidate(
                broker_id="angel_one",
                broker_name="Angel One",
                api_supported=True,
                market_data_supported=True,
                order_execution_supported=False,
                paper_trading_supported=True,
                recommended=True,
                warnings=["Final broker selection is still configurable.", "Credentials are not configured."],
            ),
            IndianBrokerCandidate(
                broker_id="fyers",
                broker_name="Fyers",
                api_supported=True,
                market_data_supported=True,
                order_execution_supported=False,
                paper_trading_supported=True,
                warnings=["Candidate only; not selected."],
            ),
            IndianBrokerCandidate(
                broker_id="upstox",
                broker_name="Upstox",
                api_supported=True,
                market_data_supported=True,
                order_execution_supported=False,
                paper_trading_supported=True,
                warnings=["Candidate only; not selected."],
            ),
            IndianBrokerCandidate(
                broker_id="zerodha",
                broker_name="Zerodha",
                api_supported=True,
                market_data_supported=True,
                order_execution_supported=False,
                paper_trading_supported=False,
                warnings=["Candidate only; account/API suitability must be validated."],
            ),
        ]

    def list_brokers(self) -> list[IndianBrokerCandidate]:
        return self._brokers

    def get_broker(self, broker_id: str) -> IndianBrokerCandidate | None:
        normalized = broker_id.strip().lower()
        return next((broker for broker in self._brokers if broker.broker_id == normalized), None)

    def get_recommended_broker(self) -> dict:
        recommended = [broker for broker in self._brokers if broker.recommended]
        return {
            "recommended_brokers": [broker.model_dump(mode="json") for broker in recommended],
            "recommendation": "Dhan or Angel One",
            "reason": "Both are suitable candidates for Indian market automation with easier API access. Final broker choice remains configurable.",
            "selected_broker": None,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_selection_guidance(self) -> dict:
        return {
            "required_before_selection": [
                "Confirm client broker account availability.",
                "Confirm API access and paper/demo support.",
                "Confirm NSE market data permissions.",
                "Validate authentication flow in a sandbox-only phase.",
            ],
            "do_not_configure_yet": ["API keys", "live order permissions", "real broker execution"],
        }
