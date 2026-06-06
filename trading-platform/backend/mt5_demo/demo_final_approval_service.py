from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class DemoFinalApprovalService:
    """Final approval gate for a future single DEMO order test."""

    def __init__(
        self,
        mt5_demo_service: Any,
        market_data_service: Any,
        strategy_feed_adapter: Any,
        risk_qualification_service: Any,
        execution_gate_service: Any,
        authorization_service: Any,
        dry_run_service: Any,
        preflight_service: Any,
        simulator_service: Any,
        readiness_service: Any,
        test_plan_service: Any,
    ) -> None:
        self.mt5_demo_service = mt5_demo_service
        self.market_data_service = market_data_service
        self.strategy_feed_adapter = strategy_feed_adapter
        self.risk_qualification_service = risk_qualification_service
        self.execution_gate_service = execution_gate_service
        self.authorization_service = authorization_service
        self.dry_run_service = dry_run_service
        self.preflight_service = preflight_service
        self.simulator_service = simulator_service
        self.readiness_service = readiness_service
        self.test_plan_service = test_plan_service
        self._history: list[dict[str, Any]] = []

    def run_final_approval_review(self) -> dict[str, Any]:
        blockers = self._collect_blockers()
        decision = self._decision(blockers)
        approved = decision == "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST"
        result = {
            "approval_id": f"demo-final-approval-{uuid4()}",
            "decision": decision,
            "approved_for_future_demo_order": approved,
            "approved_trade_count": 1 if approved else 0,
            "max_demo_lot": 0.01,
            "allowed_symbols": ["EURUSD", "XAUUSD"],
            "manual_confirmation_required": True,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "blockers": blockers,
            "warnings": self._warnings(approved),
            "timestamp": self._timestamp(),
        }
        self._history.append(result)
        return result

    def get_latest_approval(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return self._result("NOT_APPROVED", ["FINAL_APPROVAL_REVIEW_NOT_RUN"])

    def get_approval_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def revoke_final_approval(self) -> dict[str, Any]:
        result = self._result("NOT_APPROVED", ["FINAL_APPROVAL_REVOKED"])
        result["approval_id"] = f"demo-final-approval-revoked-{uuid4()}"
        self._history.append(result)
        return result

    def get_status(self) -> dict[str, Any]:
        latest = self.get_latest_approval()
        return {
            "status": "FINAL_APPROVAL_GATE_READY",
            "latest_decision": latest.get("decision"),
            "history_count": len(self._history),
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def _collect_blockers(self) -> list[str]:
        blockers: list[str] = []
        mt5_status = self.mt5_demo_service.get_status()
        market_status = self.market_data_service.get_market_data_status()
        strategy_feed = self.strategy_feed_adapter.build_strategy_feed("EURUSD")
        risk_status = self.risk_qualification_service.get_status()
        gate_status = self.execution_gate_service.get_status()
        authorization = self.authorization_service.get_status()
        dry_run = self.dry_run_service.get_latest()
        preflight = self.preflight_service.get_latest()
        simulator = self.simulator_service.get_latest()
        readiness = self.readiness_service.get_latest_audit()
        test_plan = self.test_plan_service.get_latest_test_plan()

        if mt5_status.get("status") != "CONNECTED":
            blockers.append("MT5_CONNECTION_NOT_VALIDATED")
        if market_status.get("status") != "READY":
            blockers.append("MARKET_DATA_NOT_VALIDATED")
        if not (strategy_feed.get("feed_ready") is True or strategy_feed.get("status") in {"READY", "OK"}):
            blockers.append("STRATEGY_FEED_NOT_VALIDATED")
        if risk_status.get("status") != "RISK_QUALIFICATION_READY":
            blockers.append("RISK_QUALIFICATION_NOT_VALIDATED")
        if gate_status.get("status") != "EXECUTION_GATE_VALIDATION_READY":
            blockers.append("EXECUTION_GATE_NOT_VALIDATED")
        if authorization.get("status") != "READY_FOR_DEMO_ORDER_TESTING":
            blockers.append("BLOCKED_BY_MISSING_MANUAL_CONFIRMATION")
        if dry_run.get("validation_passed") is not True:
            blockers.append("DRY_RUN_NOT_VALIDATED")
        if preflight.get("validation_passed") is not True:
            blockers.append("PREFLIGHT_NOT_VALIDATED")
        if simulator.get("simulation_passed") is not True:
            blockers.append("SIMULATOR_NOT_VALIDATED")
        if readiness.get("overall_status") != "READY":
            blockers.append("BLOCKED_BY_MISSING_READINESS")
        if test_plan.get("status") != "READY_FOR_FUTURE_DEMO_TESTING":
            blockers.append("TEST_PLAN_NOT_GENERATED")
        if any(
            item.get(flag) is True
            for item in [authorization, dry_run, preflight, simulator, readiness, test_plan]
            for flag in ["execution_allowed", "live_execution_enabled", "broker_execution_enabled"]
        ):
            blockers.append("BLOCKED_BY_SAFETY")
        return blockers

    def _decision(self, blockers: list[str]) -> str:
        if "BLOCKED_BY_SAFETY" in blockers:
            return "BLOCKED_BY_SAFETY"
        if "BLOCKED_BY_MISSING_MANUAL_CONFIRMATION" in blockers:
            return "BLOCKED_BY_MISSING_MANUAL_CONFIRMATION"
        if "BLOCKED_BY_MISSING_READINESS" in blockers:
            return "BLOCKED_BY_MISSING_READINESS"
        if blockers:
            return "NOT_APPROVED"
        return "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST"

    def _result(self, decision: str, blockers: list[str]) -> dict[str, Any]:
        return {
            "approval_id": "",
            "decision": decision,
            "approved_for_future_demo_order": False,
            "approved_trade_count": 0,
            "max_demo_lot": 0.01,
            "allowed_symbols": ["EURUSD", "XAUUSD"],
            "manual_confirmation_required": True,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "blockers": blockers,
            "warnings": self._warnings(False),
            "timestamp": self._timestamp(),
        }

    def _warnings(self, approved: bool) -> list[str]:
        warnings = ["NO_ORDER_PLACED_TODAY", "EXECUTION_REMAINS_DISABLED"]
        if approved:
            warnings.append("APPROVAL_IS_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST_ONLY")
        return warnings

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
