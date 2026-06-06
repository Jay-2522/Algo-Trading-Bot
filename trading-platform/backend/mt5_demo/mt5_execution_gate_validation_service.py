from datetime import datetime, timezone
from typing import Any

from backend.mt5_demo.market_snapshot_service import MarketSnapshotService
from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService
from backend.mt5_demo.mt5_risk_qualification_service import MT5RiskQualificationService


class MT5ExecutionGateValidationStore:
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


mt5_execution_gate_store = MT5ExecutionGateValidationStore()


class MT5ExecutionGateValidationService:
    """Final Phase 15 execution gate validation without order placement."""

    supported_symbols = {"EURUSD", "XAUUSD"}

    def __init__(
        self,
        risk_qualification_service: MT5RiskQualificationService | None = None,
        market_snapshot_service: MarketSnapshotService | None = None,
        backfill_service: MT5HistoricalBackfillService | None = None,
        store: MT5ExecutionGateValidationStore | None = None,
    ) -> None:
        self.risk_qualification_service = risk_qualification_service or MT5RiskQualificationService()
        self.market_snapshot_service = market_snapshot_service or MarketSnapshotService()
        self.backfill_service = backfill_service or MT5HistoricalBackfillService()
        self.store = store or mt5_execution_gate_store

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "EXECUTION_GATE_VALIDATION_READY",
            "supported_symbols": sorted(self.supported_symbols),
            "history_count": len(self.store.history(1000)),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def evaluate_symbol(self, symbol: str) -> dict[str, Any]:
        normalized = str(symbol or "").strip().upper()
        warnings: list[str] = []
        if normalized not in self.supported_symbols:
            return self.store.store(self._result(normalized, "BLOCKED_BY_NO_SIGNAL", False, False, warnings + ["Unsupported symbol."], None))

        risk = self.risk_qualification_service.get_latest_risk_result(normalized)
        if risk.get("qualification_status") == "NOT_RUN":
            risk = self.risk_qualification_service.qualify_symbol_from_mt5_strategy(normalized)
        strategy = risk.get("strategy_result") or {}
        warnings.extend(risk.get("warnings", []))
        gate_status = self._gate_status(risk, strategy)
        return self.store.store(
            self._result(
                normalized,
                gate_status,
                bool(strategy),
                bool(risk.get("risk_approved")),
                warnings,
                risk,
            )
        )

    def evaluate_all(self) -> dict[str, Any]:
        results = {symbol: self.evaluate_symbol(symbol) for symbol in sorted(self.supported_symbols)}
        return {
            "symbols": results,
            "all_safety_locked": self._all_safety_locked(results),
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
        return self._result(str(symbol or "").strip().upper(), "NOT_RUN", False, False, ["No execution gate result has been recorded yet."], None)

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.history(limit)

    def pipeline_summary(self) -> dict[str, Any]:
        market = self.market_snapshot_service.get_overview()
        eur_history = self.backfill_service.summarize_backfill("EURUSD", "H1")
        xau_history = self.backfill_service.summarize_backfill("XAUUSD", "H1")
        risk_all = self.risk_qualification_service.qualify_all_symbols_from_mt5_strategy()
        gate_all = self.evaluate_all()
        return {
            "market_data": market.get("status"),
            "historical_backfill": self._pair_status(eur_history, xau_history),
            "strategy_feed": "READY" if all(item.get("strategy_result", {}).get("feed_ready") for item in risk_all.get("symbols", {}).values()) else "REVIEW",
            "strategy_consumption": "READY" if all(item.get("strategy_result", {}).get("strategy_consumed_feed") for item in risk_all.get("symbols", {}).values()) else "REVIEW",
            "risk_qualification": "READY" if risk_all.get("all_safety_locked") else "REVIEW",
            "execution_gate": "READY" if gate_all.get("all_safety_locked") else "REVIEW",
            "overall_status": "VALIDATION_READY" if gate_all.get("all_safety_locked") else "REVIEW",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def close(self) -> None:
        self.risk_qualification_service.close()

    def _gate_status(self, risk: dict[str, Any], strategy: dict[str, Any]) -> str:
        if strategy.get("signal", {}).get("forced_signal") is True:
            return "BLOCKED_BY_RISK"
        if not strategy or strategy.get("signal", {}).get("action") in {None, "NONE", "WAIT"}:
            return "BLOCKED_BY_NO_SIGNAL"
        if any("stale" in str(warning).lower() for warning in strategy.get("warnings", [])):
            return "BLOCKED_BY_STALE_DATA"
        if not risk.get("risk_approved"):
            return "BLOCKED_BY_RISK"
        return "BLOCKED_BY_SIMULATION_MODE"

    def _result(
        self,
        symbol: str,
        gate_status: str,
        strategy_available: bool,
        risk_approved: bool,
        warnings: list[str],
        risk_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "gate_status": gate_status,
            "strategy_available": strategy_available,
            "risk_approved": risk_approved,
            "risk_result": risk_result,
            "execution_allowed": False,
            "execution_triggered": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "warnings": warnings,
            "timestamp": self._timestamp(),
        }

    def _pair_status(self, first: dict[str, Any], second: dict[str, Any]) -> str:
        if first.get("status") == "OK" and second.get("status") == "OK":
            return "READY"
        if first.get("status") == "OK" or second.get("status") == "OK":
            return "PARTIAL"
        return "UNAVAILABLE"

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
