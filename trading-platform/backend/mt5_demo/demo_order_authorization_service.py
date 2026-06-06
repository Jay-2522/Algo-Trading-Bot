from datetime import datetime, timezone
from typing import Any

from backend.mt5_demo.demo_order_authorization_models import DemoOrderAuthorizationStatus


class DemoOrderAuthorizationService:
    """Manual DEMO-only authorization layer. It never permits order placement on Day 1."""

    required_payload = {
        "environment": "DEMO",
        "manual_confirmation": True,
        "acknowledge_no_live_trading": True,
        "acknowledge_demo_only": True,
        "max_demo_lot": 0.01,
    }

    def __init__(self) -> None:
        self._demo_order_testing_enabled = False
        self._status = "LOCKED"
        self._warnings = ["Demo order authorization is locked by default. No order placement is allowed today."]

    def get_status(self) -> dict[str, Any]:
        return self._status_payload()

    def validate_authorization_request(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        warnings: list[str] = []

        for key, expected in self.required_payload.items():
            value = payload.get(key)
            if value != expected:
                warnings.append(f"{key} must be {expected!r}.")

        if payload.get("live_execution_enabled") is True:
            warnings.append("Live execution is never accepted by the demo authorization layer.")
        if payload.get("broker_execution_enabled") is True:
            warnings.append("Broker execution is never accepted by the demo authorization layer.")
        if payload.get("execution_allowed") is True:
            warnings.append("Execution cannot be enabled during Phase 16 Day 1.")

        valid = not warnings
        return {
            "valid": valid,
            "status": "VALIDATED" if valid else "REJECTED",
            "warnings": warnings,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def request_demo_authorization(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        validation = self.validate_authorization_request(payload)
        if not validation["valid"]:
            self._demo_order_testing_enabled = False
            self._status = "LOCKED"
            self._warnings = ["Authorization request rejected."] + validation["warnings"]
            return {
                **self._status_payload(),
                "authorization_granted": False,
                "validation": validation,
            }

        self._demo_order_testing_enabled = True
        self._status = "READY_FOR_DEMO_ORDER_TESTING"
        self._warnings = [
            "Demo order testing authorization accepted for future Day 2 checks.",
            "Order placement remains blocked during Phase 16 Day 1.",
        ]
        return {
            **self._status_payload(),
            "authorization_granted": True,
            "validation": validation,
        }

    def revoke_demo_authorization(self) -> dict[str, Any]:
        self._demo_order_testing_enabled = False
        self._status = "LOCKED"
        self._warnings = ["Demo order authorization revoked. No order placement is allowed."]
        return self._status_payload()

    def get_checklist(self) -> dict[str, Any]:
        return {
            "status": self._status,
            "items": [
                self._item("MT5 demo account connected"),
                self._item("EURUSD visible"),
                self._item("XAUUSD visible"),
                self._item("Market data readable"),
                self._item("Risk engine validated"),
                self._item("Execution gate validated"),
                self._item("Manual confirmation required", True),
                self._item("Max demo lot = 0.01", True),
                self._item("Live trading disabled", True),
                self._item("Broker execution disabled", True),
            ],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _status_payload(self) -> dict[str, Any]:
        return DemoOrderAuthorizationStatus(
            demo_order_testing_enabled=self._demo_order_testing_enabled,
            live_execution_enabled=False,
            broker_execution_enabled=False,
            execution_allowed=False,
            status=self._status,
            warnings=list(self._warnings),
            timestamp=self._timestamp(),
        ).to_dict()

    def _item(self, name: str, validated: bool = False) -> dict[str, Any]:
        return {
            "name": name,
            "validated": validated,
            "required": True,
            "execution_allowed": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
