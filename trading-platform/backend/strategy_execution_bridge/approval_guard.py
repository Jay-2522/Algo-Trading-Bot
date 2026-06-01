from datetime import datetime, timezone
from typing import Any

from backend.strategy_execution_bridge.demo_approval_models import DemoExecutionApprovalRequest


class ApprovalGuard:
    """Validate queue preview decisions before demo execution approval."""

    STALE_MINUTES = 15

    def validate(
        self,
        decision: Any | None,
        request: DemoExecutionApprovalRequest,
        already_approved: bool = False,
        now_utc: datetime | None = None,
    ) -> tuple[bool, str, list[str]]:
        if decision is None:
            return False, "FAILED_SAFE", ["Bridge decision does not exist."]
        if not request.confirm_demo_approval:
            return False, "REJECTED_NOT_CONFIRMED", ["confirm_demo_approval must be true."]
        if already_approved:
            return False, "REJECTED_DUPLICATE_APPROVAL", ["Bridge decision already has an approved demo candidate."]
        if not bool(self._get(decision, "queue_preview_created", False)) or not self._get(decision, "queue_preview_id", None):
            return False, "REJECTED_NO_QUEUE_PREVIEW", ["Bridge decision has no queue preview."]
        if self._get(decision, "bridge_status", "") != "APPROVED_FOR_QUEUE_PREVIEW":
            return False, "REJECTED_BRIDGE_NOT_APPROVED", ["Bridge decision is not approved for queue preview."]
        if not bool(self._get(decision, "risk_approved", False)):
            return False, "REJECTED_RISK_NOT_APPROVED", ["Execution risk did not approve this bridge decision."]
        if bool(self._get(decision, "live_execution_enabled", True)):
            return False, "FAILED_SAFE", ["Live execution flag must remain false."]
        if bool(self._get(decision, "broker_execution_enabled", True)):
            return False, "FAILED_SAFE", ["Broker execution flag must remain false."]
        if self._is_stale(decision, now_utc=now_utc):
            return False, "REJECTED_STALE_PREVIEW", ["Queue preview is older than 15 minutes."]
        return True, "APPROVED_FOR_DEMO_EXECUTION", []

    def _is_stale(self, decision: Any, now_utc: datetime | None = None) -> bool:
        timestamp = self._get(decision, "timestamp", None)
        if timestamp is None:
            return True
        if not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        now = now_utc or datetime.now(timezone.utc)
        return (now - timestamp).total_seconds() > self.STALE_MINUTES * 60

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
