from datetime import datetime, timezone
from typing import Any

from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator
from backend.mt5_demo.mt5_strategy_consumption_service import MT5StrategyConsumptionService


class MT5RiskQualificationStore:
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


mt5_risk_qualification_store = MT5RiskQualificationStore()


class MT5RiskQualificationService:
    """Validate MT5-fed strategy signals against existing execution risk checks."""

    supported_symbols = {"EURUSD", "XAUUSD"}

    def __init__(
        self,
        strategy_consumption_service: MT5StrategyConsumptionService | None = None,
        risk_evaluator: ExecutionRiskEvaluator | None = None,
        store: MT5RiskQualificationStore | None = None,
    ) -> None:
        self.strategy_consumption_service = strategy_consumption_service or MT5StrategyConsumptionService()
        self.risk_evaluator = risk_evaluator or ExecutionRiskEvaluator()
        self.store = store or mt5_risk_qualification_store

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "RISK_QUALIFICATION_READY",
            "source": "MT5_DEMO_STRATEGY_OUTPUT",
            "supported_symbols": sorted(self.supported_symbols),
            "history_count": len(self.store.history(1000)),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def qualify_symbol_from_mt5_strategy(self, symbol: str) -> dict[str, Any]:
        normalized = str(symbol or "").strip().upper()
        if normalized not in self.supported_symbols:
            return self.store.store(self._blocked_result(normalized, None, "Unsupported symbol.", "BLOCKED"))

        strategy_result = self.strategy_consumption_service.latest(normalized)
        if strategy_result.get("status") == "NOT_RUN":
            strategy_result = self.strategy_consumption_service.analyze_symbol_from_mt5_feed(normalized)
        signal = strategy_result.get("signal", {})
        action = str(signal.get("action") or "NONE").upper()
        warnings = list(strategy_result.get("warnings", []))

        if signal.get("forced_signal") is True:
            return self.store.store(self._blocked_result(normalized, strategy_result, "Forced signal detected.", "BLOCKED"))
        if action not in {"BUY", "SELL"}:
            return self.store.store(self._blocked_result(normalized, strategy_result, "No valid BUY/SELL signal exists.", "NO_SIGNAL"))

        decision = self.risk_evaluator.evaluate_single_account_request(
            {
                "request_id": f"mt5-risk-qualification-{normalized}-{signal.get('signal_id') or self._timestamp()}",
                "signal_id": signal.get("signal_id"),
                "symbol": normalized,
                "canonical_symbol": normalized,
                "action": action,
                "lot": 0.01,
                "requested_lot": 0.01,
                "confirm_demo_execution": False,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            }
        )
        risk_approved = bool(decision.approved) and False
        reasons = list(decision.rejection_reasons)
        qualification_status = "APPROVED" if risk_approved else "BLOCKED"
        result = {
            "symbol": normalized,
            "source": "MT5_DEMO_STRATEGY_OUTPUT",
            "strategy_signal_available": True,
            "strategy_result": strategy_result,
            "risk_checked": True,
            "risk_approved": risk_approved,
            "risk_per_trade": "0.5-1%",
            "daily_drawdown_limit": "3%",
            "qualification_status": qualification_status,
            "block_reason": "; ".join(reasons) if reasons else "Execution remains disabled during Phase 15 validation.",
            "risk_decision": decision.model_dump(mode="json"),
            "execution_allowed": False,
            "execution_triggered": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "warnings": warnings + list(decision.warnings),
            "timestamp": self._timestamp(),
        }
        return self.store.store(result)

    def qualify_all_symbols_from_mt5_strategy(self) -> dict[str, Any]:
        results = {symbol: self.qualify_symbol_from_mt5_strategy(symbol) for symbol in sorted(self.supported_symbols)}
        return {
            "source": "MT5_DEMO_STRATEGY_OUTPUT",
            "symbols": results,
            "all_safety_locked": self._all_safety_locked(results),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def get_latest_risk_result(self, symbol: str) -> dict[str, Any]:
        latest = self.store.latest(symbol)
        if latest:
            return latest
        return {
            "symbol": str(symbol or "").strip().upper(),
            "source": "MT5_DEMO_STRATEGY_OUTPUT",
            "strategy_signal_available": False,
            "risk_checked": False,
            "risk_approved": False,
            "qualification_status": "NOT_RUN",
            "execution_allowed": False,
            "execution_triggered": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "warnings": ["No MT5 risk qualification result has been recorded yet."],
            "timestamp": self._timestamp(),
        }

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.history(limit)

    def close(self) -> None:
        self.strategy_consumption_service.close()

    def _blocked_result(self, symbol: str, strategy_result: dict[str, Any] | None, reason: str, status: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "source": "MT5_DEMO_STRATEGY_OUTPUT",
            "strategy_signal_available": bool(strategy_result and strategy_result.get("signal", {}).get("action") in {"BUY", "SELL"}),
            "strategy_result": strategy_result,
            "risk_checked": True,
            "risk_approved": False,
            "risk_per_trade": "0.5-1%",
            "daily_drawdown_limit": "3%",
            "qualification_status": status,
            "block_reason": reason,
            "execution_allowed": False,
            "execution_triggered": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "warnings": [reason],
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

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
