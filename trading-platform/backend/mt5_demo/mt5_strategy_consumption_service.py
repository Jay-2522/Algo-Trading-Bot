from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder

from backend.mt5_demo.mt5_strategy_feed_adapter import MT5StrategyFeedAdapter
from backend.strategy_engine.strategy_service import StrategyService


class MT5StrategyConsumptionStore:
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def store(self, result: dict[str, Any]) -> dict[str, Any]:
        self._history.append(result)
        return result

    def latest(self, symbol: str) -> dict[str, Any] | None:
        normalized = symbol.upper()
        for item in reversed(self._history):
            if item.get("symbol") == normalized:
                return item
        return None

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]


mt5_strategy_consumption_store = MT5StrategyConsumptionStore()


class MT5StrategyConsumptionService:
    """Validate existing strategy engines against MT5 demo historical feeds."""

    supported_symbols = {"EURUSD", "XAUUSD"}

    def __init__(
        self,
        feed_adapter: MT5StrategyFeedAdapter | None = None,
        strategy_service: StrategyService | None = None,
        store: MT5StrategyConsumptionStore | None = None,
    ) -> None:
        self.feed_adapter = feed_adapter or MT5StrategyFeedAdapter()
        self.strategy_service = strategy_service or StrategyService()
        self.store = store or mt5_strategy_consumption_store

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "STRATEGY_CONSUMPTION_READY",
            "source": "MT5_DEMO_HISTORY",
            "supported_symbols": sorted(self.supported_symbols),
            "history_count": len(self.store.history(1000)),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def analyze_symbol_from_mt5_feed(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        if normalized not in self.supported_symbols:
            return self.store.store(self._error_result(normalized, "Unsupported symbol."))

        warnings: list[str] = []
        feed = self.feed_adapter.build_strategy_feed(normalized)
        warnings.extend(feed.get("warnings", []))
        candles = feed.get("timeframes", {}).get("M5", [])
        feed_ready = bool(feed.get("feed_ready")) and bool(candles)
        strategy_consumed_feed = False
        signal_payload: dict[str, Any] | None = None
        analysis = {
            "trend": "UNKNOWN",
            "liquidity": "UNKNOWN",
            "structure": "UNKNOWN",
            "fvg": "UNKNOWN",
            "regime": "UNKNOWN",
            "bias": "UNKNOWN",
            "confidence": 0.0,
        }

        if feed_ready:
            try:
                if normalized == "XAUUSD":
                    signal = self.strategy_service.analyze_xauusd(candles=candles)
                else:
                    signal = self.strategy_service.analyze_eurusd(candles=candles)
                signal_payload = jsonable_encoder(signal)
                strategy_consumed_feed = True
                analysis = self._analysis_from_signal(signal_payload)
            except Exception as exc:
                warnings.append(f"Strategy analysis failed against MT5 feed: {exc}")
        else:
            warnings.append("MT5 strategy feed is not ready; strategy analysis was not forced.")

        action = str((signal_payload or {}).get("action") or "WAIT").upper()
        if action not in {"BUY", "SELL", "WAIT", "NONE"}:
            action = "WAIT"
        forced_signal = False
        execution_triggered = False
        result = {
            "symbol": normalized,
            "source": "MT5_DEMO_HISTORY",
            "feed_ready": feed_ready,
            "strategy_consumed_feed": strategy_consumed_feed,
            "analysis": analysis,
            "signal": {
                "action": action if strategy_consumed_feed else "WAIT",
                "forced_signal": forced_signal,
                "signal_id": (signal_payload or {}).get("signal_id"),
                "confidence": (signal_payload or {}).get("confidence", 0.0),
            },
            "raw_signal": signal_payload,
            "feed_validation": feed.get("validation", {}),
            "execution_triggered": execution_triggered,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "warnings": warnings,
            "timestamp": self._timestamp(),
        }
        return self.store.store(result)

    def analyze_all_symbols_from_mt5_feed(self) -> dict[str, Any]:
        results = {symbol: self.analyze_symbol_from_mt5_feed(symbol) for symbol in sorted(self.supported_symbols)}
        return {
            "source": "MT5_DEMO_HISTORY",
            "symbols": results,
            "all_safety_locked": self._all_safety_locked(results),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def validate_strategy_consumption(self, symbol: str) -> dict[str, Any]:
        result = self.analyze_symbol_from_mt5_feed(symbol)
        return {
            "symbol": result["symbol"],
            "valid": result["strategy_consumed_feed"] or not result["feed_ready"],
            "feed_ready": result["feed_ready"],
            "strategy_consumed_feed": result["strategy_consumed_feed"],
            "forced_signal": result["signal"]["forced_signal"],
            "execution_triggered": result["execution_triggered"],
            "warnings": result["warnings"],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def latest(self, symbol: str) -> dict[str, Any]:
        latest = self.store.latest(symbol)
        if latest:
            return latest
        return {
            "symbol": self._normalize_symbol(symbol),
            "source": "MT5_DEMO_HISTORY",
            "status": "NOT_RUN",
            "feed_ready": False,
            "strategy_consumed_feed": False,
            "signal": {"action": "NONE", "forced_signal": False},
            "execution_triggered": False,
            "warnings": ["No MT5 strategy consumption result has been recorded yet."],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.history(limit)

    def close(self) -> None:
        self.strategy_service.close()

    def _analysis_from_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        confluence = signal.get("confluence_score") or {}
        return {
            "trend": signal.get("trend", "UNKNOWN"),
            "liquidity": "ALIGNED" if "liquidity" in signal.get("aligned_confirmations", []) else "UNKNOWN",
            "structure": "ALIGNED" if "structure" in signal.get("aligned_confirmations", []) else "UNKNOWN",
            "fvg": "ALIGNED" if "fvg" in signal.get("aligned_confirmations", []) else "UNKNOWN",
            "regime": signal.get("market_regime", confluence.get("risk_mode", "UNKNOWN")),
            "bias": signal.get("action", "WAIT"),
            "confidence": float(signal.get("confidence") or 0.0),
        }

    def _error_result(self, symbol: str, message: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "source": "MT5_DEMO_HISTORY",
            "feed_ready": False,
            "strategy_consumed_feed": False,
            "analysis": {},
            "signal": {"action": "NONE", "forced_signal": False},
            "execution_triggered": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "warnings": [message],
            "timestamp": self._timestamp(),
        }

    def _all_safety_locked(self, payload: Any) -> bool:
        for _, key, value in self._walk(payload):
            if key in {"execution_allowed", "execution_triggered", "live_execution_enabled", "broker_execution_enabled", "forced_signal"} and value is True:
                return False
        return True

    def _walk(self, payload: Any):
        if isinstance(payload, dict):
            for key, value in payload.items():
                yield payload, key, value
                yield from self._walk(value)
        elif isinstance(payload, list):
            for item in payload:
                yield from self._walk(item)

    def _normalize_symbol(self, symbol: str) -> str:
        return str(symbol or "").strip().upper()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
