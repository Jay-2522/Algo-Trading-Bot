from datetime import datetime, timezone
import math

from backend.broker_compatibility.broker_observation_models import BrokerSymbolSnapshot
from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper


class BrokerSymbolSnapshotter:
    """Read-only broker symbol snapshotter with deterministic fallback data."""

    def __init__(self, mapper: BrokerSymbolMapper | None = None, mt5_client=None, allow_simulation_fallback: bool = True) -> None:
        self.mapper = mapper or BrokerSymbolMapper()
        self.mt5_client = mt5_client
        self.allow_simulation_fallback = allow_simulation_fallback

    def snapshot_symbol(self, broker_id: str, canonical_symbol: str) -> BrokerSymbolSnapshot:
        mapping = self.mapper.map_symbol(broker_id, canonical_symbol)
        if not mapping.supported:
            return BrokerSymbolSnapshot(
                broker_id=str(broker_id or "").strip().upper(),
                canonical_symbol=mapping.canonical_symbol,
                broker_symbol=mapping.broker_symbol,
                source="UNAVAILABLE",
                available=False,
                message=f"{mapping.canonical_symbol} is not confirmed for broker observation. {mapping.notes}",
            )

        client = self.mt5_client or self._default_client()
        if client is None:
            return self._fallback_or_unavailable(mapping.broker_id, mapping.canonical_symbol, mapping.broker_symbol, "MT5 client unavailable.")

        try:
            client.connect()
            info = client.get_symbol_info(mapping.broker_symbol)
            tick = client.get_latest_tick(mapping.broker_symbol)
            bid = self._value(tick, "bid")
            ask = self._value(tick, "ask")
            point = self._value(info, "point")
            spread = self._value(info, "spread")
            if spread is None and bid is not None and ask is not None:
                spread = abs(float(ask) - float(bid))
            return BrokerSymbolSnapshot(
                broker_id=mapping.broker_id,
                canonical_symbol=mapping.canonical_symbol,
                broker_symbol=mapping.broker_symbol,
                bid=bid,
                ask=ask,
                spread=spread,
                digits=self._value(info, "digits"),
                point=point,
                source="MT5_READ_ONLY",
                available=True,
                message=f"{mapping.broker_symbol} observed through read-only MT5 tick and symbol info.",
            )
        except Exception as exc:
            return self._fallback_or_unavailable(
                mapping.broker_id,
                mapping.canonical_symbol,
                mapping.broker_symbol,
                f"MT5 read-only observation unavailable: {exc}",
            )
        finally:
            try:
                if client is not None:
                    client.disconnect()
            except Exception:
                pass

    def snapshot_all_symbols(self, broker_id: str) -> list[BrokerSymbolSnapshot]:
        return [self.snapshot_symbol(broker_id, mapping.canonical_symbol) for mapping in self.mapper.list_symbol_mappings(broker_id)]

    def _default_client(self):
        try:
            from backend.broker_integrations.mt5.mt5_client import MT5Client

            return MT5Client()
        except Exception:
            return None

    def _fallback_or_unavailable(
        self,
        broker_id: str,
        canonical_symbol: str,
        broker_symbol: str | None,
        message: str,
    ) -> BrokerSymbolSnapshot:
        if not self.allow_simulation_fallback:
            return BrokerSymbolSnapshot(
                broker_id=broker_id,
                canonical_symbol=canonical_symbol,
                broker_symbol=broker_symbol,
                source="UNAVAILABLE",
                available=False,
                message=message,
            )
        bid, ask, digits, point = self._synthetic_quote(canonical_symbol)
        return BrokerSymbolSnapshot(
            broker_id=broker_id,
            canonical_symbol=canonical_symbol,
            broker_symbol=broker_symbol,
            bid=bid,
            ask=ask,
            spread=round(ask - bid, digits),
            digits=digits,
            point=point,
            timestamp=datetime.now(timezone.utc),
            source="SIMULATION_FALLBACK",
            available=True,
            message=f"{message} Returned deterministic simulation fallback snapshot.",
        )

    def _synthetic_quote(self, canonical_symbol: str) -> tuple[float, float, int, float]:
        symbol = canonical_symbol.upper()
        profiles = {
            "EURUSD": (1.1, 5, 0.00001, 0.00012),
            "XAUUSD": (2400.0, 2, 0.01, 0.35),
            "NIFTY50": (22000.0, 2, 0.01, 2.5),
        }
        base, digits, point, spread = profiles.get(symbol, (100.0, 2, 0.01, 0.1))
        offset = math.sin(sum(ord(char) for char in symbol)) * spread
        bid = round(base + offset, digits)
        ask = round(bid + spread, digits)
        return bid, ask, digits, point

    def _value(self, source, field: str):
        value = getattr(source, field, None)
        if value is None:
            return None
        try:
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return value
            return float(value)
        except Exception:
            return value
