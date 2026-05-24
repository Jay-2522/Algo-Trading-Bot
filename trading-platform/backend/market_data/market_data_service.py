from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.broker_integrations.mt5.mt5_client import MT5Client, mt5
from backend.market_data.candle import Candle
from backend.market_data.timeframe import get_mt5_timeframe
from backend.market_data.validators import (
    supported_timeframes,
    validate_candle_count,
    validate_symbol_name,
    validate_timeframe,
)
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class MarketDataService:
    """Read-only market data service backed by MetaTrader 5."""

    def __init__(self, mt5_client: MT5Client | None = None) -> None:
        self.mt5_client = mt5_client or MT5Client()

    def validate_symbol(self, symbol: str) -> bool:
        """Check whether a symbol is available in MT5."""

        normalized_symbol = validate_symbol_name(symbol)
        try:
            self._ensure_connected()
            return self.mt5_client.get_symbol_info(normalized_symbol) is not None
        except Exception as exc:
            logger.warning("Symbol validation failed for %s: %s", normalized_symbol, exc)
            return False

    def get_latest_tick(self, symbol: str) -> Dict[str, Any]:
        """Return the latest symbol tick as a JSON-safe dictionary."""

        normalized_symbol = validate_symbol_name(symbol)
        try:
            self._ensure_connected()
            tick = self.mt5_client.get_latest_tick(normalized_symbol)
            return self._to_json_safe(tick)
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("Unable to fetch latest tick for %s", normalized_symbol)
            raise RuntimeError(f"Unable to fetch latest tick for {normalized_symbol}: {exc}") from exc

    def get_candles(self, symbol: str, timeframe: str, count: int = 100) -> List[Candle]:
        """Fetch normalized candles for a symbol and timeframe."""

        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        validated_count = validate_candle_count(count)
        mt5_timeframe = get_mt5_timeframe(normalized_timeframe)

        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is unavailable. Install requirements and verify MT5 support.")

        try:
            self._ensure_connected()
            rates = mt5.copy_rates_from_pos(normalized_symbol, mt5_timeframe, 0, validated_count)
            if rates is None:
                raise RuntimeError(f"MT5 returned no candle data. Last error: {mt5.last_error()}")

            candles = [
                Candle(
                    symbol=normalized_symbol,
                    timeframe=normalized_timeframe,
                    time=datetime.fromtimestamp(int(rate["time"]), tz=timezone.utc),
                    open=float(rate["open"]),
                    high=float(rate["high"]),
                    low=float(rate["low"]),
                    close=float(rate["close"]),
                    tick_volume=int(rate["tick_volume"]),
                    spread=int(rate["spread"]),
                    real_volume=int(rate["real_volume"]),
                )
                for rate in rates
            ]
            return candles
        except ValueError:
            raise
        except Exception as exc:
            logger.exception(
                "Unable to fetch candles for %s on %s",
                normalized_symbol,
                normalized_timeframe,
            )
            raise RuntimeError(
                f"Unable to fetch candles for {normalized_symbol} on {normalized_timeframe}: {exc}"
            ) from exc

    def get_multi_timeframe_data(
        self,
        symbol: str,
        timeframes: list[str],
        count: int = 100,
    ) -> Dict[str, List[Candle]]:
        """Return candle data for multiple supported timeframes."""

        normalized_symbol = validate_symbol_name(symbol)
        validate_candle_count(count)
        data: Dict[str, List[Candle]] = {}

        for timeframe in timeframes:
            normalized_timeframe = validate_timeframe(timeframe)
            data[normalized_timeframe] = self.get_candles(
                normalized_symbol,
                normalized_timeframe,
                count,
            )

        return data

    def close(self) -> None:
        """Close the underlying MT5 connection."""

        self.mt5_client.disconnect()

    def _ensure_connected(self) -> None:
        if not self.mt5_client.connected:
            self.mt5_client.connect()

    def _to_json_safe(self, value: Any) -> Any:
        if hasattr(value, "_asdict"):
            return {key: self._to_json_safe(item) for key, item in value._asdict().items()}
        if isinstance(value, dict):
            return {key: self._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_json_safe(item) for item in value]
        if hasattr(value, "item"):
            return value.item()
        return value


def build_snapshot(symbol: str, service: MarketDataService | None = None) -> dict:
    """Build the standard Day 2 market snapshot payload."""

    market_data_service = service or MarketDataService()
    normalized_symbol = validate_symbol_name(symbol)
    snapshot = {
        "symbol": normalized_symbol,
        "latest_tick": market_data_service.get_latest_tick(normalized_symbol),
        "candles": market_data_service.get_multi_timeframe_data(
            normalized_symbol,
            ["M15", "H1", "H4"],
            count=100,
        ),
        "available_timeframes": supported_timeframes(),
        "timestamp": datetime.now(timezone.utc),
        "status": "ok",
    }
    return snapshot

