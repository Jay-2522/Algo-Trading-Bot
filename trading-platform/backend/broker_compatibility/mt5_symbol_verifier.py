from typing import Any

from backend.broker_compatibility.mt5_demo_models import BrokerSymbolVerification


class MT5SymbolVerifier:
    """Verify broker symbols through read-only MT5 symbol_info when available."""

    def __init__(self, mt5_client=None) -> None:
        self.mt5_client = mt5_client

    def verify_symbol(self, canonical_symbol: str, broker_symbol: str | None, broker_id: str = "UNKNOWN") -> BrokerSymbolVerification:
        if not broker_symbol:
            return BrokerSymbolVerification(
                broker_id=broker_id,
                canonical_symbol=canonical_symbol,
                expected_broker_symbol=broker_symbol,
                verification_status="UNSUPPORTED",
                message="No broker symbol mapping is available.",
            )

        client = self.mt5_client or self._default_client()
        if client is None:
            return self._unavailable(broker_id, canonical_symbol, broker_symbol, "MT5 client package is unavailable.")
        try:
            client.connect()
            symbol_info = client.get_symbol_info(broker_symbol)
            if symbol_info is None:
                return BrokerSymbolVerification(
                    broker_id=broker_id,
                    canonical_symbol=canonical_symbol,
                    expected_broker_symbol=broker_symbol,
                    verification_status="NOT_FOUND",
                    message=f"{broker_symbol} was not found in MT5 symbol info.",
                )
            return BrokerSymbolVerification(
                broker_id=broker_id,
                canonical_symbol=canonical_symbol,
                expected_broker_symbol=broker_symbol,
                mt5_symbol_found=True,
                visible=self._value(symbol_info, "visible"),
                trade_allowed=self._trade_allowed(symbol_info),
                digits=self._value(symbol_info, "digits"),
                point=self._value(symbol_info, "point"),
                spread=self._value(symbol_info, "spread"),
                verification_status="VERIFIED",
                message=f"{broker_symbol} was verified through read-only MT5 symbol_info.",
            )
        except Exception as exc:
            return self._unavailable(broker_id, canonical_symbol, broker_symbol, str(exc))
        finally:
            try:
                if client is not None:
                    client.disconnect()
            except Exception:
                pass

    def _default_client(self):
        try:
            from backend.broker_integrations.mt5.mt5_client import MT5Client

            return MT5Client()
        except Exception:
            return None

    def _unavailable(self, broker_id: str, canonical_symbol: str, broker_symbol: str, message: str) -> BrokerSymbolVerification:
        return BrokerSymbolVerification(
            broker_id=broker_id,
            canonical_symbol=canonical_symbol,
            expected_broker_symbol=broker_symbol,
            verification_status="MT5_UNAVAILABLE",
            message=f"MT5 unavailable for read-only verification: {message}",
        )

    def _value(self, symbol_info: Any, field: str):
        return getattr(symbol_info, field, None)

    def _trade_allowed(self, symbol_info: Any) -> bool | None:
        if hasattr(symbol_info, "trade_allowed"):
            return bool(getattr(symbol_info, "trade_allowed"))
        trade_mode = getattr(symbol_info, "trade_mode", None)
        if trade_mode is None:
            return None
        return bool(trade_mode)
