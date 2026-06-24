import math
from datetime import datetime, timezone

from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService
from backend.streaming.stream_models import TickMessage


class TickStreamer:
    """Produce read-only MT5 ticks when connected and safe simulated ticks otherwise."""

    def __init__(self, market_data_service: MT5MarketDataService | None = None) -> None:
        self.market_data_service = market_data_service or MT5MarketDataService()
        self._sequences: dict[str, int] = {}

    def get_tick(self, symbol: str) -> TickMessage:
        normalized_symbol = self._normalize_symbol(symbol)
        try:
            tick = self.market_data_service.get_symbol_tick(normalized_symbol)
            bid_value = tick.get("bid") if isinstance(tick, dict) else None
            ask_value = tick.get("ask") if isinstance(tick, dict) else None
            if bid_value is not None and ask_value is not None:
                bid = float(bid_value)
                ask = float(ask_value)
                return TickMessage(
                    symbol=normalized_symbol,
                    bid=bid,
                    ask=ask,
                    spread=round(ask - bid, 8),
                    timestamp=str(tick.get("timestamp") or datetime.now(timezone.utc).isoformat()) if isinstance(tick, dict) else datetime.now(timezone.utc).isoformat(),
                    source=str(tick.get("source") or "MT5_READ_ONLY") if isinstance(tick, dict) else "MT5_READ_ONLY",
                )
        except Exception:
            pass
        return self.get_simulated_tick(normalized_symbol)

    def get_simulated_tick(self, symbol: str) -> TickMessage:
        normalized_symbol = self._normalize_symbol(symbol)
        sequence = self._sequences.get(normalized_symbol, 0) + 1
        self._sequences[normalized_symbol] = sequence
        base = 2300.0 if normalized_symbol == "XAUUSD" else 100.0
        midpoint = base + math.sin(sequence / 5.0) * (base * 0.00012)
        spread = 0.08 if normalized_symbol == "XAUUSD" else 0.0002
        return TickMessage(
            symbol=normalized_symbol,
            bid=round(midpoint - spread / 2, 5),
            ask=round(midpoint + spread / 2, 5),
            spread=spread,
            source="SIMULATION_FALLBACK",
        )

    def _normalize_symbol(self, symbol: str) -> str:
        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")
        return normalized_symbol
