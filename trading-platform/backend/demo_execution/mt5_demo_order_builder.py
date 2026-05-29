from typing import Any

from backend.execution_queue.execution_queue_models import ExecutionIntent


class MT5DemoOrderBuilder:
    """Build tiny EURUSD market order requests for guarded demo execution only."""

    MAX_LOT = 0.01
    ALLOWED_SYMBOL = "EURUSD"

    def __init__(self, mt5_module: Any = None) -> None:
        self.mt5 = mt5_module

    def build_market_order(self, intent: ExecutionIntent) -> dict[str, Any]:
        symbol = (intent.broker_symbol or intent.canonical_symbol or "").upper()
        action = str(intent.action or "").upper()
        if symbol != self.ALLOWED_SYMBOL:
            raise ValueError("Phase 5 Day 1 demo execution supports EURUSD only.")
        if action not in {"BUY", "SELL"}:
            raise ValueError("Phase 5 Day 1 demo execution supports BUY/SELL market orders only.")

        lot = min(float(intent.allocated_lot or 0.0), self.MAX_LOT)
        if lot <= 0:
            raise ValueError("Demo execution lot must be greater than zero.")

        order_type = self._order_type(action)
        price = self._market_price(symbol, action, intent.requested_price)
        return {
            "action": getattr(self.mt5, "TRADE_ACTION_DEAL", 1) if self.mt5 is not None else "TRADE_ACTION_DEAL",
            "symbol": symbol,
            "volume": round(lot, 2),
            "type": order_type,
            "price": price,
            "deviation": 10,
            "magic": 51001,
            "comment": "AI_BOT_DEMO_TEST",
            "type_time": getattr(self.mt5, "ORDER_TIME_GTC", 0) if self.mt5 is not None else "ORDER_TIME_GTC",
            "type_filling": getattr(self.mt5, "ORDER_FILLING_IOC", 1) if self.mt5 is not None else "ORDER_FILLING_IOC",
        }

    def _order_type(self, action: str):
        if self.mt5 is None:
            return f"ORDER_TYPE_{action}"
        return getattr(self.mt5, "ORDER_TYPE_BUY", 0) if action == "BUY" else getattr(self.mt5, "ORDER_TYPE_SELL", 1)

    def _market_price(self, symbol: str, action: str, requested_price: float | None) -> float:
        if self.mt5 is not None:
            try:
                tick = self.mt5.symbol_info_tick(symbol)
                if tick is not None:
                    price = getattr(tick, "ask", None) if action == "BUY" else getattr(tick, "bid", None)
                    if price:
                        return float(price)
            except Exception:
                pass
        return float(requested_price or 0.0)
