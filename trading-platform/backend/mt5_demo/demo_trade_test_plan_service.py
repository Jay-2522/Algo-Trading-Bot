from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class DemoTradeTestPlanService:
    """Creates the controlled plan for a future single DEMO trade test."""

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def generate_test_plan(self) -> dict[str, Any]:
        plan = {
            "plan_id": f"demo-test-plan-{uuid4()}",
            "status": "READY_FOR_FUTURE_DEMO_TESTING",
            "prerequisites": self._prerequisites(),
            "failure_scenarios": self._failure_scenarios(),
            "rollback_steps": self._rollback_steps(),
            "required_approvals": self._required_approvals(),
            "execution_safety_checks": self._execution_safety_checks(),
            "recommended_symbol": "EURUSD",
            "recommended_lot": 0.01,
            "recommended_trade_count": 1,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }
        self._history.append(plan)
        return plan

    def get_latest_test_plan(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return {
            "status": "NOT_GENERATED",
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def get_test_plan_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "TEST_PLAN_SERVICE_READY",
            "latest_plan_status": self.get_latest_test_plan().get("status"),
            "history_count": len(self._history),
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def _prerequisites(self) -> list[dict[str, Any]]:
        names = [
            "MT5 connected",
            "Demo account connected",
            "EURUSD available",
            "XAUUSD available",
            "Market data available",
            "Historical data available",
            "Strategy feed available",
            "Strategy consumption available",
            "Risk qualification available",
            "Execution gate validated",
            "Authorization granted",
            "Dry-run completed",
            "Preflight passed",
            "Execution simulator passed",
            "Readiness audit passed",
            "Max lot size = 0.01",
            "Manual confirmation required",
            "Live trading disabled",
            "Broker execution disabled",
        ]
        return [{"name": name, "required": True, "validated_before_execution": True} for name in names]

    def _failure_scenarios(self) -> list[dict[str, str]]:
        scenarios = [
            "MT5 disconnects",
            "No market data",
            "Invalid spread",
            "Invalid risk result",
            "Authorization revoked",
            "Execution gate blocked",
            "Strategy unavailable",
        ]
        return [
            {
                "scenario": scenario,
                "response": "stop trade",
                "execution_instruction": "do not execute",
                "operator_action": "notify operator",
            }
            for scenario in scenarios
        ]

    def _rollback_steps(self) -> list[dict[str, Any]]:
        steps = [
            "Disable authorization",
            "Disable demo testing",
            "Clear pending request",
            "Reset execution gate",
            "Return system to simulation mode",
        ]
        return [{"step_number": index + 1, "action": step, "required": True} for index, step in enumerate(steps)]

    def _required_approvals(self) -> list[str]:
        return [
            "Operator confirms DEMO environment",
            "Operator confirms max lot size is 0.01",
            "Operator confirms live trading remains disabled",
            "Operator confirms broker execution remains disabled until the future guarded execution phase",
        ]

    def _execution_safety_checks(self) -> list[str]:
        return [
            "Re-run readiness audit immediately before future demo attempt",
            "Re-run dry-run, preflight, and simulator immediately before future demo attempt",
            "Verify execution_allowed is false until the future guarded sender phase",
            "Verify no live account or production execution route is enabled",
        ]

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
