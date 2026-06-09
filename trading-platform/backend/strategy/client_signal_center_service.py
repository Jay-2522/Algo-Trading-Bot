from datetime import datetime, timezone
from typing import Any

from backend.mt5_demo.mt5_execution_gate_validation_service import MT5ExecutionGateValidationService
from backend.mt5_demo.mt5_risk_qualification_service import MT5RiskQualificationService
from backend.mt5_demo.mt5_strategy_consumption_service import MT5StrategyConsumptionService


class ClientSignalCenterService:
    """Normalize scoped strategy signals for the client dashboard without execution."""

    scoped_symbols = ("EURUSD", "XAUUSD", "NIFTY50")

    def __init__(
        self,
        strategy_consumption_service: MT5StrategyConsumptionService | None = None,
        risk_qualification_service: MT5RiskQualificationService | None = None,
        execution_gate_service: MT5ExecutionGateValidationService | None = None,
    ) -> None:
        self.strategy_consumption_service = strategy_consumption_service or MT5StrategyConsumptionService()
        self.risk_qualification_service = risk_qualification_service or MT5RiskQualificationService(
            strategy_consumption_service=self.strategy_consumption_service
        )
        self.execution_gate_service = execution_gate_service or MT5ExecutionGateValidationService(
            risk_qualification_service=self.risk_qualification_service
        )
        self._latest: dict[str, dict[str, Any]] = {}

    def status(self) -> dict[str, Any]:
        return {
            "status": "READY",
            "symbols": list(self.scoped_symbols),
            "demo_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def current(self) -> dict[str, Any]:
        signals = [self.signal_for_symbol(symbol) for symbol in self.scoped_symbols]
        return {
            "status": "READY",
            "signals": signals,
            "demo_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def signal_for_symbol(self, symbol: str) -> dict[str, Any]:
        normalized = str(symbol or "").strip().upper()
        if normalized == "NIFTY50":
            result = self._nifty_pending()
        elif normalized in {"EURUSD", "XAUUSD"}:
            result = self._mt5_signal(normalized)
        else:
            result = self._blocked(normalized, "Unsupported client dashboard symbol.", "INSUFFICIENT_DATA")
        self._latest[normalized] = result
        return result

    def refresh(self) -> dict[str, Any]:
        return self.current()

    def latest(self) -> dict[str, Any]:
        if not self._latest:
            return self.current()
        return {
            "status": "READY",
            "signals": [self._latest.get(symbol) or self.signal_for_symbol(symbol) for symbol in self.scoped_symbols],
            "demo_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _mt5_signal(self, symbol: str) -> dict[str, Any]:
        strategy = self.strategy_consumption_service.latest(symbol)
        if strategy.get("status") == "NOT_RUN":
            strategy = self.strategy_consumption_service.analyze_symbol_from_mt5_feed(symbol)
        risk = self.risk_qualification_service.get_latest_risk_result(symbol)
        if risk.get("qualification_status") == "NOT_RUN":
            risk = self.risk_qualification_service.qualify_symbol_from_mt5_strategy(symbol)
        gate = self.execution_gate_service.latest(symbol)
        if gate.get("gate_status") == "NOT_RUN":
            gate = self.execution_gate_service.evaluate_symbol(symbol)

        signal_payload = strategy.get("signal") or {}
        raw_signal = strategy.get("raw_signal") or {}
        action = str(signal_payload.get("action") or "WAIT").upper()
        if action not in {"BUY", "SELL"}:
            action = "WAIT"

        confidence = signal_payload.get("confidence")
        if action == "WAIT" or not strategy.get("strategy_consumed_feed"):
            confidence = None

        entry = self._number_from(raw_signal, ["entry", "entry_price", "recommended_entry"])
        stop_loss = self._number_from(raw_signal, ["stop_loss", "sl"])
        take_profit = self._number_from(raw_signal, ["take_profit", "tp"])
        risk_reward = self._risk_reward(entry, stop_loss, take_profit, action)
        if action == "WAIT":
            reason = "No confirmed setup available."
            risk_status = "NO_SIGNAL" if strategy.get("feed_ready") else "INSUFFICIENT_DATA"
            execution_status = "WAITING"
        else:
            reason = self._reason_from(strategy, risk, gate)
            risk_status = "APPROVED" if risk.get("risk_approved") else "REJECTED"
            execution_status = "READY" if risk_status == "APPROVED" and entry and stop_loss and take_profit else "BLOCKED"

        return {
            "symbol": symbol,
            "signal": action,
            "confidence": confidence if isinstance(confidence, (int, float)) else None,
            "reason": reason,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward": risk_reward,
            "risk_status": risk_status,
            "execution_status": execution_status,
            "data_source": "MT5_DEMO_STRATEGY_PIPELINE",
            "demo_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _nifty_pending(self) -> dict[str, Any]:
        return {
            "symbol": "NIFTY50",
            "signal": "WAIT",
            "confidence": None,
            "reason": "Indian market integration pending.",
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "risk_status": "INTEGRATION_PENDING",
            "execution_status": "BLOCKED",
            "data_source": "PENDING_INDIAN_MARKET_INTEGRATION",
            "demo_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _blocked(self, symbol: str, reason: str, risk_status: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "signal": "WAIT",
            "confidence": None,
            "reason": reason,
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "risk_status": risk_status,
            "execution_status": "BLOCKED",
            "data_source": "CLIENT_SCOPE",
            "demo_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _reason_from(self, strategy: dict[str, Any], risk: dict[str, Any], gate: dict[str, Any]) -> str:
        warnings = strategy.get("warnings") or risk.get("warnings") or gate.get("warnings") or []
        if warnings:
            return str(warnings[0])
        if gate.get("gate_status"):
            return str(gate["gate_status"]).replace("_", " ").title()
        return "Strategy signal available but guarded execution remains demo-only."

    def _number_from(self, payload: dict[str, Any], keys: list[str]) -> float | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str) and value.strip():
                try:
                    return float(value)
                except ValueError:
                    continue
        return None

    def _risk_reward(self, entry: float | None, stop_loss: float | None, take_profit: float | None, action: str) -> float | None:
        if not entry or not stop_loss or not take_profit or action not in {"BUY", "SELL"}:
            return None
        risk = entry - stop_loss if action == "BUY" else stop_loss - entry
        reward = take_profit - entry if action == "BUY" else entry - take_profit
        if risk <= 0 or reward <= 0:
            return None
        return round(reward / risk, 2)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
