import math
from datetime import datetime, timezone

from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_tick_service import MT5TickService
from backend.streaming.stream_models import TickMessage


class TickStreamer:
    """Produce read-only MT5 ticks when connected and safe simulated ticks otherwise."""

    def __init__(self, connection_manager: MT5ConnectionManager | None = None) -> None:
        self.connection_manager = connection_manager or MT5ConnectionManager()
        self.tick_service = MT5TickService(self.connection_manager)
        self._sequences: dict[str, int] = {}

    def get_tick(self, symbol: str) -> TickMessage:
        normalized_symbol = self._normalize_symbol(symbol)
        try:
            tick = self.tick_service.get_latest_tick(normalized_symbol)
            if tick.bid is not None and tick.ask is not None:
                bid = float(tick.bid)
                ask = float(tick.ask)
                return TickMessage(
                    symbol=normalized_symbol,
                    bid=bid,
                    ask=ask,
                    spread=round(ask - bid, 8),
                    timestamp=tick.time or datetime.now(timezone.utc).isoformat(),
                    source="MT5_READ_ONLY",
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
