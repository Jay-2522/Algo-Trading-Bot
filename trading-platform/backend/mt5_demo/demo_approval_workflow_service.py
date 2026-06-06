from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class DemoApprovalWorkflowService:
    """Orchestrates Phase 16 approval steps without placing any order."""

    allowed_symbols = {"EURUSD", "XAUUSD"}
    allowed_actions = {"BUY", "SELL"}
    max_demo_lot = 0.01

    def __init__(
        self,
        authorization_service: Any,
        dry_run_service: Any,
        preflight_service: Any,
        simulator_service: Any,
        readiness_service: Any,
        test_plan_service: Any,
        final_approval_service: Any,
    ) -> None:
        self.authorization_service = authorization_service
        self.dry_run_service = dry_run_service
        self.preflight_service = preflight_service
        self.simulator_service = simulator_service
        self.readiness_service = readiness_service
        self.test_plan_service = test_plan_service
        self.final_approval_service = final_approval_service
        self._history: list[dict[str, Any]] = []

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "DEMO_APPROVAL_WORKFLOW_READY",
            "history_count": len(self._history),
            "execution_allowed": False,
            "mt5_order_sent": False,
            "would_send_to_mt5": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def run_workflow(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        blockers = self._validate_payload(payload)
        if blockers:
            result = self._blocked_result(blockers)
            self._history.append(result)
            return result

        symbol = str(payload["symbol"]).strip().upper()
        action = str(payload["action"]).strip().upper()
        lot = float(payload["lot"])
        entry_price = float(payload["entry_price"])
        stop_loss = float(payload["stop_loss"])
        take_profit = float(payload["take_profit"])

        authorization_result = self.authorization_service.request_demo_authorization(
            {
                "environment": "DEMO",
                "manual_confirmation": True,
                "acknowledge_no_live_trading": True,
                "acknowledge_demo_only": True,
                "max_demo_lot": self.max_demo_lot,
            }
        )
        dry_run_result = self.dry_run_service.create_dry_run(
            {
                "symbol": symbol,
                "action": action,
                "lot": lot,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_decision_id": f"workflow-risk-{uuid4()}",
                "gate_decision_id": f"workflow-gate-{uuid4()}",
                "manual_confirmation": True,
            }
        )
        preflight_result = self.preflight_service.run_preflight(
            {
                "dry_run_id": dry_run_result.get("dry_run_id"),
                "symbol": symbol,
                "action": action,
                "lot": lot,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }
        )
        simulator_result = self.simulator_service.simulate_execution(
            {
                "preflight_id": preflight_result.get("preflight_id"),
                "symbol": symbol,
                "action": action,
                "lot": lot,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }
        )
        readiness_result = self.readiness_service.run_readiness_audit()
        test_plan_result = self.test_plan_service.generate_test_plan()
        final_approval_result = self.final_approval_service.run_final_approval_review()

        workflow_blockers = self._workflow_blockers(
            authorization_result,
            dry_run_result,
            preflight_result,
            simulator_result,
            readiness_result,
            test_plan_result,
            final_approval_result,
        )
        approved = final_approval_result.get("approved_for_future_demo_order") is True and not workflow_blockers
        result = {
            "workflow_id": f"demo-approval-workflow-{uuid4()}",
            "status": "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST" if approved else "BLOCKED",
            "authorization_result": authorization_result,
            "dry_run_result": dry_run_result,
            "preflight_result": preflight_result,
            "simulator_result": simulator_result,
            "readiness_result": readiness_result,
            "test_plan_result": test_plan_result,
            "final_approval_result": final_approval_result,
            "approved_for_future_demo_order": approved,
            "approved_trade_count": 1 if approved else 0,
            "max_demo_lot": self.max_demo_lot,
            "execution_allowed": False,
            "mt5_order_sent": False,
            "would_send_to_mt5": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "blockers": workflow_blockers,
            "warnings": ["NO_ORDER_PLACED_TODAY"],
            "timestamp": self._timestamp(),
        }
        self._history.append(result)
        return result

    def get_latest(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return self._blocked_result(["WORKFLOW_NOT_RUN"])

    def list_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def _validate_payload(self, payload: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        if payload.get("environment") != "DEMO":
            blockers.append("ENVIRONMENT_MUST_BE_DEMO")
        if str(payload.get("symbol") or "").strip().upper() not in self.allowed_symbols:
            blockers.append("INVALID_SYMBOL")
        if str(payload.get("action") or "").strip().upper() not in self.allowed_actions:
            blockers.append("INVALID_ACTION")
        lot = self._float_or_none(payload.get("lot"))
        if lot != self.max_demo_lot:
            blockers.append("MAX_DEMO_LOT_MUST_BE_0_01")
        for key in ["entry_price", "stop_loss", "take_profit"]:
            value = self._float_or_none(payload.get(key))
            if value is None or value <= 0:
                blockers.append(f"{key.upper()}_REQUIRED")
        for key in [
            "manual_confirmation",
            "acknowledge_no_live_trading",
            "acknowledge_demo_only",
            "acknowledge_no_order_placement_today",
        ]:
            if payload.get(key) is not True:
                blockers.append(f"{key.upper()}_REQUIRED")
        if payload.get("live_execution_enabled") is True:
            blockers.append("LIVE_EXECUTION_REQUESTED")
        if payload.get("broker_execution_enabled") is True:
            blockers.append("BROKER_EXECUTION_REQUESTED")
        if payload.get("execution_allowed") is True:
            blockers.append("EXECUTION_ENABLE_REQUESTED")
        return blockers

    def _workflow_blockers(
        self,
        authorization: dict[str, Any],
        dry_run: dict[str, Any],
        preflight: dict[str, Any],
        simulator: dict[str, Any],
        readiness: dict[str, Any],
        test_plan: dict[str, Any],
        final_approval: dict[str, Any],
    ) -> list[str]:
        blockers: list[str] = []
        if authorization.get("authorization_granted") is not True:
            blockers.append("AUTHORIZATION_NOT_GRANTED")
        if dry_run.get("validation_passed") is not True:
            blockers.append("DRY_RUN_NOT_VALIDATED")
        if preflight.get("validation_passed") is not True:
            blockers.append("PREFLIGHT_NOT_VALIDATED")
        if simulator.get("simulation_passed") is not True:
            blockers.append("SIMULATOR_NOT_VALIDATED")
        if readiness.get("overall_status") != "READY":
            blockers.extend(readiness.get("blockers", ["READINESS_NOT_READY"]))
        if test_plan.get("status") != "READY_FOR_FUTURE_DEMO_TESTING":
            blockers.append("TEST_PLAN_NOT_GENERATED")
        if final_approval.get("approved_for_future_demo_order") is not True:
            blockers.extend(final_approval.get("blockers", ["FINAL_APPROVAL_NOT_GRANTED"]))
        return sorted(set(blockers))

    def _blocked_result(self, blockers: list[str]) -> dict[str, Any]:
        return {
            "workflow_id": f"demo-approval-workflow-{uuid4()}",
            "status": "BLOCKED",
            "authorization_result": {},
            "dry_run_result": {},
            "preflight_result": {},
            "simulator_result": {},
            "readiness_result": {},
            "test_plan_result": {},
            "final_approval_result": {},
            "approved_for_future_demo_order": False,
            "approved_trade_count": 0,
            "max_demo_lot": self.max_demo_lot,
            "execution_allowed": False,
            "mt5_order_sent": False,
            "would_send_to_mt5": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "blockers": blockers,
            "warnings": ["NO_ORDER_PLACED_TODAY"],
            "timestamp": self._timestamp(),
        }

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
