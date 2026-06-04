from backend.nifty50.nifty_execution_models import NIFTYExecutionIntent


class NIFTYOrderMapper:
    def map_to_broker_order(self, intent: NIFTYExecutionIntent, broker_id: str) -> dict:
        normalized = broker_id.strip().lower()
        common = {
            "symbol": intent.symbol,
            "exchange": intent.exchange,
            "transaction_type": intent.action,
            "quantity": intent.quantity,
            "order_type": intent.order_type,
            "product_type": intent.product_type,
            "placeholder": True,
            "api_call_enabled": False,
        }
        broker_templates = {
            "dhan": {"broker": "Dhan", "security_id_placeholder": "NIFTY50_INDEX"},
            "angel_one": {"broker": "Angel One", "symbol_token_placeholder": "NIFTY50_INDEX"},
            "fyers": {"broker": "Fyers", "symbol_placeholder": "NSE:NIFTY50-INDEX"},
            "upstox": {"broker": "Upstox", "instrument_key_placeholder": "NSE_INDEX|Nifty 50"},
            "zerodha": {"broker": "Zerodha", "tradingsymbol_placeholder": "NIFTY 50"},
        }
        return {**common, **broker_templates.get(normalized, {"broker": broker_id, "warning": "Broker template not recognized."})}
