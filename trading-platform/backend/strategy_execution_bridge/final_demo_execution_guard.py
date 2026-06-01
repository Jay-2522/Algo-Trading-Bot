from datetime import datetime, timezone
from typing import Any

from backend.strategy_execution_bridge.final_demo_execution_models import FinalDemoExecutionRequest


class FinalDemoExecutionGuard:
    """Validate demo execution candidates before guarded MT5 demo handoff."""

    STALE_MINUTES = 15
    SUPPORTED_SYMBOLS = {"EURUSD"}

    def validate(
        self,
        candidate: Any | None,
        request: FinalDemoExecutionRequest,
        already_executed: bool = False,
        now_utc: datetime | None = None,
    ) -> tuple[bool, str, list[str]]:
        if not request.confirm_demo_execution:
            return False, "BLOCKED_NOT_CONFIRMED", ["confirm_demo_execution must be true."]
        if candidate is None:
            return False, "BLOCKED_CANDIDATE_NOT_FOUND", ["Demo execution candidate was not found."]
        if already_executed:
            return False, "BLOCKED_DUPLICATE_EXECUTION", ["Demo execution candidate has already entered final execution flow."]
        if not bool(self._get(candidate, "ready_for_demo_execution", False)):
            return False, "BLOCKED_CANDIDATE_NOT_APPROVED", ["Candidate is not ready for demo execution."]
        if not bool(self._get(candidate, "requires_final_execution_confirmation", True)):
            return False, "BLOCKED_CANDIDATE_NOT_APPROVED", ["Candidate does not require final confirmation as expected."]
        if bool(self._get(candidate, "live_execution_enabled", True)):
            return False, "FAILED_SAFE", ["Candidate live execution flag must remain false."]
        if not bool(self._get(candidate, "demo_execution", False)):
            return False, "BLOCKED_CANDIDATE_NOT_APPROVED", ["Candidate is not marked for demo execution."]
        if self._is_stale(candidate, now_utc=now_utc):
            return False, "BLOCKED_STALE_CANDIDATE", ["Demo execution candidate is older than 15 minutes."]
        if str(self._get(candidate, "symbol", "")).upper() not in self.SUPPORTED_SYMBOLS:
            return False, "BLOCKED_DEMO_GUARD", ["Existing guarded demo executor supports EURUSD only."]
        return True, "DEMO_EXECUTION_SENT", []

    def _is_stale(self, candidate: Any, now_utc: datetime | None = None) -> bool:
        timestamp = self._get(candidate, "timestamp", None)
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
