class IndianBrokerAdapterBase:
    broker_id = "generic"
    broker_name = "Generic Indian Broker Adapter"

    def get_status(self) -> dict:
        return {
            "broker_id": self.broker_id,
            "broker_name": self.broker_name,
            "status": "PLACEHOLDER",
            "api_connected": False,
            "market_data_connected": False,
            "order_execution_enabled": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_market_data(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "data_source": "PLACEHOLDER",
            "placeholder": True,
            "message": "Live broker market data is not connected.",
        }

    def place_order(self, order_request: dict) -> dict:
        return {
            "status": "ORDER_EXECUTION_DISABLED",
            "accepted": False,
            "order_request": order_request,
            "reason": "NIFTY50 broker execution is not implemented in Phase 12 Day 1.",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_positions(self) -> dict:
        return {"positions": [], "placeholder": True, "message": "Broker positions are not connected."}

    def get_account_status(self) -> dict:
        return {"status": "PLACEHOLDER", "account_connected": False, "message": "Broker account is not connected."}
