from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class GuardedDemoOrderSenderService:
    """Guarded Phase 17 sender boundary. Verification paths never send orders."""

    allowed_symbols = {"EURUSD", "XAUUSD"}
    allowed_actions = {"BUY", "SELL"}
    max_demo_lot = 0.01

    def __init__(
        self,
        mt5_demo_service: Any,
        approval_workflow_service: Any,
        final_approval_service: Any,
        dry_run_service: Any,
        preflight_service: Any,
        simulator_service: Any,
        readiness_service: Any,
    ) -> None:
        self.mt5_demo_service = mt5_demo_service
        self.approval_workflow_service = approval_workflow_service
        self.final_approval_service = final_approval_service
        self.dry_run_service = dry_run_service
        self.preflight_service = preflight_service
        self.simulator_service = simulator_service
        self.readiness_service = readiness_service
        self._history: list[dict[str, Any]] = []
        self._demo_send_attempted = False

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "GUARDED_DEMO_ORDER_SENDER_LOCKED",
            "single_trade_limit": 1,
            "demo_send_attempted": self._demo_send_attempted,
            "allowed_symbols": sorted(self.allowed_symbols),
            "max_demo_lot": self.max_demo_lot,
            "execution_allowed": False,
            "mt5_order_sent": False,
            "demo_order_attempted": False,
            "live_order_attempted": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def prepare_order(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        return self._handle(payload, require_final_flag=False)

    def send_order(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        if not payload or payload.get("execute_single_demo_order_now") is not True:
            result = self._handle(payload, require_final_flag=False)
            result["status"] = "PREPARED_BUT_NOT_SENT" if result["status"] == "PREPARED_BUT_NOT_SENT" else result["status"]
            result["reason"] = "Explicit final execution flag not provided."
            return result
        return self._handle(payload, require_final_flag=True)

    def get_latest(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return {
            "status": "NOT_PREPARED",
            "execution_allowed": False,
            "mt5_order_sent": False,
            "demo_order_attempted": False,
            "live_order_attempted": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def list_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def _handle(self, payload: dict[str, Any] | None, require_final_flag: bool) -> dict[str, Any]:
        payload = payload or {}
        blockers = self._validate(payload)
        if blockers:
            result = self._result("REJECTED", payload, blockers, "Safety validation failed.")
            self._history.append(result)
            return result

        if not require_final_flag:
            result = self._result("PREPARED_BUT_NOT_SENT", payload, [], "Explicit final execution flag not provided.")
            self._history.append(result)
            return result

        # Phase 17 Day 1 does not add a new MT5 submission point. A later manual phase can
        # connect this guarded boundary to the existing demo executor after operator review.
        result = self._result(
            "DEMO_ORDER_REJECTED",
            payload,
            ["GUARDED_RUNTIME_SENDER_NOT_ENABLED_IN_PHASE_17_DAY_1"],
            "Guarded sender prepared, but runtime MT5 submission is not enabled today.",
            demo_order_attempted=True,
        )
        self._demo_send_attempted = True
        self._history.append(result)
        return result

    def _validate(self, payload: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        symbol = str(payload.get("symbol") or "").strip().upper()
        action = str(payload.get("action") or "").strip().upper()
        lot = self._float_or_none(payload.get("lot"))
        account_status = self.mt5_demo_service.get_status()
        workflow = self.approval_workflow_service.get_latest()
        final_approval = self.final_approval_service.get_latest_approval()
        dry_run = self.dry_run_service.get_latest()
        preflight = self.preflight_service.get_latest()
        simulator = self.simulator_service.get_latest()
        readiness = self.readiness_service.get_latest_audit()

        if payload.get("environment") != "DEMO":
            blockers.append("ENVIRONMENT_MUST_BE_DEMO")
        if symbol not in self.allowed_symbols:
            blockers.append("INVALID_SYMBOL")
        if action not in self.allowed_actions:
            blockers.append("INVALID_ACTION")
        if lot is None or lot <= 0 or lot > self.max_demo_lot:
            blockers.append("LOT_EXCEEDS_MAX_DEMO_LOT")
        for key in ["entry_price", "stop_loss", "take_profit"]:
            value = self._float_or_none(payload.get(key))
            if value is None or value <= 0:
                blockers.append(f"{key.upper()}_REQUIRED")
        for key in [
            "manual_confirmation",
            "acknowledge_demo_only",
            "acknowledge_no_live_trading",
            "acknowledge_single_trade_only",
        ]:
            if payload.get(key) is not True:
                blockers.append(f"{key.upper()}_REQUIRED")
        if payload.get("live_execution_enabled") is True:
            blockers.append("LIVE_TRADING_ENABLED")
        if payload.get("broker_execution_enabled") is True:
            blockers.append("PRODUCTION_BROKER_EXECUTION_ENABLED")
        if self._demo_send_attempted:
            blockers.append("SINGLE_DEMO_TRADE_LIMIT_REACHED")
        if account_status.get("status") != "CONNECTED" or account_status.get("environment") != "DEMO":
            blockers.append("MT5_DEMO_ACCOUNT_NOT_VALIDATED")
        if account_status.get("account_type", "DEMO") != "DEMO":
            blockers.append("MT5_ACCOUNT_IS_NOT_DEMO")
        if workflow.get("approved_for_future_demo_order") is not True:
            blockers.append("APPROVAL_WORKFLOW_NOT_APPROVED")
        if final_approval.get("approved_for_future_demo_order") is not True:
            blockers.append("FINAL_APPROVAL_NOT_APPROVED")
        if dry_run.get("validation_passed") is not True:
            blockers.append("DRY_RUN_NOT_COMPLETE")
        if preflight.get("validation_passed") is not True:
            blockers.append("PREFLIGHT_NOT_COMPLETE")
        if simulator.get("simulation_passed") is not True:
            blockers.append("SIMULATOR_NOT_COMPLETE")
        if readiness.get("overall_status") != "READY":
            blockers.append("READINESS_NOT_READY")
        return blockers

    def _result(
        self,
        status: str,
        payload: dict[str, Any],
        blockers: list[str],
        reason: str,
        demo_order_attempted: bool = False,
    ) -> dict[str, Any]:
        symbol = str(payload.get("symbol") or "").strip().upper()
        lot = self._float_or_none(payload.get("lot")) or 0.0
        return {
            "request_id": f"guarded-demo-order-{uuid4()}",
            "status": status,
            "environment": "DEMO",
            "symbol": symbol,
            "action": str(payload.get("action") or "").strip().upper(),
            "lot": lot,
            "order_request_preview": self._preview(payload) if not blockers else {},
            "mt5_order_sent": False,
            "demo_order_attempted": demo_order_attempted,
            "live_order_attempted": False,
            "reason": reason,
            "blockers": blockers,
            "single_trade_limit": 1,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def _preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": str(payload.get("symbol") or "").strip().upper(),
            "type": str(payload.get("action") or "").strip().upper(),
            "volume": self._float_or_none(payload.get("lot")),
            "price": self._float_or_none(payload.get("entry_price")),
            "sl": self._float_or_none(payload.get("stop_loss")),
            "tp": self._float_or_none(payload.get("take_profit")),
            "comment": "GUARDED_DEMO_PREPARE_ONLY",
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
