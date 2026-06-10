from datetime import datetime, timezone
from typing import Any

from backend.strategy.client_signal_center_service import ClientSignalCenterService
from backend.strategy.real_signal_engine_service import RealSignalEngineService
from backend.strategy.signal_history_service import SignalHistoryService


class ClientSignalEngine:
    """Client-facing signal engine that only normalizes existing strategy outputs."""

    scoped_symbols = ("EURUSD", "XAUUSD", "NIFTY50")

    def __init__(
        self,
        signal_center_service: ClientSignalCenterService | None = None,
        real_signal_service: RealSignalEngineService | None = None,
        history_service: SignalHistoryService | None = None,
    ) -> None:
        self.signal_center_service = signal_center_service or ClientSignalCenterService()
        self.real_signal_service = real_signal_service or RealSignalEngineService()
        self.history_service = history_service or SignalHistoryService()

    def status(self) -> dict[str, Any]:
        return {
            "status": "READY",
            "mode": "REAL_SMC_MULTI_TIMEFRAME_SIGNAL_ENGINE",
            "symbols": list(self.scoped_symbols),
            "strategy_engine": self.real_signal_service.status(),
            "history_count": len(self.history_service.history(500)),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def current(self, record_history: bool = True) -> dict[str, Any]:
        signals = [self.signal_for_symbol(symbol, record_history=record_history) for symbol in self.scoped_symbols]
        return {
            "status": "READY",
            "signals": signals,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def refresh(self) -> dict[str, Any]:
        return self.current(record_history=True)

    def signal_for_symbol(self, symbol: str, record_history: bool = True) -> dict[str, Any]:
        normalized = str(symbol or "").strip().upper()
        if normalized == "NIFTY50":
            signal = self._nifty_pending()
        elif normalized in {"EURUSD", "XAUUSD"}:
            signal = self.real_signal_service.generate_signal(normalized)
        else:
            signal = self._wait(normalized, "Unsupported client dashboard symbol.", "INSUFFICIENT_DATA", "BLOCKED")
        if record_history:
            self.history_service.record(signal)
        return signal

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.history_service.history(limit)

    def history_for_symbol(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.history_service.history_for_symbol(symbol, limit)

    def latest(self, symbol: str | None = None) -> dict[str, Any]:
        if symbol:
            return self.real_signal_service.latest(symbol)
        return self.real_signal_service.latest()

    def _from_existing_center(self, symbol: str) -> dict[str, Any]:
        source = self.signal_center_service.signal_for_symbol(symbol)
        action = str(source.get("signal") or "WAIT").upper()
        if action not in {"BUY", "SELL"}:
            return self._wait(
                symbol,
                str(source.get("reason") or "No confirmed setup available."),
                str(source.get("risk_status") or "NO_SIGNAL"),
                str(source.get("execution_status") or "WAITING"),
                source,
            )
        confidence = source.get("confidence")
        if not isinstance(confidence, (int, float)):
            return self._wait(symbol, "Strategy signal lacked explicit confidence.", "INSUFFICIENT_DATA", "BLOCKED", source)
        return self._normalize(action, source)

    def _normalize(self, action: str, source: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": source.get("symbol"),
            "signal": action,
            "confidence": source.get("confidence"),
            "reason": source.get("reason") or "Strategy explicitly produced a confirmed setup.",
            "entry": source.get("entry"),
            "stop_loss": source.get("stop_loss"),
            "take_profit": source.get("take_profit"),
            "risk_reward": source.get("risk_reward"),
            "risk_status": source.get("risk_status") or "REJECTED",
            "execution_status": source.get("execution_status") or "BLOCKED",
            "strategy_components": self._components_from_source(source),
            "data_source": source.get("data_source") or "EXISTING_STRATEGY_PIPELINE",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _wait(
        self,
        symbol: str,
        reason: str = "No confirmed setup available.",
        risk_status: str = "NO_SIGNAL",
        execution_status: str = "WAITING",
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "signal": "WAIT",
            "confidence": None,
            "reason": reason or "No confirmed setup available.",
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "risk_status": risk_status if risk_status in {"APPROVED", "REJECTED", "NO_SIGNAL", "INSUFFICIENT_DATA", "INTEGRATION_PENDING"} else "NO_SIGNAL",
            "execution_status": execution_status if execution_status in {"READY", "BLOCKED", "WAITING"} else "WAITING",
            "strategy_components": self._components_from_source(source or {}),
            "data_source": (source or {}).get("data_source") or "EXISTING_STRATEGY_PIPELINE",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _nifty_pending(self) -> dict[str, Any]:
        return self._wait(
            "NIFTY50",
            "Indian market integration pending.",
            "INTEGRATION_PENDING",
            "BLOCKED",
            {"data_source": "PENDING_INDIAN_MARKET_INTEGRATION"},
        )

    def _components_from_source(self, source: dict[str, Any]) -> dict[str, bool | None]:
        text = str(source).lower()
        return {
            "liquidity_sweep": self._component(text, ["liquidity_sweep", "liquidity sweep", "sweep"]),
            "bos": self._component(text, ["bos", "break of structure"]),
            "choch": self._component(text, ["choch", "change of character"]),
            "fvg": self._component(text, ["fvg", "fair_value_gap", "fair value gap"]),
            "order_block": self._component(text, ["order_block", "order block"]),
            "session_valid": self._component(text, ["session_valid", "session valid", "killzone", "session"]),
        }

    def _component(self, text: str, names: list[str]) -> bool | None:
        if not text or text == "{}":
            return None
        if any(name in text for name in names):
            return True
        return None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
